"""
Backtesting Service Implementation.

This module provides comprehensive backtesting functionality for trading strategies,
including performance metrics, risk analysis, and comparison to benchmarks.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

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

    @staticmethod
    def _to_float(val: object) -> float:
        """Best-effort conversion to float, returns nan on failure."""
        try:
            if isinstance(val, (int, float, np.floating)):
                return float(val)
            # pandas scalar
            return float(np.asarray(val).astype(np.float64))
        except Exception:
            return float("nan")

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
                tz_loc = getattr(df, "tz_localize", None)
                df2 = tz_loc(None) if callable(tz_loc) else df
                price_history[symbol] = df2  # type: ignore[assignment]
            except Exception:
                # If not tz-aware or operation unsupported, keep original; downstream code has guards
                price_history[symbol] = df

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
        cash = 0.0  # will be computed after dates are aligned
        portfolio_values: List[float] = []
        daily_returns: List[float] = []
        timestamps: List = []
        holdings_history: List[Dict[str, float]] = []
        rebalance_details: List[Dict] = []
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
            tz_loc = getattr(idx, "tz_localize", None)
            try:
                idx2 = tz_loc(None) if callable(tz_loc) else idx
            except Exception:
                idx2 = idx
            try:
                idx_p = pd.Index(idx2)  # type: ignore[call-arg]
                for d in idx_p.tolist():
                    all_dates.add(d)
            except Exception:
                # best effort fallback
                try:
                    for d in list(idx2):  # type: ignore[arg-type]
                        all_dates.add(d)
                except Exception:
                    pass

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

        # Compute initial cash by valuing initial_holdings at the first simulation date
        # so that total initial portfolio value matches initial_capital best-effort
        first_date = simulation_dates[0]
        initial_value = 0.0
        for symbol, shares in current_holdings.items():
            df = price_history.get(symbol)
            if df is not None and not df.empty and first_date in df.index:
                try:
                    px = self._to_float(df.loc[first_date, "close"])  # type: ignore[index]
                    if np.isfinite(px):
                        initial_value += float(shares) * float(px)
                except Exception:
                    pass
        cash = max(float(backtest_config.initial_capital) - float(initial_value), 0.0)

        prev_portfolio_value = float(backtest_config.initial_capital)

        # Rebalancing frequency settings
        rebalance_days = self._get_rebalance_frequency_days(
            strategy_config.rebalance_frequency
        )
        last_rebalance_date = None

        for i, current_date in enumerate(simulation_dates):
            # Get current prices for this date
            current_prices: Dict[str, float] = {}
            for symbol, df in price_history.items():
                if current_date in df.index:
                    val = df.loc[current_date, "close"]
                    price_val = self._to_float(val)
                    if np.isfinite(price_val):
                        current_prices[symbol] = price_val

            # Calculate current portfolio value
            # Compute invested value separately to avoid cash diluting asset weights
            invested_total = 0.0
            position_values: Dict[str, float] = {}
            for symbol, shares in current_holdings.items():
                if symbol in current_prices:
                    pv = float(shares) * float(current_prices[symbol])
                    position_values[symbol] = pv
                    invested_total += pv
            portfolio_value = cash + invested_total

            current_weights: Dict[str, float] = {}
            for symbol in current_holdings.keys():
                if invested_total > 0 and symbol in position_values:
                    current_weights[symbol] = position_values[symbol] / invested_total
                else:
                    current_weights[symbol] = 0.0

            # Store portfolio value and calculate daily return
            portfolio_values.append(portfolio_value)
            timestamps.append(current_date)
            holdings_history.append(dict(current_holdings))

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

            if should_rebalance and i < len(simulation_dates) - 1:  # Don't rebalance on last day
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
                        portfolio_value,
                        current_date,
                        getattr(strategy_result, "scores", None),
                    )

                    current_holdings = trade_stats["new_holdings"]
                    cash = trade_stats["new_cash"]
                    total_trades += trade_stats["num_trades"]
                    winning_trades += trade_stats["winning_trades"]
                    losing_trades += trade_stats["losing_trades"]

                    # Accumulate executed trade metadata
                    for t in trade_stats.get("executed", []):
                        executed_trades.append(t)

                    # Record rebalance diagnostics with JSON-friendly values
                    try:
                        def _iso(ts_obj):
                            try:
                                return pd.to_datetime(ts_obj).to_pydatetime().isoformat()
                            except Exception:
                                try:
                                    return str(ts_obj)
                                except Exception:
                                    return None

                        def _float_map(m):
                            out = {}
                            for k, v in (m or {}).items():
                                try:
                                    out[str(k)] = float(v)
                                except Exception:
                                    try:
                                        out[str(k)] = self._to_float(v)
                                    except Exception:
                                        pass
                            return out

                        def _serialize_trade(t):
                            try:
                                sym = getattr(t, "symbol", None)
                                act = getattr(t, "action", None)
                                qty = getattr(t, "quantity", None)
                                price = getattr(t, "price", None)
                                ts = getattr(t, "timestamp", None) or current_date
                                reason = getattr(t, "reason", None)
                                if act is None:
                                    act_str = None
                                else:
                                    act_val = getattr(act, "value", None)
                                    if isinstance(act_val, str):
                                        act_str = act_val
                                    elif hasattr(act, "value"):
                                        act_str = str(getattr(act, "value"))
                                    else:
                                        act_str = str(act)
                                return {
                                    "symbol": None if sym is None else str(sym),
                                    "action": act_str,
                                    "quantity": None if qty is None else float(qty),
                                    "price": None if price is None else float(price),
                                    "timestamp": _iso(ts),
                                    "reason": None if reason is None else str(reason),
                                }
                            except Exception:
                                return {"trade": str(t)}

                        rebalance_details.append(
                            {
                                "timestamp": _iso(current_date),
                                "weights": _float_map(current_weights),
                                "target_weights": _float_map(getattr(strategy_result, "new_weights", {})),
                                "scores": _float_map(getattr(strategy_result, "scores", {})),
                                "trades": [_serialize_trade(t) for t in getattr(strategy_result, "trades", [])],
                            }
                        )
                    except Exception:
                        pass

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
            "holdings_history": holdings_history,
            "rebalance_details": rebalance_details,
        }

    def _execute_trades(
        self,
        trades: List[Trade],
        current_holdings: Dict[str, float],
        cash: float,
        current_prices: Dict[str, float],
        config: BacktestConfig,
        portfolio_value: float,
        trade_date,
        symbol_scores: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """
        Execute trades and update portfolio state.

        IMPORTANT: Trade.quantity is interpreted as a WEIGHT FRACTION (0..1) of the
        current portfolio value to allocate/deallocate for the given symbol at this rebalance.
        """
        new_holdings = current_holdings.copy()
        new_cash = cash
        num_trades = 0
        winning_trades = 0
        losing_trades = 0
        executed: List[Dict] = []

        for trade in trades:
            symbol = trade.symbol
            if symbol not in current_prices:
                continue

            price = float(current_prices[symbol])
            if price <= 0.0:
                continue

            # Convert weight fraction -> dollar value to trade at this rebalance
            # Clamp quantity to [0,1] just in case
            weight_fraction = max(0.0, min(1.0, float(trade.quantity)))
            dollar_value = weight_fraction * portfolio_value
            if dollar_value <= 0.0:
                continue

            shares = dollar_value / price
            trade_value = shares * price  # == dollar_value
            commission = trade_value * config.commission
            slippage = trade_value * config.slippage
            total_cost = commission + slippage

            if trade.action == TradeAction.BUY:
                total_needed = trade_value + total_cost
                if new_cash >= total_needed and shares > 0.0:
                    new_holdings[symbol] = new_holdings.get(symbol, 0.0) + shares
                    new_cash -= total_needed
                    num_trades += 1
                    executed.append(
                        {
                            "symbol": symbol,
                            "action": "buy",
                            "quantity_shares": float(shares),
                            "weight_fraction": float(weight_fraction),
                            "price": float(price),
                            "gross_value": float(trade_value),
                            "commission": float(commission),
                            "slippage": float(slippage),
                            "total_cost": float(total_cost),
                            "net_cash_delta": float(-total_needed),
                            "timestamp": getattr(trade, "timestamp", None) or trade_date,
                            "reason": getattr(trade, "reason", None),
                            "score": None
                            if symbol_scores is None
                            else float(symbol_scores.get(symbol, np.nan)),
                        }
                    )

            elif trade.action == TradeAction.SELL:
                current_shares = float(new_holdings.get(symbol, 0.0))
                shares_to_sell = min(current_shares, shares)
                if shares_to_sell > 0.0:
                    gross_value = shares_to_sell * price
                    commission = gross_value * config.commission
                    slippage = gross_value * config.slippage
                    total_cost = commission + slippage
                    proceeds = gross_value - total_cost

                    new_holdings[symbol] = current_shares - shares_to_sell
                    new_cash += proceeds
                    num_trades += 1
                    executed.append(
                        {
                            "symbol": symbol,
                            "action": "sell",
                            "quantity_shares": float(shares_to_sell),
                            "weight_fraction": float(weight_fraction),
                            "price": float(price),
                            "gross_value": float(gross_value),
                            "commission": float(commission),
                            "slippage": float(slippage),
                            "total_cost": float(total_cost),
                            "net_cash_delta": float(proceeds),
                            "timestamp": getattr(trade, "timestamp", None) or trade_date,
                            "reason": getattr(trade, "reason", None),
                            "score": None
                            if symbol_scores is None
                            else float(symbol_scores.get(symbol, np.nan)),
                        }
                    )

                    # Simple heuristic for winning/losing trades
                    if proceeds > gross_value * 0.95:  # Rough breakeven after costs
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
        try:
            benchmark_df = benchmark_df.tz_localize(None)
        except Exception:
            # If not tz-aware or operation unsupported, leave as-is
            pass

        benchmark_prices = benchmark_df["close"]

        # Filter to backtest period using tz-naive date bounds
        start_bound = start_date
        end_bound = end_date
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
