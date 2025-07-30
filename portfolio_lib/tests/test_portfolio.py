"""
Tests for the Portfolio class.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import pandas as pd
import numpy as np

from portfolio_lib.models.portfolio import Portfolio
from portfolio_lib.services.data.base import DataService


class MockDataService:
    """Mock data service for testing."""
    
    def __init__(self):
        self.fetch_price_history_called = False
        self.fetch_current_prices_called = False
    
    def fetch_price_history(self, symbols, start_date, end_date):
        self.fetch_price_history_called = True
        
        # Generate mock price data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        result = {}
        
        for symbol in symbols:
            # Create realistic-looking price data
            np.random.seed(hash(symbol) % 2**32)  # Consistent data per symbol
            base_price = 100.0
            
            prices = []
            for i, date in enumerate(dates):
                price = base_price + np.random.normal(0, 2) + i * 0.1  # Slight upward trend
                prices.append(price)
            
            df = pd.DataFrame({
                'open': prices,
                'high': [p * 1.02 for p in prices],
                'low': [p * 0.98 for p in prices],
                'close': prices,
                'volume': [1000000] * len(prices)
            }, index=dates)
            
            result[symbol] = df
        
        return result
    
    def fetch_current_prices(self, symbols):
        self.fetch_current_prices_called = True
        
        # Generate mock current prices
        result = {}
        for symbol in symbols:
            np.random.seed(hash(symbol) % 2**32)
            result[symbol] = 100.0 + np.random.normal(0, 5)
        
        return result
    
    def get_data_source_name(self):
        return "mock"
    
    def is_market_open(self):
        return True


class TestPortfolio:
    """Test cases for Portfolio class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_data_service = MockDataService()
        self.sample_holdings = {
            "AAPL": 100.0,
            "GOOGL": 50.0,
            "MSFT": 75.0
        }
    
    def test_portfolio_creation(self):
        """Test basic portfolio creation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        assert portfolio.name == "Test Portfolio"
        assert portfolio.holdings == self.sample_holdings
        assert portfolio.symbols == ["AAPL", "GOOGL", "MSFT"]
        assert portfolio.data_service is self.mock_data_service
        assert isinstance(portfolio.created_at, datetime)
    
    def test_portfolio_validation(self):
        """Test portfolio validation."""
        # Empty holdings should raise error
        with pytest.raises(ValueError, match="Portfolio must have at least one holding"):
            Portfolio("Test", {}, self.mock_data_service)
        
        # Invalid symbol should raise error
        with pytest.raises(ValueError, match="Invalid symbol"):
            Portfolio("Test", {"": 100.0}, self.mock_data_service)
        
        # Invalid shares should raise error
        with pytest.raises(ValueError, match="Invalid shares"):
            Portfolio("Test", {"AAPL": -10.0}, self.mock_data_service)
        
        with pytest.raises(ValueError, match="Invalid shares"):
            Portfolio("Test", {"AAPL": 0.0}, self.mock_data_service)
    
    def test_total_value_calculation(self):
        """Test portfolio total value calculation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        total_value = portfolio.total_value
        
        # Should have called the data service
        assert self.mock_data_service.fetch_current_prices_called
        
        # Should return a positive value
        assert total_value > 0
        
        # Should be roughly equal to sum of (shares * price)
        current_prices = self.mock_data_service.fetch_current_prices(portfolio.symbols)
        expected_value = sum(
            shares * current_prices[symbol] 
            for symbol, shares in self.sample_holdings.items()
        )
        assert abs(total_value - expected_value) < 0.01
    
    def test_current_weights_calculation(self):
        """Test portfolio weights calculation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        weights = portfolio.current_weights
        
        # Should have weights for all symbols
        assert set(weights.keys()) == set(self.sample_holdings.keys())
        
        # Weights should sum to approximately 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01
        
        # All weights should be positive
        for weight in weights.values():
            assert weight >= 0
    
    def test_add_holding(self):
        """Test adding holdings to portfolio."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings.copy(),
            data_service=self.mock_data_service
        )
        
        # Add new holding
        portfolio.add_holding("TSLA", 25.0)
        
        assert "TSLA" in portfolio.holdings
        assert portfolio.holdings["TSLA"] == 25.0
        assert "TSLA" in portfolio.symbols
        
        # Update existing holding
        portfolio.add_holding("AAPL", 150.0)
        assert portfolio.holdings["AAPL"] == 150.0
    
    def test_remove_holding(self):
        """Test removing holdings from portfolio."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings.copy(),
            data_service=self.mock_data_service
        )
        
        # Remove existing holding
        portfolio.remove_holding("AAPL")
        
        assert "AAPL" not in portfolio.holdings
        assert "AAPL" not in portfolio.symbols
        
        # Try to remove non-existent holding
        with pytest.raises(ValueError, match="Symbol TSLA not found"):
            portfolio.remove_holding("TSLA")
    
    def test_risk_metrics(self):
        """Test risk metrics calculation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        risk_metrics = portfolio.risk_metrics
        
        # Should have called price history
        assert self.mock_data_service.fetch_price_history_called
        
        # Risk metrics should be reasonable
        assert risk_metrics.volatility >= 0
        assert isinstance(risk_metrics.sharpe_ratio, float)
        assert risk_metrics.max_drawdown >= 0
        assert isinstance(risk_metrics.var_95, float)
    
    def test_performance_metrics(self):
        """Test performance metrics calculation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        perf_metrics = portfolio.performance_metrics
        
        # Performance metrics should be calculated
        assert isinstance(perf_metrics.total_return, float)
        assert isinstance(perf_metrics.annualized_return, float)
        assert isinstance(perf_metrics.cumulative_return, float)
    
    def test_refresh_data(self):
        """Test data refresh functionality."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        # Get initial value to populate cache
        initial_value = portfolio.total_value
        
        # Reset mock flags
        self.mock_data_service.fetch_current_prices_called = False
        
        # Refresh data
        portfolio.refresh_data()
        
        # Should have fetched fresh data
        assert self.mock_data_service.fetch_current_prices_called
    
    def test_to_dict_serialization(self):
        """Test portfolio serialization to dictionary."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        portfolio_dict = portfolio.to_dict()
        
        # Should contain all expected fields
        expected_fields = {
            'name', 'holdings', 'created_at', 'total_value', 
            'current_weights', 'data_source'
        }
        assert set(portfolio_dict.keys()) == expected_fields
        
        # Values should be correct types
        assert isinstance(portfolio_dict['name'], str)
        assert isinstance(portfolio_dict['holdings'], dict)
        assert isinstance(portfolio_dict['created_at'], str)  # ISO format
        assert isinstance(portfolio_dict['total_value'], float)
        assert isinstance(portfolio_dict['current_weights'], dict)
        assert isinstance(portfolio_dict['data_source'], str)
    
    def test_position_values(self):
        """Test position values calculation."""
        portfolio = Portfolio(
            name="Test Portfolio",
            holdings=self.sample_holdings,
            data_service=self.mock_data_service
        )
        
        position_values = portfolio.get_position_values()
        
        # Should have values for all positions
        assert set(position_values.keys()) == set(self.sample_holdings.keys())
        
        # All values should be positive
        for value in position_values.values():
            assert value >= 0
        
        # Sum should equal total value
        total_from_positions = sum(position_values.values())
        assert abs(total_from_positions - portfolio.total_value) < 0.01


if __name__ == "__main__":
    pytest.main([__file__])
