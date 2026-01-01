"""Kite Connect OAuth authentication endpoints."""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from kiteconnect import KiteConnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Store Kite instance temporarily during OAuth flow
_kite_instance: Optional[KiteConnect] = None


class LoginURLResponse(BaseModel):
    """Response containing Kite login URL."""

    login_url: str
    message: str


class CallbackRequest(BaseModel):
    """OAuth callback request with request token."""

    request_token: str


class AuthStatusResponse(BaseModel):
    """Authentication status response."""

    authenticated: bool
    api_key: Optional[str] = None
    message: str


def get_config_path() -> Path:
    """Get the path to Kite configuration file."""
    return Path(
        os.getenv(
            "KITE_CONFIG_PATH",
            "config/kite-config.yaml",
        )
    )


def load_api_credentials() -> dict:
    """Load API key and secret from kite-config.yaml."""
    config_path = get_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    api_config = config.get("kite", {}).get("api", {})
    
    return {
        "api_key": api_config.get("key"),
        "api_secret": api_config.get("secret"),
    }


def save_access_token(access_token: str) -> None:
    """Save access token to kite-config.yaml."""
    config_path = get_config_path()
    
    # Load existing configuration
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}
    
    # Update access token in kite.api section
    if "kite" not in config:
        config["kite"] = {}
    if "api" not in config["kite"]:
        config["kite"]["api"] = {}
    
    config["kite"]["api"]["access_token"] = access_token
    
    # Save back to file
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    logger.info(f"Access token saved to {config_path}")


@router.get("/")
async def auth_root() -> dict:
    """Authentication API root endpoint.
    
    Returns information about available authentication endpoints.
    
    Example:
        GET /api/auth
        
        Response:
        {
            "name": "Kite Connect OAuth Authentication",
            "endpoints": {
                "login": "/api/auth/login",
                "callback": "/api/auth/callback",
                "status": "/api/auth/status"
            }
        }
    """
    return {
        "name": "Kite Connect OAuth Authentication",
        "description": "OAuth 2.0 authentication for Kite Connect API",
        "endpoints": {
            "login": {
                "path": "/api/auth/login",
                "method": "GET",
                "description": "Generate Kite Connect login URL"
            },
            "callback": {
                "path": "/api/auth/callback",
                "method": "POST",
                "description": "Exchange request token for access token"
            },
            "status": {
                "path": "/api/auth/status",
                "method": "GET",
                "description": "Check authentication status"
            }
        },
        "documentation": "/docs"
    }


@router.get("/login", response_model=LoginURLResponse)
async def get_login_url() -> LoginURLResponse:
    """Generate Kite Connect login URL.
    
    Returns:
        LoginURLResponse with the login URL to redirect user to
    
    Example:
        GET /api/auth/login
        
        Response:
        {
            "login_url": "https://kite.zerodha.com/connect/login?api_key=xxx",
            "message": "Please visit this URL to login and authorize the app"
        }
    """
    global _kite_instance
    
    try:
        # Load API credentials
        creds = load_api_credentials()
        api_key = creds.get("api_key")
        
        if not api_key or api_key == "YOUR_KITE_API_KEY":
            raise HTTPException(
                status_code=400,
                detail="API key not configured. Please update config/kite-config.yaml"
            )
        
        # Create Kite instance
        _kite_instance = KiteConnect(api_key=api_key)
        
        # Generate login URL
        login_url = _kite_instance.login_url()
        
        return LoginURLResponse(
            login_url=login_url,
            message="Please visit this URL to login and authorize the app. "
                   "After login, you'll be redirected with a request_token. "
                   "Use the /api/auth/callback endpoint with that token."
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating login URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate login URL: {str(e)}")


@router.get("/callback")
async def handle_callback(request_token: str = Query(..., description="Request token from Kite redirect")) -> dict:
    """Handle OAuth callback and exchange request token for access token.
    
    Args:
        request_token: The request token received from Kite after user authorization
    
    Returns:
        Success message with access token info
    
    Example:
        POST /api/auth/callback?request_token=xxx
        
        Response:
        {
            "status": "success",
            "message": "Authentication successful. Access token saved.",
            "access_token": "xxx..."
        }
    """
    global _kite_instance
    
    if not _kite_instance:
        raise HTTPException(
            status_code=400,
            detail="No active login session. Please call /api/auth/login first"
        )
    
    try:
        # Load API secret
        creds = load_api_credentials()
        api_secret = creds.get("api_secret")
        
        if not api_secret or api_secret == "YOUR_KITE_API_SECRET":
            raise HTTPException(
                status_code=400,
                detail="API secret not configured. Please update config/kite-config.yaml"
            )
        
        # Exchange request token for access token
        data = _kite_instance.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        # Save access token to file
        save_access_token(access_token)
        
        # Set access token in Kite instance
        _kite_instance.set_access_token(access_token)
        
        logger.info("Successfully authenticated and saved access token")
        
        return {
            "status": "success",
            "message": "Authentication successful. Access token saved to config/kite-config.yaml",
            "access_token": access_token[:20] + "...",  # Show partial token for security
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
        }
        
    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status() -> AuthStatusResponse:
    """Check current authentication status.
    
    Returns:
        AuthStatusResponse with authentication status
    
    Example:
        GET /api/auth/status
        
        Response:
        {
            "authenticated": true,
            "api_key": "v1s1cg4x3rdoiwq3",
            "message": "Authenticated with valid access token"
        }
    """
    try:
        config_path = get_config_path()
        
        if not config_path.exists():
            return AuthStatusResponse(
                authenticated=False,
                message="Credentials file not found"
            )
        
        with open(config_path) as f:
            config = yaml.safe_load(f) or {}
        
        api_config = config.get("kite", {}).get("api", {})
        api_key = api_config.get("key")
        access_token = api_config.get("access_token")
        
        if not api_key or api_key == "YOUR_KITE_API_KEY":
            return AuthStatusResponse(
                authenticated=False,
                message="API key not configured"
            )
        
        if not access_token or access_token == "YOUR_KITE_ACCESS_TOKEN":
            return AuthStatusResponse(
                authenticated=False,
                api_key=api_key,
                message="Access token not configured. Please login using /api/auth/login"
            )
        
        return AuthStatusResponse(
            authenticated=True,
            api_key=api_key,
            message="Authenticated with valid access token"
        )
        
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return AuthStatusResponse(
            authenticated=False,
            message=f"Error checking status: {str(e)}"
        )


def include_auth_router(app):
    """Include authentication router in FastAPI app."""
    app.include_router(router)
    return app
