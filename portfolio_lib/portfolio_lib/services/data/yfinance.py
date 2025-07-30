"""
YFinance data service implementation.

This module provides a concrete implementation of the DataService protocol
using the yfinance library to fetch market data from Yahoo Finance.
"""

import logging
from typing import Dict, List
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class YFinanceDataService:
    """Data service implementation using yfinance."""
    
    def __init__(self):
        """Initialize the YFinance data service."""
        try:
            import yfinance as yf
            self._yf = yf
        except ImportError as e:
            logger.error("yfinance library not found. Install with: pip install yfinance")
            raise ImportError("yfinance library is required") from e
            
        logger.info("YFinance data service initialized")
    
    def fetch_price_history(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical price data using yfinance.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            Dictionary mapping symbols to DataFrames with OHLCV data
        """
        logger.info(f"Fetching price history for {len(symbols)} symbols from {start_date} to {end_date}")
        
        result = {}
        
        for symbol in symbols:
            try:
                ticker = self._yf.Ticker(symbol)
                
                # Fetch historical data
                hist = ticker.history(start=start_date, end=end_date)
                
                if hist.empty:
                    logger.warning(f"No data found for symbol {symbol}")
                    continue
                
                # Standardize column names (yfinance uses title case)
                hist.columns = hist.columns.str.lower()
                
                # Ensure we have the required columns
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in hist.columns]
                
                if missing_columns:
                    logger.warning(f"Missing columns for {symbol}: {missing_columns}")
                    continue
                
                result[symbol] = hist
                logger.debug(f"Successfully fetched {len(hist)} days of data for {symbol}")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched data for {len(result)} out of {len(symbols)} symbols")
        return result
    
    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Fetch current market prices using yfinance.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Dictionary mapping symbols to current prices
        """
        logger.info(f"Fetching current prices for {len(symbols)} symbols")
        
        result = {}
        
        try:
            # Use yfinance download for current prices (1 day)
            tickers = " ".join(symbols)
            data = self._yf.download(tickers, period="1d", interval="1d", group_by="ticker")
            
            if len(symbols) == 1:
                # Single symbol case
                symbol = symbols[0]
                if not data.empty and 'Close' in data.columns:
                    result[symbol] = float(data['Close'].iloc[-1])
                    
            else:
                # Multiple symbols case
                for symbol in symbols:
                    try:
                        if symbol in data.columns.levels[0]:
                            close_price = data[symbol]['Close'].iloc[-1]
                            if pd.notna(close_price):
                                result[symbol] = float(close_price)
                            else:
                                logger.warning(f"NaN price for {symbol}")
                        else:
                            logger.warning(f"No data found for {symbol}")
                    except (KeyError, IndexError) as e:
                        logger.warning(f"Error getting current price for {symbol}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error fetching current prices: {e}")
            # Fallback: try individual ticker approach
            for symbol in symbols:
                try:
                    ticker = self._yf.Ticker(symbol)
                    info = ticker.info
                    
                    # Try different price fields
                    price = (
                        info.get('regularMarketPrice') or 
                        info.get('currentPrice') or 
                        info.get('previousClose')
                    )
                    
                    if price:
                        result[symbol] = float(price)
                        
                except Exception as symbol_e:
                    logger.warning(f"Failed to get current price for {symbol}: {symbol_e}")
                    continue
        
        logger.info(f"Successfully fetched current prices for {len(result)} out of {len(symbols)} symbols")
        return result
    
    def get_data_source_name(self) -> str:
        """Return the data source name."""
        return "yfinance"
    
    def is_market_open(self) -> bool:
        """
        Check if market is open (simplified implementation).
        
        Note: This is a basic implementation. For production use,
        consider using a more sophisticated market hours API.
        """
        try:
            # Try to get current market status from a major index
            spy = self._yf.Ticker("SPY")
            info = spy.info
            
            # Check market state if available
            market_state = info.get('marketState', 'UNKNOWN')
            return market_state in ['REGULAR', 'PRE', 'POST']
            
        except Exception as e:
            logger.warning(f"Could not determine market status: {e}")
            
            # Fallback: basic time-based check (US market hours)
            now = datetime.now()
            weekday = now.weekday()  # 0=Monday, 6=Sunday
            hour = now.hour
            
            # Basic check: Monday-Friday, 9:30 AM - 4:00 PM ET (simplified)
            if weekday < 5 and 9 <= hour < 16:
                return True
            
            return False
