"""
Tests for data provider services.
"""

import pytest
import os
from datetime import datetime
import pandas as pd

from portfolio_lib.config import settings
from portfolio_lib.services.data import YFinanceDataService, AlphaVantageDataService

# Check if AlphaVantage key is available
ALPHAVANTAGE_API_KEY = settings.alphavantage_api_key
SKIP_AV_TESTS = not ALPHAVANTAGE_API_KEY


@pytest.mark.integration
class TestDataProviders:
    """Test cases for data provider services."""
    
    def setup_class(self):
        """Set up test fixtures for the class."""
        self.symbols = ["AAPL", "GOOGL"]
        self.start_date = "2023-01-01"
        self.end_date = "2023-01-31"
        self.yfinance_service = YFinanceDataService()
        
        if not SKIP_AV_TESTS:
            self.alphavantage_service = AlphaVantageDataService(api_key=ALPHAVANTAGE_API_KEY)
    
    def _validate_price_history_format(self, data: pd.DataFrame):
        """Validate the format of the price history DataFrame."""
        assert isinstance(data, pd.DataFrame)
        assert not data.empty
        
        # Check for required columns
        required_columns = ["open", "high", "low", "close", "volume"]
        assert all(col in data.columns for col in required_columns)
        
        # Check index type
        assert isinstance(data.index, pd.DatetimeIndex)
        
        # Check data types
        for col in ["open", "high", "low", "close"]:
            assert pd.api.types.is_numeric_dtype(data[col])
        assert pd.api.types.is_integer_dtype(data["volume"])
    
    def test_yfinance_price_history(self):
        """Test fetching price history from yfinance."""
        data = self.yfinance_service.fetch_price_history(
            symbols=self.symbols, 
            start_date=self.start_date, 
            end_date=self.end_date
        )
        
        assert isinstance(data, dict)
        assert len(data) == len(self.symbols)
        
        for symbol, df in data.items():
            assert symbol in self.symbols
            self._validate_price_history_format(df)
    
    def test_yfinance_current_prices(self):
        """Test fetching current prices from yfinance."""
        data = self.yfinance_service.fetch_current_prices(symbols=self.symbols)
        
        assert isinstance(data, dict)
        assert len(data) == len(self.symbols)
        
        for symbol, price in data.items():
            assert symbol in self.symbols
            assert isinstance(price, float)
            assert price > 0
    
    @pytest.mark.skipif(SKIP_AV_TESTS, reason="AlphaVantage API key not configured")
    def test_alphavantage_price_history(self):
        """Test fetching price history from AlphaVantage."""
        data = self.alphavantage_service.fetch_price_history(
            symbols=self.symbols, 
            start_date=self.start_date, 
            end_date=self.end_date
        )
        
        assert isinstance(data, dict)
        assert len(data) == len(self.symbols)
        
        for symbol, df in data.items():
            assert symbol in self.symbols
            self._validate_price_history_format(df)
    
    @pytest.mark.skipif(SKIP_AV_TESTS, reason="AlphaVantage API key not configured")
    def test_alphavantage_current_prices(self):
        """Test fetching current prices from AlphaVantage."""
        data = self.alphavantage_service.fetch_current_prices(symbols=self.symbols)
        
        assert isinstance(data, dict)
        assert len(data) == len(self.symbols)
        
        for symbol, price in data.items():
            assert symbol in self.symbols
            assert isinstance(price, float)
            assert price > 0
    
    def test_data_source_names(self):
        """Test data source names."""
        assert self.yfinance_service.get_data_source_name() == "yfinance"
        
        if not SKIP_AV_TESTS:
            assert self.alphavantage_service.get_data_source_name() == "alphavantage"


if __name__ == "__main__":
    # To run these tests:
    # 1. Ensure you have pytest installed: pip install pytest
    # 2. Set the ALPHAVANTAGE_API_KEY environment variable if you want to run AlphaVantage tests
    # 3. Run from the `portfolio_lib` directory: pytest tests/test_data_providers.py
    pytest.main([__file__, "-v", "-m integration"])

