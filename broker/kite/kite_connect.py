"""Kite Connect integration for live trading."""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

import yaml
from kiteconnect import KiteConnect as KiteConnectAPI
try:
    from kiteconnect import WebSocket
except ImportError:
    try:
        from kiteconnect import KiteTicker as WebSocket
    except ImportError:
        WebSocket = None

logger = logging.getLogger(__name__)


class KiteConnectConfig:
    """Configuration loader for Kite Connect."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to kite-config.yaml file
        """
        self.config_path = Path(config_path or os.getenv(
            "KITE_CONFIG_PATH",
            "config/kite-config.yaml"
        ))
        self.options_path = Path(os.getenv(
            "OPTIONS_CONFIG_PATH",
            "config/options.yaml"
        ))
        self.config = self._load_config()
        self.options = self._load_options()
    
    def _load_config(self) -> dict:
        """Load and parse configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        return config

    def _load_options(self) -> dict:
        """Load and parse options configuration file."""
        if not self.options_path.exists():
            logger.warning(f"Options config not found: {self.options_path}")
            return {}
        
        try:
            with open(self.options_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading options config: {e}")
            return {}
    
    def _resolve_env_var(self, value: str) -> str:
        """Resolve environment variables in config values.
        
        Format: ${VAR_NAME:default_value}
        """
        if not isinstance(value, str):
            return value
        
        if not value.startswith("${") or not value.endswith("}"):
            return value
        
        content = value[2:-1]
        if ":" in content:
            var_name, default = content.split(":", 1)
            return os.getenv(var_name.strip(), default)
        else:
            return os.getenv(content, "")
    
    def get_api_key(self) -> str:
        """Get API key."""
        value = self.config.get("kite", {}).get("api", {}).get("key", "")
        return self._resolve_env_var(value)
    
    def get_api_secret(self) -> str:
        """Get API secret."""
        value = self.config.get("kite", {}).get("api", {}).get("secret", "")
        return self._resolve_env_var(value)
    
    def get_access_token(self) -> str:
        """Get access token."""
        value = self.config.get("kite", {}).get("api", {}).get("access_token", "")
        return self._resolve_env_var(value)
    
    def get_product(self) -> str:
        """Get trading product (MIS/CNC/NRML)."""
        return self.config.get("kite", {}).get("trading", {}).get("product", "MIS")
    
    def get_exchange(self, symbol: Optional[str] = None) -> str:
        """Get trading exchange.
        
        Args:
            symbol: Optional symbol to get specific exchange for
        """
        if symbol:
            indices = self.config.get("kite", {}).get("instruments", {}).get("indices", {})
            if symbol in indices:
                return indices[symbol].get("exchange", "NSE")
        
        return self.config.get("kite", {}).get("trading", {}).get("exchange", "NSE")
    
    def get_symbols(self) -> List[str]:
        """Get trading symbols, filtered by enabled status in options.yaml."""
        config_symbols = self.config.get("kite", {}).get("instruments", {}).get("symbols", [])
        indices_config = self.options.get("indices", {})
        
        enabled_symbols = []
        for s in config_symbols:
            # Check if index is enabled in options.yaml
            index_cfg = indices_config.get(s.lower(), {})
            if index_cfg.get("enabled", False):
                enabled_symbols.append(s)
                
        return enabled_symbols
    
    def get_instrument_token(self, symbol: str) -> Optional[str]:
        """Get instrument token for symbol."""
        indices = self.config.get("kite", {}).get("instruments", {}).get("indices", {})
        # Only return token if index is enabled
        indices_config = self.options.get("indices", {})
        if not indices_config.get(symbol.lower(), {}).get("enabled", False):
            return None
        return indices.get(symbol, {}).get("token")
    
    def get_lot_size(self, symbol: str) -> int:
        """Get lot size for symbol."""
        indices = self.config.get("kite", {}).get("instruments", {}).get("indices", {})
        return indices.get(symbol, {}).get("lot_size", 1)
    
    def is_live_trading_enabled(self) -> bool:
        """Check if live trading is enabled."""
        return self.config.get("live_trading", {}).get("enabled", False)
    
    def get_live_trading_symbols(self) -> List[str]:
        """Get symbols for live trading, filtered by enabled status in options.yaml."""
        config_symbols = self.config.get("live_trading", {}).get("symbols", [])
        indices_config = self.options.get("indices", {})
        
        enabled_symbols = []
        for s in config_symbols:
            index_cfg = indices_config.get(s.lower(), {})
            if index_cfg.get("enabled", False):
                enabled_symbols.append(s)
                
        return enabled_symbols
    
    def get_max_positions(self) -> int:
        """Get maximum open positions."""
        return self.config.get("live_trading", {}).get("settings", {}).get("max_positions", 5)
    
    def get_max_loss_per_trade(self) -> float:
        """Get maximum loss per trade."""
        return self.config.get("live_trading", {}).get("risk_management", {}).get("max_loss_per_trade", 500)
    
    def get_max_daily_loss(self) -> float:
        """Get maximum daily loss."""
        return self.config.get("live_trading", {}).get("risk_management", {}).get("max_daily_loss", 2000)


class KiteConnectBroker:
    """Kite Connect broker for live trading."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Kite Connect broker.
        
        Args:
            config_path: Path to kite-config.yaml file
        """
        self.config = KiteConnectConfig(config_path)
        self.kite = None
        self.ws = None
        self.connected = False
        self.subscribed_instruments = set()
        self._connect()
    
    def _connect(self):
        """Connect to Kite Connect API."""
        try:
            api_key = self.config.get_api_key()
            access_token = self.config.get_access_token()
            
            if not api_key or api_key == "YOUR_KITE_API_KEY":
                raise ValueError("API key not configured")
            
            if not access_token or access_token == "YOUR_KITE_ACCESS_TOKEN":
                raise ValueError("Access token not configured")
            
            self.kite = KiteConnectAPI(api_key=api_key)
            self.kite.set_access_token(access_token)
            
            self.kite.profile()
            
            logger.info("Connected to Kite Connect API")
            self.connected = True
            
        except Exception as e:
            logger.error(f"Failed to connect to Kite Connect: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to Kite Connect."""
        return self.connected and self.kite is not None
    
    def disconnect(self):
        """Disconnect from Kite Connect."""
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        self.connected = False
        self.kite = None
        logger.info("Disconnected from Kite Connect")
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, dict]:
        """Get market quotes for symbols.
        
        Args:
            symbols: List of symbol names (e.g., ["NIFTY50", "BANKNIFTY"])
        
        Returns:
            Dictionary with symbol quotes
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            instruments_to_fetch = []
            for s in symbols:
                exchange = self.config.get_exchange(s)
                instruments_to_fetch.append(f"{exchange}:{s}")
            
            quotes = self.kite.quote(instruments=instruments_to_fetch)
            return quotes
            
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            return {}
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """Get last traded price for symbol.
        
        Args:
            symbol: Symbol name (e.g., "NIFTY50")
        
        Returns:
            Last traded price or None
        """
        try:
            exchange = self.config.get_exchange(symbol)
            instr = f"{exchange}:{symbol}"
            quote = self.kite.quote(instruments=[instr])
            if quote and instr in quote:
                return quote[instr]["last_price"]
        except Exception as e:
            logger.error(f"Error fetching LTP for {symbol}: {e}")
        
        return None
    
    def place_order(self, symbol: str, order_type: str, quantity: int,
                   price: Optional[float] = None, stop_loss: Optional[float] = None,
                   take_profit: Optional[float] = None, **kwargs) -> Optional[str]:
        """Place an order.
        
        Args:
            symbol: Trading symbol
            order_type: Order type (BUY/SELL)
            quantity: Order quantity
            price: Order price (for limit orders)
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            **kwargs: Additional parameters
        
        Returns:
            Order ID or None if failed
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            kite_order_type = self.config.get("kite", {}).get("trading", {}).get("order_type", "MARKET")
            product = self.config.get_product()
            exchange = self.config.get_exchange(symbol)
            
            order_params = {
                "exchange": exchange,
                "tradingsymbol": symbol,
                "transaction_type": order_type,
                "quantity": quantity,
                "order_type": kite_order_type,
                "product": product,
            }
            
            if price and kite_order_type == "LIMIT":
                order_params["price"] = price
            
            order_id = self.kite.place_order(**order_params)
            logger.info(f"Order placed: {order_id} for {symbol} {order_type} {quantity}")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            self.kite.cancel_order(order_id=order_id)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_orders(self) -> List[dict]:
        """Get all orders.
        
        Returns:
            List of orders
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            orders = self.kite.orders()
            return orders if orders else []
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []
    
    def get_order_status(self, order_id: str) -> Optional[dict]:
        """Get status of a specific order.
        
        Args:
            order_id: Order ID
        
        Returns:
            Order details or None if not found
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            orders = self.get_orders()
            for order in orders:
                if order["order_id"] == order_id:
                    return order
        except Exception as e:
            logger.error(f"Error fetching order status: {e}")
        
        return None
    
    def get_positions(self) -> Dict[str, dict]:
        """Get open positions.
        
        Returns:
            Dictionary of positions indexed by symbol
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            positions = self.kite.positions()
            result = {}
            
            if positions and "net" in positions:
                for position in positions["net"]:
                    symbol = position["tradingsymbol"]
                    result[symbol] = position
            
            return result
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return {}
    
    def get_position(self, symbol: str) -> Optional[dict]:
        """Get position for specific symbol.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Position details or None if no position
        """
        positions = self.get_positions()
        return positions.get(symbol)
    
    def get_holdings(self) -> List[dict]:
        """Get holdings (delivery positions).
        
        Returns:
            List of holdings
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            holdings = self.kite.holdings()
            return holdings if holdings else []
        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return []
    
    def get_profile(self) -> Optional[dict]:
        """Get user profile information.
        
        Returns:
            User profile details
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            return self.kite.profile()
        except Exception as e:
            logger.error(f"Error fetching profile: {e}")
            return None
    
    def get_margin(self) -> Optional[dict]:
        """Get account margin information.
        
        Returns:
            Margin details
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Kite Connect")
        
        try:
            return self.kite.margins()
        except Exception as e:
            logger.error(f"Error fetching margins: {e}")
            return None
    
    def subscribe_websocket(self, symbols: List[str]):
        """Subscribe to WebSocket updates for symbols.
        
        Args:
            symbols: List of symbols to subscribe
        """
        if WebSocket is None:
            logger.warning("WebSocket/KiteTicker not available in kiteconnect library")
            return
        
        if not self.is_connected():
            logger.warning("Not connected to Kite Connect, cannot subscribe to WebSocket")
            return
        
        try:
            api_key = self.config.get_api_key()
            access_token = self.config.get_access_token()
            
            self.ws = WebSocket(api_key=api_key, public_token=access_token)
            
            for symbol in symbols:
                instrument_token = self.config.get_instrument_token(symbol)
                if instrument_token:
                    self.ws.subscribe([int(instrument_token)])
                    self.subscribed_instruments.add(symbol)
            
            logger.info(f"Subscribed to WebSocket for: {symbols}")
            
        except Exception as e:
            logger.error(f"Error subscribing to WebSocket: {e}")
    
    def unsubscribe_websocket(self, symbols: List[str]):
        """Unsubscribe from WebSocket updates for symbols.
        
        Args:
            symbols: List of symbols to unsubscribe
        """
        if not self.ws:
            return
        
        try:
            for symbol in symbols:
                instrument_token = self.config.get_instrument_token(symbol)
                if instrument_token:
                    self.ws.unsubscribe([int(instrument_token)])
                    self.subscribed_instruments.discard(symbol)
            
            logger.info(f"Unsubscribed from WebSocket for: {symbols}")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from WebSocket: {e}")


def get_kite_broker(config_path: Optional[str] = None) -> KiteConnectBroker:
    """Get or create Kite Connect broker instance.
    
    Args:
        config_path: Path to kite-config.yaml file
    
    Returns:
        KiteConnectBroker instance
    """
    return KiteConnectBroker(config_path)
