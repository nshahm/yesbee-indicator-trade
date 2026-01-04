import logging
from typing import Dict, Optional, List
from broker.kite.live.kite_live import KiteLiveBroker
from broker.base import Order

logger = logging.getLogger(__name__)

class PaperBroker(KiteLiveBroker):
    """
    Paper trading broker that simulates order placement while using live market data.
    """
    def __init__(self, config: Dict):
        super().__init__(config)
        self.virtual_orders: Dict[str, Order] = {}
        self.order_counter = 5000  # Start a different counter for virtual orders
        logger.info("PaperBroker initialized. Orders will be simulated.")

    def place_order(self, symbol: str, order_type: str, quantity: int, price: float,
                    stop_loss: float, take_profit: float, order_subtype: str = 'MARKET',
                    validity: str = 'DAY', product: str = 'MIS', exchange: str = 'NSE') -> Order:
        """
        Simulate order placement.
        """
        # Create internal order object
        order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
        
        # Simulate broker ID
        self.order_counter += 1
        order.broker_order_id = f"PAPER_{self.order_counter}"
        
        # Simulate immediate fill for MARKET orders
        if order_subtype.upper() == 'MARKET':
            current_price = self.get_current_price(symbol, exchange)
            fill_price = current_price if current_price > 0 else price
            order.fill_order(fill_price, quantity)
            order.status = 'FILLED'
            logger.info(f"[PAPER] Market Order FILLED: {order.broker_order_id} for {symbol} @ {fill_price}")
        else:
            order.status = 'SUBMITTED'
            logger.info(f"[PAPER] {order_subtype} Order SUBMITTED: {order.broker_order_id} for {symbol} @ {price}")
        
        self.virtual_orders[order.broker_order_id] = order
        return order

    def cancel_order(self, order: Order) -> bool:
        """
        Simulate order cancellation.
        """
        if order.broker_order_id in self.virtual_orders:
            order.status = 'CANCELLED'
            logger.info(f"[PAPER] Order CANCELLED: {order.broker_order_id}")
            return True
        return False

    def get_order_status(self, order: Order) -> str:
        """
        Get simulated order status.
        """
        return order.status

    def modify_order(self, order: Order, quantity: Optional[int] = None,
                    price: Optional[float] = None, trigger_price: Optional[float] = None,
                    order_type: Optional[str] = None) -> bool:
        """
        Simulate order modification.
        """
        if order.broker_order_id in self.virtual_orders:
            if quantity: order.quantity = quantity
            if price: order.price = price
            logger.info(f"[PAPER] Order MODIFIED: {order.broker_order_id}")
            return True
        return False

    def get_account_balance(self) -> float:
        """
        Return simulated balance.
        """
        return self.balance

    def get_positions(self) -> Dict:
        """
        For paper trading, we might want to calculate positions from virtual_orders.
        But for now, return empty or dummy as it's primarily used for tracking.
        """
        # Simplistic implementation: just return net positions from filled orders
        net_positions = []
        for order in self.virtual_orders.values():
            if order.status == 'FILLED':
                # This is a very basic mapping to Kite position format
                net_positions.append({
                    "tradingsymbol": order.symbol,
                    "quantity": order.quantity if 'BUY' in order.order_type.upper() else -order.quantity,
                    "average_price": order.average_fill_price,
                    "last_price": self.get_current_price(order.symbol),
                    "pnl": order.pnl
                })
        return {'net': net_positions, 'day': net_positions}
