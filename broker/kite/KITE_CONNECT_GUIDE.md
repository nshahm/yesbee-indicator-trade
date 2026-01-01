# Kite Connect Integration Guide

## Overview

This directory contains a complete Kite Connect integration for live trading with FastAPI. It includes:

- **OAuth Authentication**: Secure authentication flow with Kite Connect
- **Trading Endpoints**: REST API for orders, positions, quotes, and account management
- **Configuration Management**: Externalized configuration through YAML files
- **Credential Management**: Secure credential storage and management

## Directory Structure

```
broker/kite/
├── __init__.py                      # Package initialization
├── credentials_manager.py           # Credential management singleton
├── kite_oauth.py                   # OAuth authentication endpoints
├── kite_connect.py                 # Kite Connect API wrapper
├── kite_trading_endpoints.py       # Trading REST API endpoints
├── fastapi_integration.py          # FastAPI integration helper
├── example_app.py                  # Example FastAPI application
└── KITE_CONNECT_GUIDE.md          # This file
```

## Configuration Files

### 1. config/kite-config.yaml

Main configuration file for Kite Connect settings:

```yaml
kite:
  api:
    key: "${KITE_API_KEY:YOUR_KITE_API_KEY}"
    secret: "${KITE_API_SECRET:YOUR_KITE_API_SECRET}"
    access_token: "${KITE_ACCESS_TOKEN:YOUR_KITE_ACCESS_TOKEN}"
  
  trading:
    product: "MIS"  # MIS (Intraday), CNC (Delivery), NRML (Normal)
    exchange: "NSE"
    order_type: "MARKET"
  
  instruments:
    symbols: ["NIFTY50", "BANKNIFTY", "FINNIFTY"]
```

### 2. Credentials in config/kite-config.yaml

All API credentials are stored in the main `config/kite-config.yaml` file:

```yaml
kite:
  api:
    key: "YOUR_KITE_API_KEY"
    secret: "YOUR_KITE_API_SECRET"
    access_token: "YOUR_KITE_ACCESS_TOKEN"
    user_id: "YOUR_USER_ID"
```

Note: The credentials section should not be committed to version control with actual values.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install fastapi uvicorn kiteconnect pydantic pyyaml
```

### 2. Configure Credentials

#### Option A: Environment Variables

```bash
export KITE_API_KEY="your_api_key"
export KITE_API_SECRET="your_api_secret"
export KITE_ACCESS_TOKEN="your_access_token"
export KITE_USER_ID="your_user_id"
```

#### Option B: YAML Configuration File

Update `config/kite-config.yaml` in the `kite.api` section with your credentials:

```yaml
kite:
  api:
    key: "your_api_key"
    secret: "your_api_secret"
    access_token: "your_access_token"
    user_id: "your_user_id"
```

### 3. Run the FastAPI Server

```bash
# Development
uvicorn broker.kite.example_app:app --reload

# Production
gunicorn broker.kite.example_app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

## API Endpoints

### Authentication Endpoints

#### 1. Get Login URL
```
GET /api/auth/login
```

Response:
```json
{
  "login_url": "https://kite.zerodha.com/connect/login?api_key=xxx",
  "message": "Please visit this URL to login and authorize the app"
}
```

#### 2. OAuth Callback
```
GET /api/auth/callback?request_token=xxx
```

Response:
```json
{
  "status": "success",
  "message": "Authentication successful. Access token saved.",
  "access_token": "xxx...",
  "user_id": "ABC123",
  "user_name": "John Doe"
}
```

#### 3. Check Auth Status
```
GET /api/auth/status
```

Response:
```json
{
  "authenticated": true,
  "api_key": "v1s1cg4x3rdoiwq3",
  "message": "Authenticated with valid access token"
}
```

### Trading Endpoints

#### 1. Health Check
```
GET /api/trading/health
```

Response:
```json
{
  "status": "ok",
  "connected": true,
  "message": "Connected to Kite Connect API",
  "timestamp": "2024-12-23T12:00:00"
}
```

#### 2. Get Quotes
```
GET /api/trading/quotes?symbols=NIFTY50,BANKNIFTY
```

Response:
```json
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
```

#### 3. Get Single Quote
```
GET /api/trading/quote/NIFTY50
```

Response:
```json
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
```

#### 4. Place Order
```
POST /api/trading/orders?symbol=NIFTY50&order_type=BUY&quantity=1
```

Response:
```json
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
```

#### 5. Get All Orders
```
GET /api/trading/orders
```

Response:
```json
{
  "success": true,
  "data": {
    "orders": [
      {
        "order_id": "1001",
        "symbol": "NIFTY50",
        "transaction_type": "BUY",
        "quantity": 1,
        "status": "COMPLETE"
      }
    ],
    "count": 1
  },
  "message": "Orders fetched successfully"
}
```

#### 6. Get Order Status
```
GET /api/trading/orders/1001
```

Response:
```json
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
```

#### 7. Cancel Order
```
DELETE /api/trading/orders/1001
```

Response:
```json
{
  "success": true,
  "data": {
    "order_id": "1001",
    "status": "CANCELLED"
  },
  "message": "Order cancelled successfully"
}
```

#### 8. Get Positions
```
GET /api/trading/positions
```

Response:
```json
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
```

#### 9. Get Position for Symbol
```
GET /api/trading/positions/NIFTY50
```

Response:
```json
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
```

#### 10. Get Holdings
```
GET /api/trading/holdings
```

Response:
```json
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
```

#### 11. Get Account Information
```
GET /api/trading/account
```

Response:
```json
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
```

## Integration with Main Trading System

### Using Kite Broker in Your Application

```python
from broker.kite import KiteConnectBroker

# Initialize broker
broker = KiteConnectBroker(config_path="config/kite-config.yaml")

# Check connection
if not broker.is_connected():
    print("Not connected to Kite Connect")
    exit(1)

# Get quotes
quotes = broker.get_quotes(["NIFTY50", "BANKNIFTY"])

# Place order
order_id = broker.place_order(
    symbol="NIFTY50",
    order_type="BUY",
    quantity=1,
    price=None
)

# Get positions
positions = broker.get_positions()

# Get account info
profile = broker.get_profile()
margin = broker.get_margin()
```

### Using with FastAPI

```python
from fastapi import FastAPI
from broker.kite.fastapi_integration import setup_kite_api

app = FastAPI()
app = setup_kite_api(app)

# Your custom routes
@app.get("/custom")
async def custom_endpoint():
    return {"message": "Custom endpoint"}

# Kite routes are now available at:
# - /api/auth/* (authentication)
# - /api/trading/* (trading operations)
```

## Error Handling

All endpoints return consistent JSON responses:

### Success Response
```json
{
  "success": true,
  "data": {},
  "message": "Operation successful",
  "timestamp": "2024-12-23T12:00:00"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error details",
  "message": "User-friendly message",
  "timestamp": "2024-12-23T12:00:00"
}
```

## Configuration Environment Variables

The configuration system supports environment variable expansion:

```yaml
# In kite-config.yaml
api_key: "${KITE_API_KEY:default_value}"
```

This will:
1. Check for `KITE_API_KEY` environment variable
2. Use default value if not set
3. Load from environment if set

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Restrict API access** by IP whitelisting in Kite settings
4. **Rotate access tokens** regularly
5. **Use HTTPS** in production
6. **Implement rate limiting** for API endpoints

## Logging

Configure logging in your application:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/kite_trading.log'),
        logging.StreamHandler()
    ]
)
```

## API Documentation

Access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Troubleshooting

### Connection Issues

```python
broker = KiteConnectBroker()
if not broker.is_connected():
    print("Check API credentials in config/kite-config.yaml under kite.api section")
```

### Order Placement Failures

- Verify symbol is valid for the trading exchange
- Check market hours
- Ensure sufficient margin/balance
- Verify order parameters (quantity, price)

### Quote Retrieval Issues

- Ensure instrument token is correct
- Check market hours
- Verify symbol configuration in kite-config.yaml

## Examples

See `example_app.py` for a complete working example.

## Support

For issues with Kite Connect API, refer to:
- [Kite Connect Documentation](https://kite.trade/)
- [Zerodha API Reference](https://kite.trade/static/documents/Kite_Connect_API_Reference.pdf)

## License

This integration is part of the yesbee-trading system.
