import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from kiteconnect import KiteConnect
from broker.base import BaseBroker, Order

logger = logging.getLogger(__name__)

class KiteLiveBroker(BaseBroker):
    """
    Live trading broker implementation for Zerodha Kite.
    """
    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.access_token = config.get('access_token')
        self.kite = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Connect to Kite Connect API.
        """
        try:
            if not self.api_key or not self.access_token:
                logger.error("Kite API key or Access Token missing in config")
                return False
            
            self.kite = KiteConnect(api_key=self.api_key)
            self.kite.set_access_token(self.access_token)
            
            # Verify connection by getting profile
            profile = self.kite.profile()
            logger.info(f"Connected to Kite. User: {profile.get('user_name')}")
            self.is_connected = True
            
            # Update initial balance
            margins = self.kite.margins()
            self.balance = margins.get('equity', {}).get('available', {}).get('cash', 0)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kite: {str(e)}")
            self.is_connected = False
            return False

    def disconnect(self):
        """
        Disconnect from Kite Connect.
        """
        self.kite = None
        self.is_connected = False
        logger.info("Disconnected from Kite")

    def place_order(self, symbol: str, order_type: str, quantity: int, price: float,
                    stop_loss: float, take_profit: float, order_subtype: str = 'MARKET',
                    validity: str = 'DAY', product: str = 'MIS', exchange: str = 'NSE') -> Order:
        """
        Place an order on Kite.
        """
        if not self.is_connected:
            logger.error("Broker not connected. Call connect() first.")
            return None

        try:
            transaction_type = self.kite.TRANSACTION_TYPE_BUY if order_type.upper() == 'BUY' else self.kite.TRANSACTION_TYPE_SELL
            
            kite_order_type = self.kite.ORDER_TYPE_MARKET
            if order_subtype.upper() == 'LIMIT':
                kite_order_type = self.kite.ORDER_TYPE_LIMIT
            elif order_subtype.upper() == 'SL':
                kite_order_type = self.kite.ORDER_TYPE_SL
            elif order_subtype.upper() == 'SL-M':
                kite_order_type = self.kite.ORDER_TYPE_SLM

            params = {
                "exchange": exchange,
                "tradingsymbol": symbol,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "order_type": kite_order_type,
                "product": product,
                "validity": validity
            }

            if kite_order_type == self.kite.ORDER_TYPE_LIMIT:
                params["price"] = price
            
            if kite_order_type in [self.kite.ORDER_TYPE_SL, self.kite.ORDER_TYPE_SLM]:
                params["trigger_price"] = stop_loss

            # Place the order
            broker_order_id = self.kite.place_order(variety=self.kite.VARIETY_REGULAR, **params)
            
            # Create internal order object
            order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
            order.broker_order_id = broker_order_id
            order.status = 'SUBMITTED'
            
            logger.info(f"Order placed on Kite: {broker_order_id} for {symbol}")
            return order

        except Exception as e:
            logger.error(f"Error placing order on Kite: {str(e)}")
            # Create a failed order record
            order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
            order.status = 'FAILED'
            return order

    def cancel_order(self, order: Order) -> bool:
        """
        Cancel an existing order.
        """
        if not self.is_connected or not order.broker_order_id:
            return False

        try:
            self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order.broker_order_id)
            order.status = 'CANCELLED'
            logger.info(f"Order cancelled on Kite: {order.broker_order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order.broker_order_id}: {str(e)}")
            return False

    def get_order_status(self, order: Order) -> str:
        """
        Get the latest status of an order from Kite.
        """
        if not self.is_connected or not order.broker_order_id:
            return order.status

        try:
            order_history = self.kite.order_history(order_id=order.broker_order_id)
            if order_history:
                latest_update = order_history[-1]
                kite_status = latest_update.get('status')
                
                # Map Kite status to internal status
                if kite_status == 'COMPLETE':
                    order.status = 'FILLED'
                    order.filled_quantity = latest_update.get('filled_quantity', order.quantity)
                    order.average_fill_price = latest_update.get('average_price', order.price)
                elif kite_status == 'CANCELLED':
                    order.status = 'CANCELLED'
                elif kite_status == 'REJECTED':
                    order.status = 'FAILED'
                
                return order.status
        except Exception as e:
            logger.error(f"Error fetching status for order {order.broker_order_id}: {str(e)}")
        
        return order.status

    def get_current_price(self, symbol: str, exchange: str = 'NSE') -> float:
        """
        Get LTP for a symbol.
        """
        if not self.is_connected:
            return 0.0

        try:
            instrument = f"{exchange}:{symbol}"
            quote = self.kite.ltp([instrument])
            return quote.get(instrument, {}).get('last_price', 0.0)
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {str(e)}")
            return 0.0

    def get_account_balance(self) -> float:
        """
        Get available cash balance.
        """
        if not self.is_connected:
            return self.balance

        try:
            margins = self.kite.margins()
            self.balance = margins.get('equity', {}).get('available', {}).get('cash', 0.0)
            return self.balance
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            return self.balance

    def get_positions(self) -> Dict:
        """
        Get all current positions.
        """
        if not self.is_connected:
            return {'net': [], 'day': []}

        try:
            return self.kite.positions()
        except Exception as e:
            logger.error(f"Error fetching positions: {str(e)}")
            return {'net': [], 'day': []}

    def get_holdings(self) -> List[Dict]:
        """
        Get current holdings.
        """
        if not self.is_connected:
            return []

        try:
            return self.kite.holdings()
        except Exception as e:
            logger.error(f"Error fetching holdings: {str(e)}")
            return []

    def modify_order(self, order: Order, quantity: Optional[int] = None,
                    price: Optional[float] = None, trigger_price: Optional[float] = None,
                    order_type: Optional[str] = None) -> bool:
        """
        Modify a pending order.
        """
        if not self.is_connected or not order.broker_order_id:
            return False

        try:
            params = {}
            if quantity: params['quantity'] = quantity
            if price: params['price'] = price
            if trigger_price: params['trigger_price'] = trigger_price
            if order_type: params['order_type'] = order_type

            self.kite.modify_order(variety=self.kite.VARIETY_REGULAR, 
                                 order_id=order.broker_order_id, **params)
            logger.info(f"Order modified on Kite: {order.broker_order_id}")
            return True
        except Exception as e:
            logger.error(f"Error modifying order {order.broker_order_id}: {str(e)}")
            return False
