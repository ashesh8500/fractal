"""
Data services package - Market data providers and abstractions.
"""

from .base import DataService
from .yfinance import YFinanceDataService

# AlphaVantage is optional - only import if alpha-vantage is installed
try:
    from .alphavantage import AlphaVantageDataService
    _ALPHAVANTAGE_AVAILABLE = True
except ImportError:
    _ALPHAVANTAGE_AVAILABLE = False
    AlphaVantageDataService = None

__all__ = [
    "DataService",
    "YFinanceDataService",
]

if _ALPHAVANTAGE_AVAILABLE:
    __all__.append("AlphaVantageDataService")
