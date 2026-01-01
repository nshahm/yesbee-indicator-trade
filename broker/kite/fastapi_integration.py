"""FastAPI integration for Kite Connect OAuth and Trading."""

import logging
from typing import Optional, Dict, List
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .kite_oauth import include_auth_router
from .kite_trading_endpoints import include_trading_router

logger = logging.getLogger(__name__)

_warmup_data = None
_warmup_config = None


def setup_kite_api(app: FastAPI, enable_cors: bool = True) -> FastAPI:
    """Setup Kite Connect API routes in FastAPI application.
    
    This function configures:
    - OAuth authentication endpoints (/api/auth/*)
    - Trading endpoints (/api/trading/*)
    - CORS middleware (optional)
    - Error handlers for pretty JSON responses
    
    Args:
        app: FastAPI application instance
        enable_cors: Whether to enable CORS middleware (default: True)
    
    Returns:
        FastAPI application with Kite API routes configured
    
    Example:
        ```python
        from fastapi import FastAPI
        from broker.kite.fastapi_integration import setup_kite_api
        
        app = FastAPI(
            title="Trading API",
            description="Kite Connect Trading Platform",
            version="1.0.0"
        )
        
        # Setup Kite API routes
        app = setup_kite_api(app)
        
        # Run the application
        # uvicorn main:app --reload
        ```
    """
    logger.info("Setting up Kite Connect API routes...")
    
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS middleware enabled")
    
    app = include_auth_router(app)
    logger.info("Authentication routes registered (/api/auth/*)")
    
    app = include_trading_router(app)
    logger.info("Trading routes registered (/api/trading/*)")
    
    @app.get("/")
    async def root() -> dict:
        """API root endpoint."""
        return {
            "name": "Kite Connect Trading Platform",
            "version": "1.0.0",
            "description": "Real-time trading through Kite Connect",
            "api_endpoints": {
                "authentication": "/api/auth",
                "trading": "/api/trading",
                "health": "/health",
                "documentation": "/docs",
                "openapi": "/openapi.json"
            }
        }
    
    @app.get("/health")
    async def health() -> dict:
        """Health check endpoint."""
        return {
            "status": "ok",
            "service": "Kite Connect Trading API",
            "version": "1.0.0"
        }
    
    logger.info("Kite Connect API routes setup completed successfully")
    return app


def load_warmup_data(kite_client, symbols: List[str],
                    lower_timeframe: str = "5min",
                    higher_timeframe: str = "15min",
                    num_candles: int = 30,
                    instrument_tokens: Optional[Dict[str, str]] = None) -> Dict:
    """Load historical warmup data on application startup.
    
    Args:
        kite_client: Connected KiteConnect instance
        symbols: List of symbols to warm up
        lower_timeframe: Lower timeframe for warmup (default: '5min')
        higher_timeframe: Higher timeframe for warmup (default: '15min')
        num_candles: Number of warmup candles (default: 30)
        instrument_tokens: Optional dict mapping symbol -> token
    
    Returns:
        Dictionary with warmup results for each symbol
    """
    from .historical_data_warmup import HistoricalDataWarmup
    
    global _warmup_data, _warmup_config
    
    try:
        logger.info(f"Starting warmup data load for {len(symbols)} symbols")
        
        warmup_loader = HistoricalDataWarmup(kite_client)
        
        _warmup_config = {
            'lower_timeframe': lower_timeframe,
            'higher_timeframe': higher_timeframe,
            'num_candles': num_candles,
            'symbols': symbols
        }
        
        warmup_results = warmup_loader.load_warmup_for_symbols(
            symbols=symbols,
            lower_timeframe=lower_timeframe,
            higher_timeframe=higher_timeframe,
            num_candles=num_candles,
            instrument_tokens=instrument_tokens
        )
        
        _warmup_data = warmup_results
        
        logger.info(f"Warmup data load completed successfully")
        return warmup_results
        
    except Exception as e:
        logger.error(f"Failed to load warmup data: {e}")
        _warmup_data = {}
        return {}


def get_warmup_data() -> Optional[Dict]:
    """Get cached warmup data.
    
    Returns:
        Warmup data dictionary or None if not loaded
    """
    return _warmup_data


def get_warmup_config() -> Optional[Dict]:
    """Get warmup configuration.
    
    Returns:
        Warmup config dictionary or None if not configured
    """
    return _warmup_config


def create_kite_app(
    title: str = "Kite Connect Trading API",
    description: str = "Real-time trading through Kite Connect",
    version: str = "1.0.0",
    enable_cors: bool = True,
    lifespan = None,
    load_warmup_on_startup: bool = False,
    warmup_symbols: Optional[List[str]] = None,
    warmup_lower_timeframe: str = "5min",
    warmup_higher_timeframe: str = "15min",
    warmup_num_candles: int = 30
) -> FastAPI:
    """Create a new FastAPI application with Kite Connect integration.
    
    Args:
        title: Application title
        description: Application description
        version: Application version
        enable_cors: Whether to enable CORS (default: True)
        lifespan: Optional lifespan context manager
        load_warmup_on_startup: Whether to load warmup data on startup
        warmup_symbols: List of symbols to warm up (if enabled)
        warmup_lower_timeframe: Lower timeframe for warmup (default: '5min')
        warmup_higher_timeframe: Higher timeframe for warmup (default: '15min')
        warmup_num_candles: Number of warmup candles (default: 30)
    
    Returns:
        Configured FastAPI application
    
    Example:
        ```python
        from broker.kite.fastapi_integration import create_kite_app
        
        app = create_kite_app(
            load_warmup_on_startup=True,
            warmup_symbols=['NIFTY50', 'BANKNIFTY']
        )
        # Run with: uvicorn <module>:app --reload
        ```
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    if load_warmup_on_startup and warmup_symbols:
        logger.info(f"Warmup on startup enabled for symbols: {warmup_symbols}")
        app.warmup_config = {
            'enabled': True,
            'symbols': warmup_symbols,
            'lower_timeframe': warmup_lower_timeframe,
            'higher_timeframe': warmup_higher_timeframe,
            'num_candles': warmup_num_candles
        }
    else:
        app.warmup_config = {'enabled': False}
    
    return setup_kite_api(app, enable_cors=enable_cors)
