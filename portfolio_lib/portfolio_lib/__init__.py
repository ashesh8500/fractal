"""
Portfolio Library - A standalone Python library for portfolio management and financial analysis.

This library provides core functionality for:
- Portfolio creation and management
- Market data fetching from multiple providers (yfinance, alphavantage)
- Strategy execution and backtesting
- Risk metrics and performance analysis

The library is designed with dependency injection for maximum flexibility and testability.
It can be used independently in Jupyter notebooks, scripts, or as part of a larger application.
"""

from .models.portfolio import Portfolio
from .models.market_data import PriceData, MarketData, RiskMetrics, PerformanceMetrics
from .models.strategy import StrategyConfig, BacktestConfig, StrategyResult, BacktestResult
from .services.data.base import DataService
from .services.data.yfinance import YFinanceDataService

# Version information
__version__ = "0.1.0"
__author__ = "Ashesh Kaji"

# Public API
__all__ = [
    # Core models
    "Portfolio",
    "PriceData",
    "MarketData", 
    "RiskMetrics",
    "PerformanceMetrics",
    
    # Strategy models
    "StrategyConfig",
    "BacktestConfig", 
    "StrategyResult",
    "BacktestResult",
    
    # Services
    "DataService",
    "YFinanceDataService",
]
