"""Example FastAPI application with Kite Connect integration.

This is a standalone example showing how to use the Kite Connect
trading platform with FastAPI.

Run with:
    uvicorn broker.kite.example_app:app --reload
    
Or for production:
    gunicorn broker.kite.example_app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
"""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .fastapi_integration import create_kite_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_kite_app(
    title="Kite Connect Trading Platform",
    description="Real-time trading through Kite Connect API",
    version="1.0.0"
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for pretty error responses."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
