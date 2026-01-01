from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import logging


class Order:
    def __init__(self, order_id: str, symbol: str, order_type: str, price: float,
                 quantity: int, entry_price: float, stop_loss: float, take_profit: float):
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type
        self.price = price
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.created_at = datetime.now()
        self.status = 'PENDING'
        self.filled_quantity = 0
        self.average_fill_price = 0
        self.pnl = 0
        self.pnl_percent = 0
        self.exit_reason = None
        self.broker_order_id = None

    def fill_order(self, fill_price: float, fill_quantity: Optional[int] = None):
        fill_qty = fill_quantity or self.quantity
        self.filled_quantity += fill_qty
        self.status = 'FILLED' if self.filled_quantity >= self.quantity else 'PARTIALLY_FILLED'
        self.average_fill_price = fill_price
        return self.status

    def update_pnl(self, current_price: float):
        if self.filled_quantity == 0:
            return
        
        price_diff = current_price - self.average_fill_price
        
        if 'SELL' in self.order_type or 'PUT' in self.order_type:
            price_diff = -price_diff
        
        self.pnl = price_diff * self.filled_quantity
        self.pnl_percent = (price_diff / self.average_fill_price) * 100 if self.average_fill_price > 0 else 0

    def close_order(self, exit_price: float, reason: str = 'MANUAL'):
        self.status = 'CLOSED'
        self.exit_reason = reason
        self.update_pnl(exit_price)


class BaseBroker(ABC):
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.orders: List[Order] = []
        self.open_positions: Dict[str, List[Order]] = {}
        self.closed_orders: List[Order] = []
        self.order_id_counter = 1
        self.balance = config.get('initial_capital', 100000)

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def place_order(self, symbol: str, order_type: str, quantity: int, price: float,
                    stop_loss: float, take_profit: float) -> Order:
        pass

    @abstractmethod
    def cancel_order(self, order: Order) -> bool:
        pass

    @abstractmethod
    def get_order_status(self, order: Order) -> str:
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        pass

    @abstractmethod
    def get_account_balance(self) -> float:
        pass

    def create_order_internal(self, symbol: str, order_type: str, entry_price: float,
                            quantity: int, stop_loss: float, take_profit: float) -> Order:
        order_id = f"ORD_{self.order_id_counter}"
        self.order_id_counter += 1
        
        order = Order(order_id, symbol, order_type, entry_price, quantity,
                     entry_price, stop_loss, take_profit)
        
        self.orders.append(order)
        if symbol not in self.open_positions:
            self.open_positions[symbol] = []
        self.open_positions[symbol].append(order)
        
        return order

    def close_order_internal(self, order: Order, exit_price: float, reason: str = 'MANUAL'):
        order.close_order(exit_price, reason)
        self.closed_orders.append(order)
        
        if order.symbol in self.open_positions:
            self.open_positions[order.symbol] = [
                o for o in self.open_positions[order.symbol] if o.order_id != order.order_id
            ]

    def get_open_positions(self, symbol: Optional[str] = None) -> List[Order]:
        if symbol:
            return self.open_positions.get(symbol, [])
        
        result = []
        for orders in self.open_positions.values():
            result.extend(orders)
        return result

    def get_position_stats(self) -> Dict:
        total_open = len(self.get_open_positions())
        total_pnl = sum(o.pnl for o in self.get_open_positions())
        winning = len([o for o in self.get_open_positions() if o.pnl > 0])
        losing = len([o for o in self.get_open_positions() if o.pnl < 0])
        
        return {
            'open_positions': total_open,
            'total_pnl': total_pnl,
            'winning': winning,
            'losing': losing,
            'win_rate': (winning / total_open * 100) if total_open > 0 else 0,
        }

    def check_stop_loss(self, order: Order, current_price: float) -> bool:
        if 'BUY' in order.order_type or 'CALL' in order.order_type:
            return current_price <= order.stop_loss
        else:
            return current_price >= order.stop_loss

    def check_take_profit(self, order: Order, current_price: float) -> bool:
        if 'BUY' in order.order_type or 'CALL' in order.order_type:
            return current_price >= order.take_profit
        else:
            return current_price <= order.take_profit


class BacktestBroker(BaseBroker):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.current_prices: Dict[str, float] = {}
        self.holdings: List[Dict] = []
        self.positions: Dict[str, Dict] = {}

    def connect(self) -> bool:
        self.logger.info("Backtest broker initialized")
        return True

    def disconnect(self):
        self.logger.info("Backtest broker disconnected")

    def place_order(self, symbol: str, order_type: str, quantity: int, price: float,
                    stop_loss: float, take_profit: float, order_subtype: str = 'MARKET',
                    validity: str = 'DAY', product: str = 'MIS') -> Order:
        order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
        order.fill_order(price, quantity)
        order.status = 'FILLED'
        self.balance -= (price * quantity * (1 + self.config.get('commission', 0)))
        self.logger.info(f"Order placed and filled: {order.order_id} | {symbol} | {order_type} | Qty: {quantity} @ {price}")
        return order

    def cancel_order(self, order: Order) -> bool:
        if order.status in ['PENDING', 'PARTIALLY_FILLED']:
            order.status = 'CANCELLED'
            self.logger.info(f"Order cancelled: {order.order_id}")
            return True
        return False

    def get_order_status(self, order: Order) -> str:
        return order.status

    def get_current_price(self, symbol: str) -> float:
        return self.current_prices.get(symbol, 0)

    def set_current_price(self, symbol: str, price: float):
        self.current_prices[symbol] = price

    def get_account_balance(self) -> float:
        return self.balance

    def update_balance(self, amount: float):
        self.balance += amount

    def place_bracket_order(self, symbol: str, order_type: str, quantity: int, price: float,
                          stop_loss: float, take_profit: float, order_subtype: str = 'MARKET') -> Dict:
        order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
        order.fill_order(price, quantity)
        order.status = 'FILLED'
        self.balance -= (price * quantity * (1 + self.config.get('commission', 0)))
        
        return {
            'order': order,
            'broker_order_id': order.broker_order_id,
            'status': 'SUBMITTED'
        }

    def place_cover_order(self, symbol: str, order_type: str, quantity: int, price: float,
                         stop_loss: float) -> Dict:
        order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, 0)
        order.fill_order(price, quantity)
        order.status = 'FILLED'
        self.balance -= (price * quantity * (1 + self.config.get('commission', 0)))
        
        return {
            'order': order,
            'broker_order_id': order.broker_order_id,
            'status': 'SUBMITTED'
        }

    def modify_order(self, order: Order, quantity: Optional[int] = None, 
                    price: Optional[float] = None, trigger_price: Optional[float] = None) -> bool:
        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price
        return True

    def get_holdings(self) -> List[Dict]:
        return self.holdings

    def get_positions(self) -> Dict:
        return {
            'net': list(self.positions.values()),
            'day': [],
            'total_net_positions': len(self.positions),
            'total_day_positions': 0
        }

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        return self.positions.get(symbol)

    def get_margin_available(self) -> Dict:
        return {
            'equity_margin': self.balance,
            'equity_used': 0,
            'commodity_margin': 0,
            'commodity_used': 0,
            'available_balance': self.balance
        }

    def get_leverage(self, symbol: str) -> Dict:
        position = self.get_position_by_symbol(symbol)
        
        if not position:
            return {
                'symbol': symbol,
                'quantity': 0,
                'leverage': 0,
                'margin_required': 0
            }
        
        return {
            'symbol': symbol,
            'quantity': position.get('quantity', 0),
            'last_price': position.get('last_price', 0),
            'average_price': position.get('average_price', 0),
            'margin_required': 0,
            'margin_multiplier': 1
        }

    def square_off_position(self, symbol: str, quantity: Optional[int] = None) -> bool:
        position = self.get_position_by_symbol(symbol)
        
        if not position:
            return False
        
        qty = quantity or abs(position.get('quantity', 0))
        direction = 'SELL' if position.get('quantity', 0) > 0 else 'BUY'
        
        order = self.place_order(
            symbol=symbol,
            order_type=direction,
            quantity=qty,
            price=position.get('last_price', 0),
            stop_loss=0,
            take_profit=0
        )
        
        if order.status != 'FAILED':
            del self.positions[symbol]
        return order.status != 'FAILED'

    def place_multi_leg_order(self, legs: List[Dict]) -> List[Order]:
        orders = []
        for leg in legs:
            order = self.place_order(
                symbol=leg.get('symbol'),
                order_type=leg.get('order_type'),
                quantity=leg.get('quantity'),
                price=leg.get('price'),
                stop_loss=leg.get('stop_loss', 0),
                take_profit=leg.get('take_profit', 0)
            )
            orders.append(order)
        
        return orders

    def exit_by_order_id(self, broker_order_id: str) -> bool:
        return True


class ZerodhaBroker(BaseBroker):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.kite = None
        self.ticker = None
        self.access_token = None
        self.subscribed_tokens = set()

    def connect(self) -> bool:
        try:
            from kiteconnect import KiteConnect
            
            api_key = self.config.get('api_key')
            access_token = self.config.get('access_token')
            
            if not api_key or not access_token:
                self.logger.error("API key or access token not configured")
                return False
            
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
            self.access_token = access_token
            
            profile = self.kite.profile()
            self.balance = profile.get('equity', {}).get('available', 0)
            self.logger.info(f"Connected to Zerodha. Available balance: {self.balance}")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Zerodha: {e}")
            return False

    def disconnect(self):
        if self.ticker:
            self.ticker.close()
        self.logger.info("Disconnected from Zerodha")

    def place_order(self, symbol: str, order_type: str, quantity: int, price: float,
                    stop_loss: float, take_profit: float, order_subtype: str = 'MARKET',
                    validity: str = 'DAY', product: str = 'MIS') -> Order:
        try:
            order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
            
            direction = 'BUY' if 'BUY' in order_type else 'SELL'
            order_type_map = {
                'MARKET': 'MARKET',
                'LIMIT': 'LIMIT',
                'STOP': 'STOP',
                'STOP_LIMIT': 'STOP'
            }
            kite_order_type = order_type_map.get(order_subtype, 'MARKET')
            
            order_params = {
                'variety': 'regular',
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'transaction_type': direction,
                'quantity': quantity,
                'order_type': kite_order_type,
                'product': product,
                'validity': validity
            }
            
            if order_subtype in ['LIMIT', 'STOP_LIMIT']:
                order_params['price'] = price
            
            if order_subtype in ['STOP', 'STOP_LIMIT']:
                order_params['trigger_price'] = stop_loss if direction == 'SELL' else price
            
            broker_order = self.kite.place_order(**order_params)
            
            order.broker_order_id = broker_order.get('order_id')
            order.status = 'SUBMITTED'
            self.logger.info(f"Order placed: {order.order_id} (Broker ID: {order.broker_order_id}) | Type: {order_subtype}")
            
            return order
        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")
            order.status = 'FAILED'
            return order

    def cancel_order(self, order: Order) -> bool:
        try:
            if not order.broker_order_id:
                return False
            
            self.kite.cancel_order(
                variety='regular',
                order_id=order.broker_order_id
            )
            order.status = 'CANCELLED'
            self.logger.info(f"Order cancelled: {order.broker_order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to cancel order: {e}")
            return False

    def get_order_status(self, order: Order) -> str:
        try:
            if not order.broker_order_id:
                return order.status
            
            orders = self.kite.orders()
            for kite_order in orders:
                if kite_order['order_id'] == order.broker_order_id:
                    status_map = {
                        'COMPLETE': 'FILLED',
                        'CANCELLED': 'CANCELLED',
                        'REJECTED': 'FAILED',
                        'PENDING': 'PENDING'
                    }
                    order.status = status_map.get(kite_order['status'], order.status)
                    return order.status
            
            return order.status
        except Exception as e:
            self.logger.error(f"Failed to get order status: {e}")
            return order.status

    def get_current_price(self, symbol: str) -> float:
        try:
            quote = self.kite.quote('NSE:' + symbol)
            return quote['NSE:' + symbol]['last_price']
        except Exception as e:
            self.logger.error(f"Failed to get current price for {symbol}: {e}")
            return 0

    def get_account_balance(self) -> float:
        try:
            profile = self.kite.profile()
            self.balance = profile.get('equity', {}).get('available', 0)
            return self.balance
        except Exception as e:
            self.logger.error(f"Failed to get account balance: {e}")
            return self.balance

    def subscribe_to_ticks(self, symbols: List[str]):
        try:
            from kiteconnect import KiteTicker
            
            self.ticker = KiteTicker(
                self.config.get('api_key'),
                self.access_token
            )
            
            def on_tick(ws, ticks):
                for tick in ticks:
                    symbol = tick['instrument_token']
                    if symbol in self.subscribed_tokens:
                        pass
            
            def on_connect(ws, response):
                self.logger.info("Ticker connected")
                for symbol in symbols:
                    token = self._get_instrument_token(symbol)
                    if token:
                        self.ticker.subscribe([token])
                        self.subscribed_tokens.add(token)
            
            def on_close(ws, code, reason):
                self.logger.info(f"Ticker closed: {reason}")
            
            self.ticker.on_tick = on_tick
            self.ticker.on_connect = on_connect
            self.ticker.on_close = on_close
            
            self.ticker.connect(threaded=True)
        except Exception as e:
            self.logger.error(f"Failed to subscribe to ticks: {e}")

    def _get_instrument_token(self, symbol: str) -> Optional[int]:
        try:
            instruments = self.kite.instruments('NSE')
            for inst in instruments:
                if inst['tradingsymbol'] == symbol:
                    return inst['instrument_token']
        except Exception as e:
            self.logger.error(f"Failed to get instrument token for {symbol}: {e}")
        return None

    def place_bracket_order(self, symbol: str, order_type: str, quantity: int, price: float,
                          stop_loss: float, take_profit: float, order_subtype: str = 'MARKET') -> Dict:
        try:
            direction = 'BUY' if 'BUY' in order_type else 'SELL'
            order_type_map = {
                'MARKET': 'MARKET',
                'LIMIT': 'LIMIT',
                'STOP': 'STOP',
                'STOP_LIMIT': 'STOP'
            }
            kite_order_type = order_type_map.get(order_subtype, 'MARKET')
            
            sl_distance = abs(price - stop_loss)
            tp_distance = abs(take_profit - price)
            
            order_params = {
                'variety': 'bo',
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'transaction_type': direction,
                'quantity': quantity,
                'order_type': kite_order_type,
                'product': 'MIS',
                'validity': 'DAY'
            }
            
            if order_subtype in ['LIMIT', 'STOP_LIMIT']:
                order_params['price'] = price
            
            if direction == 'BUY':
                order_params['stoploss'] = stop_loss
                order_params['target'] = take_profit
            else:
                order_params['stoploss'] = stop_loss
                order_params['target'] = take_profit
            
            broker_order = self.kite.place_order(**order_params)
            order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, take_profit)
            order.broker_order_id = broker_order.get('order_id')
            order.status = 'SUBMITTED'
            
            self.logger.info(f"Bracket order placed: {order.order_id} (Broker ID: {order.broker_order_id}) | "
                           f"SL: {stop_loss}, TP: {take_profit}")
            
            return {
                'order': order,
                'broker_order_id': broker_order.get('order_id'),
                'status': 'SUBMITTED'
            }
        except Exception as e:
            self.logger.error(f"Failed to place bracket order: {e}")
            return {
                'order': None,
                'broker_order_id': None,
                'status': 'FAILED',
                'error': str(e)
            }

    def place_cover_order(self, symbol: str, order_type: str, quantity: int, price: float,
                         stop_loss: float) -> Dict:
        try:
            direction = 'BUY' if 'BUY' in order_type else 'SELL'
            
            order_params = {
                'variety': 'co',
                'exchange': 'NSE',
                'tradingsymbol': symbol,
                'transaction_type': direction,
                'quantity': quantity,
                'order_type': 'MARKET',
                'product': 'MIS',
                'validity': 'DAY',
                'price': price,
                'trigger_price': stop_loss
            }
            
            broker_order = self.kite.place_order(**order_params)
            order = self.create_order_internal(symbol, order_type, price, quantity, stop_loss, 0)
            order.broker_order_id = broker_order.get('order_id')
            order.status = 'SUBMITTED'
            
            self.logger.info(f"Cover order placed: {order.order_id} (Broker ID: {order.broker_order_id}) | "
                           f"Stop Loss: {stop_loss}")
            
            return {
                'order': order,
                'broker_order_id': broker_order.get('order_id'),
                'status': 'SUBMITTED'
            }
        except Exception as e:
            self.logger.error(f"Failed to place cover order: {e}")
            return {
                'order': None,
                'broker_order_id': None,
                'status': 'FAILED',
                'error': str(e)
            }

    def modify_order(self, order: Order, quantity: Optional[int] = None, 
                    price: Optional[float] = None, trigger_price: Optional[float] = None) -> bool:
        try:
            if not order.broker_order_id:
                self.logger.error(f"No broker order ID for order {order.order_id}")
                return False
            
            modify_params = {
                'variety': 'regular',
                'order_id': order.broker_order_id
            }
            
            if quantity is not None:
                modify_params['quantity'] = quantity
                order.quantity = quantity
            
            if price is not None:
                modify_params['price'] = price
                order.price = price
            
            if trigger_price is not None:
                modify_params['trigger_price'] = trigger_price
            
            self.kite.modify_order(**modify_params)
            self.logger.info(f"Order modified: {order.broker_order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to modify order: {e}")
            return False

    def get_holdings(self) -> List[Dict]:
        try:
            holdings = self.kite.holdings()
            self.logger.info(f"Retrieved {len(holdings)} holdings")
            return holdings
        except Exception as e:
            self.logger.error(f"Failed to get holdings: {e}")
            return []

    def get_positions(self) -> Dict:
        try:
            positions = self.kite.positions()
            net_positions = positions.get('net', [])
            day_positions = positions.get('day', [])
            
            self.logger.info(f"Retrieved {len(net_positions)} net positions, {len(day_positions)} day positions")
            
            return {
                'net': net_positions,
                'day': day_positions,
                'total_net_positions': len(net_positions),
                'total_day_positions': len(day_positions)
            }
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return {'net': [], 'day': [], 'total_net_positions': 0, 'total_day_positions': 0}

    def get_position_by_symbol(self, symbol: str) -> Optional[Dict]:
        try:
            positions = self.kite.positions()
            all_positions = positions.get('net', []) + positions.get('day', [])
            
            for position in all_positions:
                if position['tradingsymbol'] == symbol:
                    return position
            
            return None
        except Exception as e:
            self.logger.error(f"Failed to get position for {symbol}: {e}")
            return None

    def get_margin_available(self) -> Dict:
        try:
            profile = self.kite.profile()
            equity = profile.get('equity', {})
            commodity = profile.get('commodity', {})
            
            return {
                'equity_margin': equity.get('margin_available', 0),
                'equity_used': equity.get('margin_used', 0),
                'commodity_margin': commodity.get('margin_available', 0),
                'commodity_used': commodity.get('margin_used', 0),
                'available_balance': equity.get('available', 0)
            }
        except Exception as e:
            self.logger.error(f"Failed to get margin info: {e}")
            return {
                'equity_margin': 0,
                'equity_used': 0,
                'commodity_margin': 0,
                'commodity_used': 0,
                'available_balance': 0
            }

    def get_leverage(self, symbol: str) -> Dict:
        try:
            position = self.get_position_by_symbol(symbol)
            
            if not position:
                return {
                    'symbol': symbol,
                    'quantity': 0,
                    'leverage': 0,
                    'margin_required': 0
                }
            
            quantity = position.get('quantity', 0)
            last_price = position.get('last_price', 0)
            leverage = position.get('average_price', 0)
            
            margin_required = (quantity * last_price) / 2 if last_price > 0 else 0
            
            return {
                'symbol': symbol,
                'quantity': quantity,
                'last_price': last_price,
                'average_price': leverage,
                'margin_required': margin_required,
                'margin_multiplier': 1 if quantity == 0 else (quantity * last_price) / margin_required if margin_required > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Failed to get leverage for {symbol}: {e}")
            return {
                'symbol': symbol,
                'quantity': 0,
                'leverage': 0,
                'margin_required': 0
            }

    def square_off_position(self, symbol: str, quantity: Optional[int] = None) -> bool:
        try:
            position = self.get_position_by_symbol(symbol)
            
            if not position:
                self.logger.warning(f"No position found for {symbol}")
                return False
            
            qty = quantity or abs(position.get('quantity', 0))
            direction = 'SELL' if position.get('quantity', 0) > 0 else 'BUY'
            
            order = self.place_order(
                symbol=symbol,
                order_type=direction,
                quantity=qty,
                price=position.get('last_price', 0),
                stop_loss=0,
                take_profit=0,
                order_subtype='MARKET'
            )
            
            self.logger.info(f"Squared off position: {symbol} | Qty: {qty} | Direction: {direction}")
            return order.status != 'FAILED'
        except Exception as e:
            self.logger.error(f"Failed to square off position for {symbol}: {e}")
            return False

    def place_multi_leg_order(self, legs: List[Dict]) -> List[Order]:
        try:
            orders = []
            for leg in legs:
                order = self.place_order(
                    symbol=leg.get('symbol'),
                    order_type=leg.get('order_type'),
                    quantity=leg.get('quantity'),
                    price=leg.get('price'),
                    stop_loss=leg.get('stop_loss', 0),
                    take_profit=leg.get('take_profit', 0),
                    order_subtype=leg.get('order_subtype', 'MARKET'),
                    product=leg.get('product', 'MIS'),
                    validity=leg.get('validity', 'DAY')
                )
                orders.append(order)
            
            self.logger.info(f"Multi-leg order placed: {len(orders)} legs")
            return orders
        except Exception as e:
            self.logger.error(f"Failed to place multi-leg order: {e}")
            return []

    def exit_by_order_id(self, broker_order_id: str) -> bool:
        try:
            self.kite.exit_order(
                variety='regular',
                order_id=broker_order_id,
                product='MIS'
            )
            self.logger.info(f"Exited order: {broker_order_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to exit order {broker_order_id}: {e}")
            return False
