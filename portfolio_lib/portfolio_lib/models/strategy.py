"""
Strategy and backtesting models.

This module defines data structures for strategy configuration, execution results,
and backtesting outcomes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum


class TradeAction(Enum):
    """Trade action types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Trade:
    """Individual trade recommendation or execution."""
    symbol: str
    action: TradeAction
    quantity: float
    price: Optional[float] = None
    timestamp: Optional[datetime] = None
    reason: Optional[str] = None  # Reasoning for the trade


@dataclass
class StrategyConfig:
    """Configuration for strategy execution."""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Common strategy parameters
    rebalance_frequency: str = "monthly"  # daily, weekly, monthly, quarterly
    risk_tolerance: float = 0.1  # 0.0 - 1.0 scale
    max_position_size: float = 0.3  # Maximum weight per position
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            'name': self.name,
            'parameters': self.parameters,
            'rebalance_frequency': self.rebalance_frequency,
            'risk_tolerance': self.risk_tolerance,
            'max_position_size': self.max_position_size
        }


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    
    # Backtest settings
    commission: float = 0.001  # 0.1% commission per trade
    slippage: float = 0.0005  # 0.05% slippage
    benchmark: str = "SPY"  # Benchmark symbol for comparison
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'commission': self.commission,
            'slippage': self.slippage,
            'benchmark': self.benchmark
        }


@dataclass
class StrategyResult:
    """Result of strategy execution."""
    strategy_name: str
    timestamp: datetime
    trades: List[Trade]
    expected_return: float
    confidence: float
    new_weights: Dict[str, float]  # Recommended new portfolio weights
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            'strategy_name': self.strategy_name,
            'timestamp': self.timestamp.isoformat(),
            'trades': [
                {
                    'symbol': trade.symbol,
                    'action': trade.action.value,
                    'quantity': trade.quantity,
                    'price': trade.price,
                    'timestamp': trade.timestamp.isoformat() if trade.timestamp else None,
                    'reason': trade.reason
                }
                for trade in self.trades
            ],
            'expected_return': self.expected_return,
            'confidence': self.confidence,
            'new_weights': self.new_weights
        }


@dataclass
class BacktestResult:
    """Result of portfolio backtesting."""
    strategy_name: str
    config: BacktestConfig
    start_date: datetime
    end_date: datetime
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Benchmark comparison
    benchmark_return: float
    alpha: float
    beta: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    
    # Historical data
    daily_returns: List[float] = field(default_factory=list)
    portfolio_values: List[float] = field(default_factory=list)
    timestamps: List[datetime] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API serialization."""
        return {
            'strategy_name': self.strategy_name,
            'config': self.config.to_dict(),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'volatility': self.volatility,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha,
            'beta': self.beta,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'daily_returns': self.daily_returns,
            'portfolio_values': self.portfolio_values,
            'timestamps': [ts.isoformat() for ts in self.timestamps]
        }
