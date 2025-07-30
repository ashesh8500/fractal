"""
Core Portfolio class - the heart of the portfolio management system.

This module defines the Portfolio class, which serves as the single source of truth
for portfolio data and operations. It uses dependency injection for data services
to allow for flexible data provider integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from ..services.data.base import DataService
from .market_data import RiskMetrics, PerformanceMetrics
from .strategy import StrategyConfig, BacktestConfig, StrategyResult, BacktestResult

logger = logging.getLogger(__name__)


class Portfolio:
    """
    Core Portfolio class with dependency injection for data services.
    
    This class represents a financial portfolio and provides methods for:
    - Portfolio valuation and analysis
    - Risk metrics calculation
    - Performance measurement
    - Strategy execution (future implementation)
    - Backtesting (future implementation)
    """
    
    def __init__(
        self,
        name: str,
        holdings: Dict[str, float],
        data_service: DataService,
        created_at: Optional[datetime] = None
    ):
        """
        Initialize a Portfolio.
        
        Args:
            name: Portfolio name
            holdings: Dictionary of symbol -> shares
            data_service: Injected data service for market data
            created_at: Portfolio creation timestamp (defaults to now)
        """
        self.name = name
        self.holdings = holdings.copy()
        self.data_service = data_service
        self.created_at = created_at or datetime.now()
        
        # Cached data
        self._price_history: Optional[Dict[str, pd.DataFrame]] = None
        self._current_prices: Optional[Dict[str, float]] = None
        self._last_data_update: Optional[datetime] = None
        
        logger.info(f"Created portfolio '{name}' with {len(holdings)} holdings")
        
        # Validate initial holdings
        self._validate_holdings()
    
    def _validate_holdings(self) -> None:
        """Validate portfolio holdings."""
        if not self.holdings:
            raise ValueError("Portfolio must have at least one holding")
        
        for symbol, shares in self.holdings.items():
            if not isinstance(symbol, str) or not symbol.strip():
                raise ValueError(f"Invalid symbol: {symbol}")
            
            if not isinstance(shares, (int, float)) or shares <= 0:
                raise ValueError(f"Invalid shares for {symbol}: {shares}")
    
    @property
    def symbols(self) -> List[str]:
        """Get list of symbols in the portfolio."""
        return list(self.holdings.keys())
    
    @property
    def total_value(self) -> float:
        """
        Calculate current total portfolio value.
        
        Returns:
            Total portfolio value in USD
        """
        current_prices = self._get_current_prices()
        
        total = 0.0
        for symbol, shares in self.holdings.items():
            if symbol in current_prices:
                total += shares * current_prices[symbol]
            else:
                logger.warning(f"No current price available for {symbol}")
        
        return total
    
    @property
    def current_weights(self) -> Dict[str, float]:
        """
        Calculate current portfolio weights by value.
        
        Returns:
            Dictionary mapping symbols to their weight (0-1)
        """
        current_prices = self._get_current_prices()
        total_value = self.total_value
        
        if total_value <= 0:
            logger.warning("Portfolio has zero or negative value")
            return {symbol: 0.0 for symbol in self.symbols}
        
        weights = {}
        for symbol, shares in self.holdings.items():
            if symbol in current_prices:
                value = shares * current_prices[symbol]
                weights[symbol] = value / total_value
            else:
                weights[symbol] = 0.0
        
        return weights
    
    @property
    def risk_metrics(self) -> RiskMetrics:
        """
        Calculate portfolio risk metrics.
        
        Returns:
            RiskMetrics object with volatility, Sharpe ratio, etc.
        """
        price_history = self._get_price_history()
        
        if not price_history:
            logger.warning("No price history available for risk calculation")
            return RiskMetrics(
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0
            )
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(price_history)
        
        if portfolio_returns.empty:
            logger.warning("No returns data available")
            return RiskMetrics(
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0
            )
        
        # Calculate metrics
        volatility = portfolio_returns.std() * np.sqrt(252)  # Annualized
        sharpe_ratio = (portfolio_returns.mean() * 252) / volatility if volatility > 0 else 0.0
        max_drawdown = self._calculate_max_drawdown(portfolio_returns)
        var_95 = np.percentile(portfolio_returns, 5)  # 95% VaR
        
        return RiskMetrics(
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95
        )
    
    @property
    def performance_metrics(self) -> PerformanceMetrics:
        """
        Calculate portfolio performance metrics.
        
        Returns:
            PerformanceMetrics object with returns and performance data
        """
        price_history = self._get_price_history()
        
        if not price_history:
            logger.warning("No price history available for performance calculation")
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                cumulative_return=0.0
            )
        
        portfolio_returns = self._calculate_portfolio_returns(price_history)
        
        if portfolio_returns.empty:
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                cumulative_return=0.0
            )
        
        # Calculate performance metrics
        cumulative_return = (1 + portfolio_returns).prod() - 1
        total_return = cumulative_return
        
        # Annualized return
        days = len(portfolio_returns)
        if days > 0:
            annualized_return = (1 + cumulative_return) ** (252 / days) - 1
        else:
            annualized_return = 0.0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cumulative_return=cumulative_return
        )
    
    def refresh_data(self) -> None:
        """Refresh market data from the data service."""
        logger.info(f"Refreshing data for portfolio '{self.name}'")
        
        # Clear cached data
        self._price_history = None
        self._current_prices = None
        self._last_data_update = None
        
        # Pre-fetch current prices to warm the cache
        self._get_current_prices()
        
        logger.info("Data refresh completed")
    
    def add_holding(self, symbol: str, shares: float) -> None:
        """
        Add or update a holding in the portfolio.
        
        Args:
            symbol: Stock symbol
            shares: Number of shares
        """
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(f"Invalid symbol: {symbol}")
        
        if not isinstance(shares, (int, float)) or shares <= 0:
            raise ValueError(f"Invalid shares: {shares}")
        
        self.holdings[symbol] = shares
        
        # Clear cached data since holdings changed
        self._price_history = None
        self._current_prices = None
        
        logger.info(f"Added {shares} shares of {symbol} to portfolio '{self.name}'")
    
    def remove_holding(self, symbol: str) -> None:
        """
        Remove a holding from the portfolio.
        
        Args:
            symbol: Stock symbol to remove
        """
        if symbol not in self.holdings:
            raise ValueError(f"Symbol {symbol} not found in portfolio")
        
        del self.holdings[symbol]
        
        # Clear cached data since holdings changed
        self._price_history = None
        self._current_prices = None
        
        logger.info(f"Removed {symbol} from portfolio '{self.name}'")
    
    def run_strategy(self, strategy_name: str, config: StrategyConfig) -> StrategyResult:
        """
        Run a trading strategy on the portfolio.
        
        Args:
            strategy_name: Name of the strategy to run
            config: Strategy configuration
            
        Returns:
            Strategy execution result
        """
        logger.info(f"Running strategy '{strategy_name}' on portfolio '{self.name}'")
        
        # Import here to avoid circular imports
        from ..services.strategy import StrategyService, MomentumStrategy
        
        # Create strategy service and register available strategies
        strategy_service = StrategyService()
        
        # Register built-in strategies
        if strategy_name.lower() == "momentum":
            strategy_service.register_strategy("momentum", MomentumStrategy())
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available strategies: ['momentum']")
        
        # Get required data
        price_history = self._get_price_history()
        current_prices = self._get_current_prices()
        current_weights = self.current_weights
        
        # Execute strategy
        return strategy_service.execute_strategy(
            strategy_name.lower(),
            current_weights,
            price_history,
            current_prices,
            config
        )
    
    def run_backtest(self, strategy_name: str, config: BacktestConfig) -> BacktestResult:
        """
        Run a backtest on the portfolio.
        
        Args:
            strategy_name: Name of the strategy to backtest
            config: Backtest configuration
            
        Returns:
            Backtest result
        """
        logger.info(f"Running backtest '{strategy_name}' on portfolio '{self.name}'")
        
        # Import here to avoid circular imports
        from ..services.strategy import MomentumStrategy
        from ..services.backtesting import BacktestingService
        from .strategy import StrategyConfig
        
        # Create strategy instance
        if strategy_name.lower() == "momentum":
            strategy = MomentumStrategy()
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available strategies: ['momentum']")
        
        # Create strategy config from backtest config
        strategy_config = StrategyConfig(
            name=strategy_name.lower(),
            parameters={},  # Use default parameters
            rebalance_frequency="monthly",  # Default rebalancing
            risk_tolerance=0.1,
            max_position_size=0.3
        )
        
        # Create backtesting service
        backtesting_service = BacktestingService(self.data_service)
        
        # Run backtest
        return backtesting_service.run_backtest(
            strategy,
            strategy_config,
            config,
            self.holdings
        )
    
    def get_position_values(self) -> Dict[str, float]:
        """
        Get current value of each position.
        
        Returns:
            Dictionary mapping symbols to their current value
        """
        current_prices = self._get_current_prices()
        
        values = {}
        for symbol, shares in self.holdings.items():
            if symbol in current_prices:
                values[symbol] = shares * current_prices[symbol]
            else:
                values[symbol] = 0.0
        
        return values
    
    def _get_current_prices(self) -> Dict[str, float]:
        """Get current prices, using cache if available."""
        # Use cached data if it's recent (within 5 minutes)
        if (self._current_prices is not None and 
            self._last_data_update is not None and
            datetime.now() - self._last_data_update < timedelta(minutes=5)):
            return self._current_prices
        
        # Fetch fresh data
        try:
            self._current_prices = self.data_service.fetch_current_prices(self.symbols)
            self._last_data_update = datetime.now()
            logger.debug(f"Fetched current prices for {len(self._current_prices)} symbols")
        except Exception as e:
            logger.error(f"Error fetching current prices: {e}")
            self._current_prices = {}
        
        return self._current_prices or {}
    
    def _get_price_history(self, days: int = 252) -> Dict[str, pd.DataFrame]:
        """Get price history, using cache if available."""
        if self._price_history is not None:
            return self._price_history
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            self._price_history = self.data_service.fetch_price_history(
                self.symbols,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            logger.debug(f"Fetched price history for {len(self._price_history)} symbols")
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            self._price_history = {}
        
        return self._price_history or {}
    
    def _calculate_portfolio_returns(self, price_history: Dict[str, pd.DataFrame]) -> pd.Series:
        """Calculate portfolio returns from price history."""
        if not price_history:
            return pd.Series(dtype=float)
        
        # Get aligned price data
        aligned_prices = self._align_price_data(price_history)
        
        if aligned_prices.empty:
            return pd.Series(dtype=float)
        
        # Calculate portfolio values over time
        weights = self.current_weights
        portfolio_values = pd.Series(0.0, index=aligned_prices.index)
        
        for symbol in self.symbols:
            if symbol in aligned_prices.columns and symbol in weights:
                portfolio_values += weights[symbol] * aligned_prices[symbol]
        
        # Calculate returns
        portfolio_returns = portfolio_values.pct_change().dropna()
        
        return portfolio_returns
    
    def _align_price_data(self, price_history: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Align price data across all symbols."""
        if not price_history:
            return pd.DataFrame()
        
        # Extract close prices for each symbol
        close_prices = {}
        for symbol, df in price_history.items():
            if 'close' in df.columns:
                close_prices[symbol] = df['close']
        
        if not close_prices:
            return pd.DataFrame()
        
        # Combine into single DataFrame
        aligned = pd.DataFrame(close_prices)
        
        # Forward fill missing values
        aligned = aligned.ffill().dropna()
        
        return aligned
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns series."""
        if returns.empty:
            return 0.0
        
        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()
        
        # Calculate running maximum
        running_max = cumulative.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max
        
        # Return maximum drawdown (most negative value)
        return abs(drawdown.min())
    
    def to_dict(self) -> Dict:
        """Convert portfolio to dictionary for serialization."""
        return {
            'name': self.name,
            'holdings': self.holdings,
            'created_at': self.created_at.isoformat(),
            'total_value': self.total_value,
            'current_weights': self.current_weights,
            'data_source': self.data_service.get_data_source_name()
        }
