"""
Backtesting Service Implementation.

This module provides comprehensive backtesting functionality for trading strategies,
including performance metrics, risk analysis, and comparison to benchmarks.
"""

import logging
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import (
    BacktestConfig,
    BacktestResult,
    StrategyConfig,
    Trade,
    TradeAction,
)
from portfolio_lib.services.data.base import DataService
from portfolio_lib.services.strategy.base import StrategyProtocol

logger = logging.getLogger(__name__)


class BacktestingService:
    """Service for running comprehensive backtests on trading strategies."""

    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self.logger = logging.getLogger(__name__)

    def run_backtest(
        self,
        strategy: StrategyProtocol,
        strategy_config: StrategyConfig,
        backtest_config: BacktestConfig,
        initial_holdings: Dict[str, float],
    ) -> BacktestResult:
        """
        Run a comprehensive backtest of a strategy.

        Args:
            strategy: The strategy to backtest
            strategy_config: Configuration for the strategy
            backtest_config: Backtesting parameters
            initial_holdings: Starting portfolio holdings (symbol -> shares)

        Returns:
            BacktestResult with performance metrics and historical data
        """
        self.logger.info(
            f"Starting backtest for strategy '{strategy_config.name}' from {backtest_config.start_date} to {backtest_config.end_date}"
        )

        # Get historical data for all symbols
        all_symbols = list(initial_holdings.keys())
        if backtest_config.benchmark not in all_symbols:
            all_symbols.append(backtest_config.benchmark)

        # Fetch price history
        price_history = self.data_service.fetch_price_history(
            all_symbols,
            backtest_config.start_date.strftime("%Y-%m-%d"),
            backtest_config.end_date.strftime("%Y-%m-%d"),
        )

        if not price_history:
            raise ValueError("No price history available for backtesting")

        # Normalize timezone awareness across all price history indices to avoid tz-aware/naive comparison errors
        for symbol, df in list(price_history.items()):
            try:
                if hasattr(df.index, "tz") and df.index.tz is not None:
                    price_history[symbol] = df.tz_localize(None)
            except Exception:
                # If normalization fails, keep original to avoid data loss; downstream code has additional guards
                pass

        # Run the backtest simulation
        simulation_result = self._run_simulation(
            strategy, strategy_config, backtest_config, initial_holdings, price_history
        )

        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(
            simulation_result, backtest_config, price_history
        )

        return BacktestResult(
            strategy_name=strategy_config.name,
            config=backtest_config,
            start_date=backtest_config.start_date,
            end_date=backtest_config.end_date,
            **performance_metrics,
            **simulation_result,
        )

    def _run_simulation(
        self,
        strategy: StrategyProtocol,
        strategy_config: StrategyConfig,
        backtest_config: BacktestConfig,
        initial_holdings: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
    ) -> Dict:
        """Run the backtesting simulation."""

        # Initialize simulation state
        current_holdings = initial_holdings.copy()
        cash = backtest_config.initial_capital
        portfolio_values = []
        daily_returns = []
        timestamps = []
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        # Record of all executed trades with metadata for plotting/analysis
        executed_trades: List[Dict] = []

        # Get aligned dates from price history
        all_dates = set()
        for df in price_history.values():
            # Ensure tz-naive for consistent comparisons
            idx = df.index
            try:
                if hasattr(idx, "tz") and idx.tz is not None:
                    idx = idx.tz_localize(None)
            except Exception:
                pass
            all_dates.update(idx)

        simulation_dates = sorted(list(all_dates))

        # Filter dates to backtest period (use tz-naive comparison by converting to dates)
        start_date_naive = backtest_config.start_date.date()
        end_date_naive = backtest_config.end_date.date()
        simulation_dates = [
            date
            for date in simulation_dates
            if start_date_naive
            <= getattr(date, "date", lambda: date)()
            <= end_date_naive
        ]

        if len(simulation_dates) < 2:
            raise ValueError("Insufficient data for backtesting period")

        prev_portfolio_value = backtest_config.initial_capital

        # Rebalancing frequency settings
        rebalance_days = self._get_rebalance_frequency_days(
            strategy_config.rebalance_frequency
        )
        last_rebalance_date = None

        for i, current_date in enumerate(simulation_dates):
            # Get current prices for this date
            current_prices = {}
            for symbol, df in price_history.items():
                if current_date in df.index:
                    current_prices[symbol] = df.loc[current_date, "close"]

            # Calculate current portfolio value
            portfolio_value = cash
            current_weights = {}

            for symbol, shares in current_holdings.items():
                if symbol in current_prices:
                    position_value = shares * current_prices[symbol]
                    portfolio_value += position_value
                    current_weights[symbol] = position_value / max(
                        portfolio_value, 1e-10
                    )
                else:
                    current_weights[symbol] = 0.0

            # Store portfolio value and calculate daily return
            portfolio_values.append(portfolio_value)
            timestamps.append(current_date)

            if i > 0:
                daily_return = (
                    portfolio_value - prev_portfolio_value
                ) / prev_portfolio_value
                daily_returns.append(daily_return)

            prev_portfolio_value = portfolio_value

            # Check if it's time to rebalance
            should_rebalance = (
                last_rebalance_date is None
                or (current_date - last_rebalance_date).days >= rebalance_days
            )

            if (
                should_rebalance and i < len(simulation_dates) - 1
            ):  # Don't rebalance on last day
                try:
                    # Execute strategy
                    strategy_result = strategy.execute(
                        current_weights,
                        {
                            symbol: df[df.index <= current_date]
                            for symbol, df in price_history.items()
                        },
                        current_prices,
                        strategy_config,
                    )

                    # Execute trades
                    trade_stats = self._execute_trades(
                        strategy_result.trades,
                        current_holdings,
                        cash,
                        current_prices,
                        backtest_config,
                    )

                    current_holdings = trade_stats["new_holdings"]
                    cash = trade_stats["new_cash"]
                    total_trades += trade_stats["num_trades"]
                    winning_trades += trade_stats["winning_trades"]
                    losing_trades += trade_stats["losing_trades"]

                    # Accumulate executed trade metadata
                    # Attach the current_date to any trades that were missing a timestamp
                    for t in trade_stats.get("executed", []):
                        if t.get("timestamp") is None:
                            t["timestamp"] = current_date
                        executed_trades.append(t)

                    last_rebalance_date = current_date

                except Exception as e:
                    self.logger.warning(
                        f"Strategy execution failed on {current_date}: {e}"
                    )
                    continue

        return {
            "portfolio_values": portfolio_values,
            "daily_returns": daily_returns,
            "timestamps": timestamps,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            # Expose executed trades for downstream analytics/plotting
            "executed_trades": executed_trades,
        }

    def _execute_trades(
        self,
        trades: List[Trade],
        current_holdings: Dict[str, float],
        cash: float,
        current_prices: Dict[str, float],
        config: BacktestConfig,
    ) -> Dict:
        """Execute trades and update portfolio state."""
        new_holdings = current_holdings.copy()
        new_cash = cash
        num_trades = 0
        winning_trades = 0
        losing_trades = 0
        executed: List[Dict] = []

        for trade in trades:
            if trade.symbol not in current_prices:
                continue

            price = current_prices[trade.symbol]
            trade_value = trade.quantity * price
            commission = trade_value * config.commission
            slippage = trade_value * config.slippage
            total_cost = commission + slippage

            if trade.action == TradeAction.BUY:
                total_needed = trade_value + total_cost
                if new_cash >= total_needed:
                    new_holdings[trade.symbol] = (
                        new_holdings.get(trade.symbol, 0) + trade.quantity
                    )
                    new_cash -= total_needed
                    num_trades += 1
                    executed.append(
                        {
                            "symbol": trade.symbol,
                            "action": "buy",
                            "quantity": float(trade.quantity),
                            "price": float(price),
                            "gross_value": float(trade_value),
                            "commission": float(commission),
                            "slippage": float(slippage),
                            "total_cost": float(total_cost),
                            "net_cash_delta": float(-total_needed),
                            "timestamp": trade.timestamp,
                            "reason": trade.reason,
                        }
                    )

            elif trade.action == TradeAction.SELL:
                current_shares = new_holdings.get(trade.symbol, 0)
                if current_shares >= trade.quantity:
                    new_holdings[trade.symbol] = current_shares - trade.quantity
                    proceeds = trade_value - total_cost
                    new_cash += proceeds
                    num_trades += 1
                    executed.append(
                        {
                            "symbol": trade.symbol,
                            "action": "sell",
                            "quantity": float(trade.quantity),
                            "price": float(price),
                            "gross_value": float(trade_value),
                            "commission": float(commission),
                            "slippage": float(slippage),
                            "total_cost": float(total_cost),
                            "net_cash_delta": float(proceeds),
                            "timestamp": trade.timestamp,
                            "reason": trade.reason,
                        }
                    )

                    # Simple heuristic for winning/losing trades
                    if proceeds > trade_value * 0.95:  # Rough breakeven after costs
                        winning_trades += 1
                    else:
                        losing_trades += 1

        return {
            "new_holdings": new_holdings,
            "new_cash": new_cash,
            "num_trades": num_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "executed": executed,
        }

    def _calculate_performance_metrics(
        self,
        simulation_result: Dict,
        config: BacktestConfig,
        price_history: Dict[str, pd.DataFrame],
    ) -> Dict:
        """Calculate comprehensive performance metrics."""
        portfolio_values = simulation_result["portfolio_values"]
        daily_returns = simulation_result["daily_returns"]

        if not daily_returns:
            return self._empty_performance_metrics()

        returns_series = pd.Series(daily_returns)

        # Basic performance metrics
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[
            0
        ]
        days = len(portfolio_values)
        annualized_return = (1 + total_return) ** (252 / days) - 1 if days > 0 else 0.0

        # Risk metrics
        volatility = returns_series.std() * np.sqrt(252)
        sharpe_ratio = (
            (returns_series.mean() * 252) / volatility if volatility > 0 else 0.0
        )
        max_drawdown = self._calculate_max_drawdown(portfolio_values)

        # Benchmark comparison
        benchmark_metrics = self._calculate_benchmark_metrics(
            config.benchmark, price_history, config.start_date, config.end_date
        )

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            **benchmark_metrics,
        }

    def _calculate_benchmark_metrics(
        self,
        benchmark_symbol: str,
        price_history: Dict[str, pd.DataFrame],
        start_date: datetime,
        end_date: datetime,
    ) -> Dict:
        """Calculate benchmark performance metrics."""
        if benchmark_symbol not in price_history:
            return {"benchmark_return": 0.0, "alpha": 0.0, "beta": 1.0}

        benchmark_df = price_history[benchmark_symbol]

        # Normalize index tz-awareness to tz-naive for safe comparison
        idx = benchmark_df.index
        try:
            if hasattr(idx, "tz") and idx.tz is not None:
                idx = idx.tz_localize(None)
        except Exception:
            pass

        # Create a view with normalized index if needed
        if not idx.equals(benchmark_df.index):
            benchmark_df = benchmark_df.copy()
            benchmark_df.index = idx

        benchmark_prices = benchmark_df["close"]

        # Filter to backtest period using tz-naive date bounds
        start_bound = start_date
        end_bound = end_date
        # Convert tz-aware to naive if needed (should be naive already, but guard anyway)
        try:
            if hasattr(start_bound, "tzinfo") and start_bound.tzinfo is not None:
                start_bound = start_bound.replace(tzinfo=None)
            if hasattr(end_bound, "tzinfo") and end_bound.tzinfo is not None:
                end_bound = end_bound.replace(tzinfo=None)
        except Exception:
            pass

        mask = (benchmark_df.index >= start_bound) & (benchmark_df.index <= end_bound)
        benchmark_prices = benchmark_prices[mask]

        if len(benchmark_prices) < 2:
            return {"benchmark_return": 0.0, "alpha": 0.0, "beta": 1.0}

        benchmark_return = (
            benchmark_prices.iloc[-1] - benchmark_prices.iloc[0]
        ) / benchmark_prices.iloc[0]

        return {
            "benchmark_return": benchmark_return,
            "alpha": 0.0,  # Simplified - would need portfolio returns aligned with benchmark
            "beta": 1.0,  # Simplified - would need regression analysis
        }

    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """Calculate maximum drawdown from a series of portfolio values."""
        if not values:
            return 0.0

        peak = values[0]
        max_dd = 0.0

        for value in values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)

        return max_dd

    def _get_rebalance_frequency_days(self, frequency: str) -> int:
        """Convert rebalance frequency string to days."""
        frequency_map = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}
        return frequency_map.get(frequency.lower(), 30)

    def _empty_performance_metrics(self) -> Dict:
        """Return empty performance metrics for error cases."""
        return {
            "total_return": 0.0,
            "annualized_return": 0.0,
            "volatility": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "benchmark_return": 0.0,
            "alpha": 0.0,
            "beta": 1.0,
        }
