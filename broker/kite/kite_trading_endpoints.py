"""FastAPI endpoints for Kite Connect trading operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from .kite_connect import KiteConnectBroker, get_kite_broker
from .market_status import MarketStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["trading"])

_broker_instance: Optional[KiteConnectBroker] = None


def get_broker() -> KiteConnectBroker:
    """Get or initialize Kite broker instance."""
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = get_kite_broker()
    return _broker_instance


class OrderType(str, Enum):
    """Order type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderResponse(BaseModel):
    """Order response model."""
    status: str
    message: str
    order_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class QuoteResponse(BaseModel):
    """Quote response model."""
    symbol: str
    last_price: Optional[float]
    bid: Optional[float]
    ask: Optional[float]
    volume: Optional[int]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PositionResponse(BaseModel):
    """Position response model."""
    symbol: str
    quantity: int
    buy_quantity: int
    sell_quantity: int
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class OrderStatusResponse(BaseModel):
    """Order status response model."""
    order_id: str
    symbol: str
    transaction_type: str
    quantity: int
    filled_quantity: int
    status: str
    price: float
    average_price: float
    created_at: str
    updated_at: str


class AccountResponse(BaseModel):
    """Account information response."""
    user_id: str
    user_name: str
    broker: str
    balance: float
    used_margin: float
    available_margin: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    connected: bool
    message: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: str
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health and connection status.
    
    Example:
        GET /api/trading/health
        
        Response:
        {
            "status": "ok",
            "connected": true,
            "message": "Connected to Kite Connect API",
            "timestamp": "2024-12-23T12:00:00"
        }
    """
    broker = get_broker()
    return HealthResponse(
        status="ok" if broker.is_connected() else "error",
        connected=broker.is_connected(),
        message="Connected to Kite Connect API" if broker.is_connected() 
                else "Not connected to Kite Connect API"
    )


@router.get("/", response_model=ApiResponse)
async def trading_root() -> ApiResponse:
    """Trading API root endpoint.
    
    Returns information about available trading endpoints.
    
    Example:
        GET /api/trading
        
        Response:
        {
            "success": true,
            "data": {
                "name": "Kite Connect Trading API",
                "endpoints": {...}
            },
            "message": "Trading API endpoints"
        }
    """
    return ApiResponse(
        success=True,
        data={
            "name": "Kite Connect Trading API",
            "description": "Real-time trading through Kite Connect",
            "endpoints": {
                "health": "/api/trading/health",
                "quotes": "/api/trading/quotes",
                "quote": "/api/trading/quote/{symbol}",
                "place_order": "/api/trading/orders",
                "get_orders": "/api/trading/orders",
                "cancel_order": "/api/trading/orders/{order_id}",
                "positions": "/api/trading/positions",
                "position": "/api/trading/positions/{symbol}",
                "account": "/api/trading/account",
                "holdings": "/api/trading/holdings"
            },
            "documentation": "/docs"
        },
        message="Trading API endpoints"
    )


@router.get("/quotes", response_model=ApiResponse)
async def get_quotes(symbols: str = Query(..., description="Comma-separated symbol list")) -> ApiResponse:
    """Get market quotes for multiple symbols.
    
    Args:
        symbols: Comma-separated list of symbols (e.g., "NIFTY50,BANKNIFTY")
    
    Example:
        GET /api/trading/quotes?symbols=NIFTY50,BANKNIFTY
        
        Response:
        {
            "success": true,
            "data": {
                "NIFTY50": {
                    "symbol": "NIFTY50",
                    "last_price": 23450.5,
                    "bid": 23450.0,
                    "ask": 23451.0,
                    "volume": 1000000
                },
                "BANKNIFTY": {
                    "symbol": "BANKNIFTY",
                    "last_price": 48750.0,
                    "bid": 48749.5,
                    "ask": 48750.5,
                    "volume": 500000
                }
            },
            "message": "Quotes fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        symbol_list = [s.strip() for s in symbols.split(",")]
        quotes = broker.get_quotes(symbol_list)
        
        data = {}
        for symbol in symbol_list:
            ltp = broker.get_ltp(symbol)
            data[symbol] = {
                "symbol": symbol,
                "last_price": ltp,
                "bid": None,
                "ask": None,
                "volume": None
            }
        
        return ApiResponse(
            success=True,
            data=data,
            message="Quotes fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}", response_model=ApiResponse)
async def get_quote(symbol: str) -> ApiResponse:
    """Get market quote for a single symbol.
    
    Args:
        symbol: Trading symbol (e.g., "NIFTY50")
    
    Example:
        GET /api/trading/quote/NIFTY50
        
        Response:
        {
            "success": true,
            "data": {
                "symbol": "NIFTY50",
                "last_price": 23450.5,
                "bid": 23450.0,
                "ask": 23451.0,
                "volume": 1000000
            },
            "message": "Quote fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        ltp = broker.get_ltp(symbol)
        
        if ltp is None:
            raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")
        
        return ApiResponse(
            success=True,
            data={
                "symbol": symbol,
                "last_price": ltp,
                "bid": None,
                "ask": None,
                "volume": None
            },
            message="Quote fetched successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/orders", response_model=ApiResponse)
async def place_order(
    symbol: str = Query(..., description="Trading symbol"),
    order_type: OrderType = Query(..., description="Order type (BUY/SELL)"),
    quantity: int = Query(..., description="Order quantity"),
    price: Optional[float] = Query(None, description="Order price (for limit orders)")
) -> ApiResponse:
    """Place a new order.
    
    Args:
        symbol: Trading symbol (e.g., "NIFTY50")
        order_type: Order type (BUY or SELL)
        quantity: Order quantity
        price: Optional price for limit orders
    
    Example:
        POST /api/trading/orders?symbol=NIFTY50&order_type=BUY&quantity=1
        
        Response:
        {
            "success": true,
            "data": {
                "order_id": "1001",
                "symbol": "NIFTY50",
                "order_type": "BUY",
                "quantity": 1,
                "status": "PENDING"
            },
            "message": "Order placed successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        order_id = broker.place_order(
            symbol=symbol,
            order_type=order_type.value,
            quantity=quantity,
            price=price
        )
        
        if not order_id:
            raise HTTPException(status_code=400, detail="Failed to place order")
        
        return ApiResponse(
            success=True,
            data={
                "order_id": order_id,
                "symbol": symbol,
                "order_type": order_type.value,
                "quantity": quantity,
                "status": "PENDING"
            },
            message="Order placed successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders", response_model=ApiResponse)
async def get_orders() -> ApiResponse:
    """Get all orders.
    
    Example:
        GET /api/trading/orders
        
        Response:
        {
            "success": true,
            "data": [
                {
                    "order_id": "1001",
                    "symbol": "NIFTY50",
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "status": "COMPLETE"
                }
            ],
            "message": "Orders fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        orders = broker.get_orders()
        
        return ApiResponse(
            success=True,
            data={"orders": orders, "count": len(orders)},
            message="Orders fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}", response_model=ApiResponse)
async def get_order_status(order_id: str) -> ApiResponse:
    """Get status of a specific order.
    
    Args:
        order_id: Order ID to check
    
    Example:
        GET /api/trading/orders/1001
        
        Response:
        {
            "success": true,
            "data": {
                "order_id": "1001",
                "symbol": "NIFTY50",
                "transaction_type": "BUY",
                "quantity": 1,
                "filled_quantity": 1,
                "status": "COMPLETE"
            },
            "message": "Order status fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        order = broker.get_order_status(order_id)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return ApiResponse(
            success=True,
            data=order,
            message="Order status fetched successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching order status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}", response_model=ApiResponse)
async def cancel_order(order_id: str) -> ApiResponse:
    """Cancel an order.
    
    Args:
        order_id: Order ID to cancel
    
    Example:
        DELETE /api/trading/orders/1001
        
        Response:
        {
            "success": true,
            "data": {
                "order_id": "1001",
                "status": "CANCELLED"
            },
            "message": "Order cancelled successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        success = broker.cancel_order(order_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel order")
        
        return ApiResponse(
            success=True,
            data={
                "order_id": order_id,
                "status": "CANCELLED"
            },
            message="Order cancelled successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=ApiResponse)
async def get_positions() -> ApiResponse:
    """Get all open positions.
    
    Example:
        GET /api/trading/positions
        
        Response:
        {
            "success": true,
            "data": {
                "positions": [
                    {
                        "symbol": "NIFTY50",
                        "quantity": 1,
                        "entry_price": 23400.0,
                        "current_price": 23450.5,
                        "pnl": 50.5,
                        "pnl_percent": 0.21
                    }
                ],
                "count": 1
            },
            "message": "Positions fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        positions = broker.get_positions()
        
        return ApiResponse(
            success=True,
            data={
                "positions": list(positions.values()),
                "count": len(positions)
            },
            message="Positions fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{symbol}", response_model=ApiResponse)
async def get_position(symbol: str) -> ApiResponse:
    """Get position for a specific symbol.
    
    Args:
        symbol: Trading symbol
    
    Example:
        GET /api/trading/positions/NIFTY50
        
        Response:
        {
            "success": true,
            "data": {
                "symbol": "NIFTY50",
                "quantity": 1,
                "entry_price": 23400.0,
                "current_price": 23450.5,
                "pnl": 50.5,
                "pnl_percent": 0.21
            },
            "message": "Position fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        position = broker.get_position(symbol)
        
        if not position:
            raise HTTPException(status_code=404, detail=f"No position found for {symbol}")
        
        return ApiResponse(
            success=True,
            data=position,
            message="Position fetched successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching position for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/holdings", response_model=ApiResponse)
async def get_holdings() -> ApiResponse:
    """Get all holdings (delivery positions).
    
    Example:
        GET /api/trading/holdings
        
        Response:
        {
            "success": true,
            "data": {
                "holdings": [
                    {
                        "tradingsymbol": "NIFTY50",
                        "quantity": 100,
                        "price": 23400.0,
                        "t1_quantity": 50
                    }
                ],
                "count": 1
            },
            "message": "Holdings fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        holdings = broker.get_holdings()
        
        return ApiResponse(
            success=True,
            data={
                "holdings": holdings,
                "count": len(holdings)
            },
            message="Holdings fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account", response_model=ApiResponse)
async def get_account() -> ApiResponse:
    """Get account information.
    
    Example:
        GET /api/trading/account
        
        Response:
        {
            "success": true,
            "data": {
                "user_id": "ABC123",
                "user_name": "John Doe",
                "broker": "Zerodha",
                "balance": 100000,
                "used_margin": 25000,
                "available_margin": 75000
            },
            "message": "Account information fetched successfully"
        }
    """
    try:
        broker = get_broker()
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Not connected to Kite Connect")
        
        profile = broker.get_profile()
        margin = broker.get_margin()
        
        if not profile:
            raise HTTPException(status_code=500, detail="Failed to fetch account information")
        
        data = {
            "user_id": profile.get("user_id"),
            "user_name": profile.get("user_name"),
            "broker": "Zerodha",
            "balance": margin.get("equity", {}).get("available") if margin else 0,
            "used_margin": margin.get("equity", {}).get("used") if margin else 0,
            "available_margin": margin.get("equity", {}).get("available") if margin else 0
        }
        
        return ApiResponse(
            success=True,
            data=data,
            message="Account information fetched successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching account information: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades", response_model=ApiResponse)
async def get_trades() -> ApiResponse:
    """Get trade history.
    
    Example:
        GET /api/trading/trades
        
        Response:
        {
            "success": true,
            "data": {
                "trades": [
                    {
                        "trade_id": "TRADE_1",
                        "symbol": "NIFTY50",
                        "signal_type": "BUY",
                        "entry_price": 23400.0,
                        "entry_time": "2024-12-23T10:00:00",
                        "exit_price": 23500.0,
                        "exit_time": "2024-12-23T11:00:00",
                        "exit_reason": "TP_HIT",
                        "pnl": 100.0,
                        "status": "CLOSED"
                    }
                ],
                "count": 1
            },
            "message": "Trade history fetched successfully"
        }
    """
    try:
        broker = get_broker()
        
        trades = broker.get_trades()
        
        return ApiResponse(
            success=True,
            data={
                "trades": trades if trades else [],
                "count": len(trades) if trades else 0
            },
            message="Trade history fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/{symbol}", response_model=ApiResponse)
async def get_symbol_trades(symbol: str) -> ApiResponse:
    """Get trade history for a specific symbol.
    
    Args:
        symbol: Trading symbol
    
    Example:
        GET /api/trading/trades/NIFTY50
        
        Response:
        {
            "success": true,
            "data": {
                "symbol": "NIFTY50",
                "trades": [
                    {
                        "trade_id": "TRADE_1",
                        "signal_type": "BUY",
                        "entry_price": 23400.0,
                        "entry_time": "2024-12-23T10:00:00",
                        "exit_price": 23500.0,
                        "exit_reason": "TP_HIT",
                        "pnl": 100.0
                    }
                ],
                "count": 1
            },
            "message": "Trade history fetched successfully"
        }
    """
    try:
        broker = get_broker()
        
        trades = broker.get_trades(symbol)
        
        return ApiResponse(
            success=True,
            data={
                "symbol": symbol,
                "trades": trades if trades else [],
                "count": len(trades) if trades else 0
            },
            message="Trade history fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching trade history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trade-status", response_model=ApiResponse)
async def get_trade_status() -> ApiResponse:
    """Get current trade status and statistics.
    
    Example:
        GET /api/trading/trade-status
        
        Response:
        {
            "success": true,
            "data": {
                "active_trades": 2,
                "total_trades_closed": 15,
                "win_rate": 60.0,
                "total_pnl": 5000.0,
                "last_trade_time": "2024-12-23T15:30:00"
            },
            "message": "Trade status fetched successfully"
        }
    """
    try:
        broker = get_broker()
        
        status = broker.get_trade_status() if hasattr(broker, 'get_trade_status') else {}
        
        return ApiResponse(
            success=True,
            data=status if status else {
                "active_trades": 0,
                "total_trades_closed": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "last_trade_time": None
            },
            message="Trade status fetched successfully"
        )
    
    except Exception as e:
        logger.error(f"Error fetching trade status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/warmup/load", response_model=ApiResponse)
async def load_warmup_data_endpoint(
    symbols: List[str] = Body(..., example=["NIFTY50", "BANKNIFTY"]),
    lower_timeframe: str = Body("5min"),
    higher_timeframe: str = Body("15min"),
    num_candles: int = Body(30, ge=10, le=500)
) -> ApiResponse:
    """Load historical warmup data for indicators.
    
    This endpoint fetches historical candlestick data for both lower and higher
    timeframes to warm up indicators (ATR, RSI, MACD) before trading starts.
    
    Args:
        symbols: List of trading symbols (e.g., ["NIFTY50", "BANKNIFTY"])
        lower_timeframe: Lower timeframe (default: "5min")
        higher_timeframe: Higher timeframe (default: "15min")
        num_candles: Number of candles to fetch (default: 30, range: 10-500)
    
    Returns:
        ApiResponse with warmup data for each symbol
    """
    from .fastapi_integration import load_warmup_data
    
    try:
        broker = get_broker()
        
        if not broker.is_connected():
            raise HTTPException(status_code=503, detail="Broker not connected")
        
        logger.info(
            f"Loading warmup data for {len(symbols)} symbols: "
            f"{lower_timeframe}, {higher_timeframe}"
        )
        
        warmup_results = load_warmup_data(
            kite_client=broker.kite,
            symbols=symbols,
            lower_timeframe=lower_timeframe,
            higher_timeframe=higher_timeframe,
            num_candles=num_candles
        )
        
        successful = sum(1 for r in warmup_results.values() 
                        if r.get('status') != 'failed')
        
        return ApiResponse(
            success=True,
            data=warmup_results,
            message=f"Warmup data loaded for {successful}/{len(symbols)} symbols"
        )
        
    except Exception as e:
        logger.error(f"Error loading warmup data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/warmup/status", response_model=ApiResponse)
async def get_warmup_status() -> ApiResponse:
    """Get current warmup data status and cached data.
    
    Returns:
        ApiResponse with cached warmup data if available
    """
    from .fastapi_integration import get_warmup_data, get_warmup_config
    
    try:
        warmup_data = get_warmup_data()
        warmup_config = get_warmup_config()
        
        if warmup_data is None:
            return ApiResponse(
                success=False,
                data=None,
                message="No warmup data loaded yet"
            )
        
        symbol_count = len(warmup_data)
        successful = sum(1 for r in warmup_data.values() 
                        if r.get('status') != 'failed')
        
        return ApiResponse(
            success=True,
            data={
                'config': warmup_config,
                'data': warmup_data,
                'summary': {
                    'total_symbols': symbol_count,
                    'successful': successful,
                    'failed': symbol_count - successful
                }
            },
            message=f"Warmup status: {successful}/{symbol_count} symbols ready"
        )
        
    except Exception as e:
        logger.error(f"Error fetching warmup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/market/check-at-open", response_model=ApiResponse)
async def check_market_at_open() -> ApiResponse:
    """Check market status at market open (9:00 AM) and cache for the entire day.
    
    This endpoint should be called once at 9:00 AM to check if the market is open
    (holiday check, weekend check, etc.) and cache the result for the entire day.
    Subsequent calls will use the cached status.
    
    Returns:
        ApiResponse with market status and cache info
    """
    from .market_status import MarketStatus
    
    try:
        broker = get_broker()
        
        market_status = MarketStatus(broker.kite if broker.is_connected() else None)
        result = market_status.check_market_status_at_open()
        
        return ApiResponse(
            success=True,
            data=result,
            message=f"Market status checked and cached: {result['status']}"
        )
        
    except Exception as e:
        logger.error(f"Error checking market status at open: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/status", response_model=ApiResponse)
async def get_market_status() -> ApiResponse:
    """Get current market status (uses cached value if available).
    
    Returns:
        ApiResponse with detailed market status
    """
    from .market_status import MarketStatus
    
    try:
        broker = get_broker()
        
        market_status = MarketStatus(broker.kite if broker.is_connected() else None)
        result = market_status.get_market_status()
        
        return ApiResponse(
            success=True,
            data=result,
            message=result.get('reason', 'Market status retrieved')
        )
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/holidays", response_model=ApiResponse)
async def get_market_holidays(year: Optional[int] = Query(None)) -> ApiResponse:
    """Get NSE market holidays from Upstox API.
    
    Args:
        year: Optional year filter (default: current year)
    
    Returns:
        ApiResponse with holidays dictionary
    """
    from .market_status import MarketStatus
    
    try:
        broker = get_broker()
        
        market_status = MarketStatus(broker.kite if broker.is_connected() else None)
        holidays = market_status.get_holidays(year)
        
        return ApiResponse(
            success=True,
            data={
                'holidays': holidays,
                'count': len(holidays),
                'year': year or datetime.now().year,
                'source': 'Upstox API'
            },
            message=f"Found {len(holidays)} market holidays"
        )
        
    except Exception as e:
        logger.error(f"Error fetching market holidays: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/warmup/indicators/{symbol}", response_model=ApiResponse)
async def get_warmup_indicators(
    symbol: str,
    timeframe: Optional[str] = Query(None, description="Specific timeframe (lower_timeframe or higher_timeframe)")
) -> ApiResponse:
    """Get initialized indicator values for a symbol from warmup data.
    
    Args:
        symbol: Trading symbol (e.g., "NIFTY50")
        timeframe: Optional specific timeframe to retrieve
    
    Returns:
        ApiResponse with ATR, RSI, MACD values
    """
    from .fastapi_integration import get_warmup_data
    
    try:
        warmup_data = get_warmup_data()
        
        if warmup_data is None or symbol not in warmup_data:
            raise HTTPException(
                status_code=404,
                detail=f"No warmup data available for symbol: {symbol}"
            )
        
        symbol_data = warmup_data[symbol]
        
        if symbol_data.get('status') == 'failed':
            raise HTTPException(
                status_code=400,
                detail=f"Warmup failed for symbol: {symbol}. Error: {symbol_data.get('error')}"
            )
        
        indicators = symbol_data.get('indicators', {})
        
        if timeframe and timeframe in indicators:
            indicators = {timeframe: indicators[timeframe]}
        
        return ApiResponse(
            success=True,
            data={
                'symbol': symbol,
                'timeframes': indicators,
                'timestamp': symbol_data.get('timestamp')
            },
            message=f"Warmup indicators for {symbol}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching warmup indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/trading-enabled", response_model=ApiResponse)
async def get_trading_enabled() -> ApiResponse:
    """Check if trading is enabled (market is open).
    
    Returns:
        ApiResponse with trading_enabled flag and current market status
    """
    try:
        from datetime import datetime
        
        market_status = MarketStatus()
        status = market_status.get_market_status()
        is_open = status.get('market_open', False)
        
        return ApiResponse(
            success=True,
            data={
                'trading_enabled': is_open,
                'market_status': status['status'],
                'reason': status.get('reason', ''),
                'current_time': datetime.now().isoformat(),
                'timestamp': datetime.now().isoformat()
            },
            message=f"Trading {'enabled' if is_open else 'disabled'} - Market is {status['status']}"
        )
    
    except Exception as e:
        logger.error(f"Error checking trading status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def include_trading_router(app):
    """Include trading router in FastAPI app.
    
    Args:
        app: FastAPI application instance
    
    Returns:
        FastAPI application with trading router included
    """
    app.include_router(router)
    return app
