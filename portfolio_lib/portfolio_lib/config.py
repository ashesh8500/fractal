"""
Configuration for the portfolio library.

This module provides a centralized location for library configuration.
It uses pydantic for type-safe configuration management and supports
loading settings from environment variables and .env files.
"""

import os
from typing import Optional

# Try to import pydantic-settings, but fall back to a simple class if not available
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """Type-safe configuration settings for the library."""

        # Alpha Vantage API key
        alphavantage_api_key: Optional[str] = None

        # Default data provider to use
        default_data_provider: str = "yfinance"

        # Logging level
        log_level: str = "INFO"

        # Model configuration
        model_config = SettingsConfigDict(
            env_prefix="PORTFOLIO_LIB_",  # e.g., PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY
            env_file=".env",  # Load from .env file
            env_file_encoding="utf-8",
            extra="ignore",
        )

    # Instantiate the settings
    settings = Settings()

except ImportError:
    # Fallback to a simple class if pydantic-settings is not installed
    class Settings:
        """Basic configuration fallback if pydantic-settings is not installed."""

        alphavantage_api_key: Optional[str] = os.getenv(
            "PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY"
        )
        default_data_provider: str = "yfinance"
        log_level: str = "INFO"

    settings = Settings()


# Helper function to get a data service instance based on config
def get_data_service(provider: Optional[str] = None):
    """
    Get a data service instance based on the specified provider or default config.

    Args:
        provider: Data provider name ('yfinance' or 'alphavantage')

    Returns:
        Instance of the specified data service
    """
    from .services.data import AlphaVantageDataService, YFinanceDataService

    provider_name = provider or settings.default_data_provider

    if provider_name.lower() == "yfinance":
        return YFinanceDataService()

    elif provider_name.lower() == "alphavantage":
        if not AlphaVantageDataService:
            raise ImportError("alpha-vantage package not installed")

        if not settings.alphavantage_api_key:
            raise ValueError("Alpha Vantage API key not configured")

        return AlphaVantageDataService(api_key=settings.alphavantage_api_key)

    else:
        raise ValueError(f"Unknown data provider: {provider_name}")


# Example usage:
if __name__ == "__main__":
    print("Configuration Settings:")
    print(f"  - Default Data Provider: {settings.default_data_provider}")
    print(
        f"  - AlphaVantage API Key Loaded: {'Yes' if settings.alphavantage_api_key else 'No'}"
    )

    try:
        # Get default data service
        default_service = get_data_service()
        print(f"\\nDefault service: {default_service.get_data_source_name()}")

        # Get specific service
        yfinance_service = get_data_service("yfinance")
        print(f"YFinance service: {yfinance_service.get_data_source_name()}")

        # Try getting AlphaVantage (will fail if key not set)
        if settings.alphavantage_api_key:
            av_service = get_data_service("alphavantage")
            print(f"AlphaVantage service: {av_service.get_data_source_name()}")

    except (ImportError, ValueError) as e:
        print(f"\\nError getting data service: {e}")
