"""
Abstract base class for data services.

This module defines the `DataService` protocol, which outlines the contract
for all data provider implementations. This allows for a pluggable data service
architecture where different data sources can be used interchangeably.
"""

from typing import List, Protocol, Dict
import pandas as pd


class DataService(Protocol):
    """Abstract protocol for a market data service."""

    def fetch_price_history(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data for multiple symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date for historical data (YYYY-MM-DD)
            end_date: End date for historical data (YYYY-MM-DD)

        Returns:
            Dictionary mapping symbols to pandas DataFrames with OHLCV data.
            DataFrames should be indexed by datetime.
        """
        ...

    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Fetch current market prices for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to their current price.
        """
        ...
        
    def get_data_source_name(self) -> str:
        """
        Return the name of the data source (e.g., 'yfinance', 'alphavantage').
        """
        ...
        
    def is_market_open(self) -> bool:
        """
        Check if the market is currently open.
        
        Returns:
            True if the market is open, False otherwise.
        """
        ...
