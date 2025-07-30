"""
Market data models and value objects.

This module defines the core data structures used throughout the portfolio library
for representing market data, risk metrics, and performance analytics.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


@dataclass
class PriceData:
    """Single price data point with OHLCV information."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adjusted_close: Optional[float] = None


@dataclass
class MarketData:
    """Complete market data for a symbol including historical prices."""
    symbol: str
    prices: List[PriceData]
    current_price: float
    last_updated: datetime
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert price data to pandas DataFrame for analysis."""
        data = []
        for price in self.prices:
            data.append({
                'timestamp': price.timestamp,
                'open': price.open,
                'high': price.high,
                'low': price.low,
                'close': price.close,
                'volume': price.volume,
                'adjusted_close': price.adjusted_close or price.close
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df


@dataclass
class RiskMetrics:
    """Portfolio risk analysis metrics."""
    volatility: float  # Annualized volatility
    sharpe_ratio: float  # Risk-adjusted return
    max_drawdown: float  # Maximum peak-to-trough decline
    var_95: float  # Value at Risk (95% confidence)
    beta: Optional[float] = None  # Beta vs benchmark
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for API serialization."""
        return {
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'var_95': self.var_95,
            'beta': self.beta
        }


@dataclass 
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_return: float  # Total return percentage
    annualized_return: float  # Annualized return percentage
    cumulative_return: float  # Cumulative return from inception
    benchmark_return: Optional[float] = None  # Benchmark comparison
    alpha: Optional[float] = None  # Alpha vs benchmark
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for API serialization."""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return, 
            'cumulative_return': self.cumulative_return,
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha
        }
