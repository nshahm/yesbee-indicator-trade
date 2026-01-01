"""Kite Connect broker integration."""

from .credentials_manager import CredentialsManager
from .kite_connect import KiteConnectBroker, KiteConnectConfig, get_kite_broker
from .market_status import MarketStatus

try:
    from .kite_oauth import include_auth_router
except ImportError:
    include_auth_router = None

try:
    from .kite_trading_endpoints import include_trading_router
except ImportError:
    include_trading_router = None

__all__ = [
    "CredentialsManager",
    "KiteConnectBroker",
    "KiteConnectConfig",
    "get_kite_broker",
    "include_auth_router",
    "include_trading_router",
    "MarketStatus",
]
