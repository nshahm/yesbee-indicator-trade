"""Global credentials manager for trading modules."""

import logging
import os
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)


class KiteCredentials:
    """Container for Kite API credentials."""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, user_id: Optional[str] = None):
        """Initialize credentials.
        
        Args:
            api_key: Kite API key
            api_secret: Kite API secret
            access_token: Kite access token
            user_id: Optional user ID
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.user_id = user_id


class CredentialsManager:
    """Singleton-like manager for API credentials."""

    _instance: Optional["CredentialsManager"] = None
    _credentials: Optional[KiteCredentials] = None

    def __new__(cls) -> "CredentialsManager":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load_credentials(cls, config_path: Optional[str] = None) -> "CredentialsManager":
        """Load credentials from kite-config.yaml file.

        Args:
            config_path: Path to kite-config.yaml file (defaults to config/kite-config.yaml)

        Returns:
            CredentialsManager instance
            
        Raises:
            FileNotFoundError: If configuration file not found
        """
        instance = cls()
        try:
            if config_path is None:
                config_path = os.getenv("KITE_CONFIG_PATH", "config/kite-config.yaml")
            
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_file}")
            
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            kite_config = config.get("kite", {})
            api_config = kite_config.get("api", {})
            
            instance._credentials = KiteCredentials(
                api_key=api_config.get("key", ""),
                api_secret=api_config.get("secret", ""),
                access_token=api_config.get("access_token", ""),
                user_id=api_config.get("user_id")
            )
            logger.info("Credentials loaded successfully from kite-config.yaml")
        except FileNotFoundError as e:
            logger.error(f"Failed to load credentials: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse configuration file: {e}")
            raise
        return instance

    @classmethod
    def get_credentials(cls) -> KiteCredentials:
        """Get loaded credentials.

        Returns:
            KiteCredentials with api_key, api_secret, and access_token

        Raises:
            RuntimeError: If credentials not loaded yet
        """
        instance = cls()
        if instance._credentials is None:
            raise RuntimeError(
                "Credentials not loaded. Call CredentialsManager.load_credentials() first"
            )
        return instance._credentials

    @classmethod
    def is_loaded(cls) -> bool:
        """Check if credentials are loaded."""
        instance = cls()
        return instance._credentials is not None

    @classmethod
    def get_api_key(cls) -> str:
        """Get API key."""
        return cls.get_credentials().api_key

    @classmethod
    def get_api_secret(cls) -> str:
        """Get API secret."""
        return cls.get_credentials().api_secret

    @classmethod
    def get_access_token(cls) -> str:
        """Get access token."""
        return cls.get_credentials().access_token

    @classmethod
    def get_user_id(cls) -> Optional[str]:
        """Get user ID."""
        return cls.get_credentials().user_id

    @classmethod
    def reset(cls) -> None:
        """Reset credentials (useful for testing)."""
        instance = cls()
        instance._credentials = None
        logger.info("Credentials reset")
