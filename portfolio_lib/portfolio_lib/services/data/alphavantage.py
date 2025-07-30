"""
AlphaVantage data service implementation.

This module provides a concrete implementation of the DataService protocol
using the alpha-vantage library to fetch market data from Alpha Vantage API.
"""

import logging
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import time

logger = logging.getLogger(__name__)


class AlphaVantageDataService:
    """Data service implementation using Alpha Vantage API."""
    
    def __init__(self, api_key: str, requests_per_minute: int = 5):
        """
        Initialize the AlphaVantage data service.
        
        Args:
            api_key: Alpha Vantage API key
            requests_per_minute: Rate limit for API calls (default: 5 for free tier)
        """
        if not api_key:
            raise ValueError("Alpha Vantage API key is required")
        
        self.api_key = api_key
        self.requests_per_minute = requests_per_minute
        self._last_request_time = 0.0
        self._request_interval = 60.0 / requests_per_minute  # seconds between requests
        
        try:
            from alpha_vantage.timeseries import TimeSeries
            from alpha_vantage.fundamentaldata import FundamentalData
            self._ts = TimeSeries(key=api_key, output_format='pandas')
            self._fd = FundamentalData(key=api_key, output_format='pandas')
        except ImportError as e:
            logger.error("alpha-vantage library not found. Install with: pip install alpha-vantage")
            raise ImportError("alpha-vantage library is required") from e
            
        logger.info(f"AlphaVantage data service initialized with {requests_per_minute} requests/minute limit")
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting for API calls."""
        current_time = time.time()
        time_since_last_request = current_time - self._last_request_time
        
        if time_since_last_request < self._request_interval:
            sleep_time = self._request_interval - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def fetch_price_history(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data using Alpha Vantage.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            Dictionary mapping symbols to DataFrames with OHLCV data
        """
        logger.info(f"Fetching price history for {len(symbols)} symbols from {start_date} to {end_date}")
        
        result = {}
        
        for i, symbol in enumerate(symbols):
            try:
                self._rate_limit()
                
                logger.debug(f"Fetching data for {symbol} ({i+1}/{len(symbols)})")
                
                # Get daily data (free tier - use get_daily instead of get_daily_adjusted)
                data, meta_data = self._ts.get_daily(symbol=symbol, outputsize='full')
                
                if data is None or data.empty:
                    logger.warning(f"No data found for symbol {symbol}")
                    continue
                
                # Filter by date range
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                
                # Alpha Vantage returns data with newest first, so we need to filter
                mask = (data.index >= start_dt) & (data.index <= end_dt)
                filtered_data = data.loc[mask]
                
                if filtered_data.empty:
                    logger.warning(f"No data in date range for {symbol}")
                    continue
                
                # Standardize column names to match our interface
                # Alpha Vantage daily columns: '1. open', '2. high', '3. low', '4. close', '5. volume'
                # Note: daily endpoint doesn't have adjusted close, so we use regular close
                standardized_data = pd.DataFrame({
                    'open': filtered_data['1. open'],
                    'high': filtered_data['2. high'], 
                    'low': filtered_data['3. low'],
                    'close': filtered_data['4. close'],
                    'volume': filtered_data['5. volume'].astype(int)
                })
                
                # Add adjusted_close as same as close for consistency
                standardized_data['adjusted_close'] = standardized_data['close']
                
                # Sort by date (oldest first)
                standardized_data = standardized_data.sort_index()
                
                result[symbol] = standardized_data
                logger.debug(f"Successfully fetched {len(standardized_data)} days of data for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched data for {len(result)} out of {len(symbols)} symbols")
        return result
    
    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Fetch current market prices using Alpha Vantage.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to current prices
        """
        logger.info(f"Fetching current prices for {len(symbols)} symbols")
        
        result = {}
        
        for i, symbol in enumerate(symbols):
            try:
                self._rate_limit()
                
                logger.debug(f"Fetching current price for {symbol} ({i+1}/{len(symbols)})")
                
                # Use quote endpoint for current price
                data, meta_data = self._ts.get_quote_endpoint(symbol=symbol)
                
                if data is None or data.empty:
                    logger.warning(f"No current price data for {symbol}")
                    continue
                
                # Extract current price from quote data
                # Alpha Vantage quote columns: '01. symbol', '02. open', '03. high', '04. low', '05. price', etc.
                current_price = float(data['05. price'].iloc[0])
                result[symbol] = current_price
                
                logger.debug(f"Current price for {symbol}: ${current_price:.2f}")
                
            except Exception as e:
                logger.error(f"Error fetching current price for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched current prices for {len(result)} out of {len(symbols)} symbols")
        return result
    
    def get_data_source_name(self) -> str:
        """Return the data source name."""
        return "alphavantage"
    
    def is_market_open(self) -> bool:
        """
        Check if market is open.
        
        Note: Alpha Vantage doesn't provide a direct market status endpoint,
        so we use a simple time-based approach.
        """
        # Basic time-based check (US market hours)
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        
        # Monday-Friday, 9:30 AM - 4:00 PM ET (simplified)
        if weekday < 5 and 9 <= hour < 16:
            return True
        
        return False
    
    def get_fundamental_data(self, symbol: str) -> Dict:
        """
        Get fundamental data for a symbol (bonus feature).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with fundamental data
        """
        try:
            self._rate_limit()
            
            logger.info(f"Fetching fundamental data for {symbol}")
            
            # Get company overview
            data, meta_data = self._fd.get_company_overview(symbol=symbol)
            
            if data is None or data.empty:
                logger.warning(f"No fundamental data for {symbol}")
                return {}
            
            # Convert to dictionary and clean up
            fundamental_data = data.to_dict()
            
            # Extract key metrics
            key_metrics = {
                'market_cap': fundamental_data.get('MarketCapitalization', 'N/A'),
                'pe_ratio': fundamental_data.get('PERatio', 'N/A'),
                'dividend_yield': fundamental_data.get('DividendYield', 'N/A'),
                'beta': fundamental_data.get('Beta', 'N/A'),
                'sector': fundamental_data.get('Sector', 'N/A'),
                'industry': fundamental_data.get('Industry', 'N/A'),
                'description': fundamental_data.get('Description', 'N/A')
            }
            
            logger.debug(f"Fundamental data retrieved for {symbol}")
            return key_metrics
            
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {symbol}: {e}")
            return {}
