"""
Base strategy service and protocol definitions.

This module defines the core strategy execution framework with a protocol-based
approach allowing for multiple strategy implementations.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Protocol
import pandas as pd
import numpy as np

from portfolio_lib.models.strategy import (
    StrategyConfig, StrategyResult, Trade, TradeAction
)

logger = logging.getLogger(__name__)


class StrategyProtocol(Protocol):
    """Protocol for strategy implementations."""
    
    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig
    ) -> StrategyResult:
        """Execute the strategy and return recommendations."""
        ...


class BaseStrategy(ABC):
    """Abstract base class for strategy implementations."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig
    ) -> StrategyResult:
        """Execute the strategy and return recommendations."""
        pass
    
    def _validate_inputs(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float]
    ) -> None:
        """Validate strategy inputs."""
        if not portfolio_weights:
            raise ValueError("Portfolio weights cannot be empty")
        
        if not price_history:
            raise ValueError("Price history cannot be empty")
        
        if not current_prices:
            raise ValueError("Current prices cannot be empty")
    
    def _calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate returns from price series."""
        return prices.pct_change().dropna()
    
    def _calculate_volatility(self, returns: pd.Series, annualize: bool = True) -> float:
        """Calculate volatility from return series."""
        vol = returns.std()
        return vol * np.sqrt(252) if annualize else vol


class StrategyService:
    """Service for managing and executing trading strategies."""
    
    def __init__(self):
        self._strategies: Dict[str, StrategyProtocol] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_strategy(self, name: str, strategy: StrategyProtocol) -> None:
        """Register a new strategy."""
        self._strategies[name] = strategy
        self.logger.info(f"Registered strategy: {name}")
    
    def get_available_strategies(self) -> List[str]:
        """Get list of registered strategy names."""
        return list(self._strategies.keys())
    
    def execute_strategy(
        self,
        strategy_name: str,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig
    ) -> StrategyResult:
        """Execute a specific strategy."""
        if strategy_name not in self._strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found. Available: {self.get_available_strategies()}")
        
        strategy = self._strategies[strategy_name]
        
        self.logger.info(f"Executing strategy: {strategy_name}")
        
        try:
            result = strategy.execute(portfolio_weights, price_history, current_prices, config)
            self.logger.info(f"Strategy {strategy_name} executed successfully. Generated {len(result.trades)} trades.")
            return result
        except Exception as e:
            self.logger.error(f"Error executing strategy {strategy_name}: {e}")
            raise
