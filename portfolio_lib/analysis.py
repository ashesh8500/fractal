# %%
"""
Unified analysis runner:
- Automatically discovers available strategies in portfolio_lib.services.strategy package
  (classes inheriting BaseStrategy).
- Loads sensible default settings for backtests and per-strategy parameters.
- Runs backtests for each discovered strategy with minimal repeated code.
- Produces a comparison plot vs benchmark and prints key metrics.

Usage:
    python -m portfolio_lib.analysis
"""

import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Type

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.strategy import BaseStrategy


# -----------------------------
# Configuration and defaults
# -----------------------------

@dataclass
class AnalysisDefaults:
    # Universe
    symbols: List[str]
    benchmark: str
    years: int
    initial_capital: float
    commission: float
    slippage: float
    rebalance_frequency: str
    risk_tolerance: float
    max_position_size: float
    strategy_overrides: Dict[str, Dict[str, Any]]


def default_settings() -> AnalysisDefaults:
    # Reasonable defaults for Nasdaq-heavy backtest
    symbols = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "AVGO",
        "ADBE", "AMD", "NFLX", "PEP", "TMUS", "INTC", "CMCSA", "CSCO",
        "TXN", "AMAT", "QCOM", "PYPL",
    ]
    return AnalysisDefaults(
        symbols=symbols,
        benchmark="QQQ",
        years=3,
        initial_capital=100000.0,
        commission=0.0005,
        slippage=0.0002,
        rebalance_frequency="monthly",
        risk_tolerance=0.5,
        max_position_size=1.0,
        # Optional per-strategy parameter overrides by class name or strategy name
        strategy_overrides={
            # Examples:
            # "BollingerAttractivenessStrategy": {"bb_period": 20, "bb_std": 2.0, "adjustment_factor": 0.2},
            # "MomentumStrategy": {"lookback_period": 90, "top_n": 5},
        },
    )


# -----------------------------
# Strategy discovery
# -----------------------------

def discover_strategies() -> List[BaseStrategy]:
    """
    Import all modules in portfolio_lib.services.strategy and instantiate classes
    that inherit from BaseStrategy (excluding the base itself).
    """
    strategies: List[BaseStrategy] = []
    pkg_name = "portfolio_lib.services.strategy"
    pkg = importlib.import_module(pkg_name)

    for _, mod_name, is_pkg in pkgutil.iter_modules(pkg.__path__, pkg_name + "."):
        if is_pkg:
            continue
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            # Must inherit BaseStrategy and be defined in this module
            if issubclass(obj, BaseStrategy) and obj is not BaseStrategy and obj.__module__ == mod.__name__:
                try:
                    instance = obj()
                    strategies.append(instance)
                except Exception:
                    # Skip strategies that fail to instantiate
                    continue
    # Deduplicate by strategy name to avoid collisions
    seen = set()
    unique: List[BaseStrategy] = []
    for s in strategies:
        name = getattr(s, "name", s.__class__.__name__)
        if name not in seen:
            unique.append(s)
            seen.add(name)
    return unique


# -----------------------------
# Utilities
# -----------------------------

def build_backtest_config(defaults: AnalysisDefaults) -> BacktestConfig:
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=365 * defaults.years)
    return BacktestConfig(
        start_date=pd.Timestamp(start).to_pydatetime(),
        end_date=end.to_pydatetime(),
        initial_capital=defaults.initial_capital,
        commission=defaults.commission,
        slippage=defaults.slippage,
        benchmark=defaults.benchmark,
    )


def fetch_aligned_price_history(data_service: YFinanceDataService, symbols: List[str], bt_cfg: BacktestConfig) -> Dict[str, pd.DataFrame]:
    price_history = data_service.fetch_price_history(
        symbols,
        bt_cfg.start_date.strftime("%Y-%m-%d"),
        bt_cfg.end_date.strftime("%Y-%m-%d"),
    )
    if not price_history:
        raise RuntimeError("No price data returned. Check internet, symbols, or dates.")
    return price_history


def compute_initial_holdings(
    price_history: Dict[str, pd.DataFrame],
    symbols: List[str],
    initial_capital: float,
) -> Dict[str, float]:
    # Find first common date across all symbols that have data
    first_dates = [
        df.index.min()
        for s, df in price_history.items()
        if hasattr(df, "empty") and not df.empty and s in symbols and isinstance(df.index.min(), pd.Timestamp)
    ]
    if not first_dates:
        raise RuntimeError("Could not find any first dates for given symbols.")
    first_common = max(first_dates)

    start_prices: Dict[str, float] = {}
    for s in symbols:
        df = price_history.get(s)
        if df is not None and isinstance(first_common, pd.Timestamp) and first_common in df.index:
            start_prices[s] = float(df.loc[first_common, "close"])

    symbols_valid = [s for s in symbols if s in start_prices and start_prices[s] > 0 and np.isfinite(start_prices[s])]
    if len(symbols_valid) < 3:
        raise RuntimeError("Not enough valid symbols with start prices to build initial holdings.")

    capital_per = initial_capital / len(symbols_valid)
    initial_holdings = {s: capital_per / start_prices[s] for s in symbols_valid}
    return initial_holdings


def run_backtests_for_strategies(
    strategies: List[BaseStrategy],
    defaults: AnalysisDefaults,
    data_service: YFinanceDataService,
    backtester: BacktestingService,
) -> Dict[str, Any]:
    bt_cfg = build_backtest_config(defaults)

    # Fetch once: universe + benchmark
    symbols_full = list(dict.fromkeys(defaults.symbols + [bt_cfg.benchmark]))
    price_history = fetch_aligned_price_history(data_service, symbols_full, bt_cfg)

    # Build initial holdings using universe only (not benchmark)
    initial_holdings = compute_initial_holdings(price_history, defaults.symbols, bt_cfg.initial_capital)

    results: Dict[str, Any] = {}
    for strategy in strategies:
        s_name = getattr(strategy, "name", strategy.__class__.__name__)
        # Build per-strategy config merging defaults and overrides
        override_params = defaults.strategy_overrides.get(strategy.__class__.__name__, {})
        # StrategyConfig.parameters is a free-form dict
        strat_cfg = StrategyConfig(
            name=s_name,
            parameters=override_params,
            rebalance_frequency=defaults.rebalance_frequency,
            risk_tolerance=defaults.risk_tolerance,
            max_position_size=defaults.max_position_size,
        )
        try:
            res = backtester.run_backtest(
                strategy=strategy,
                strategy_config=strat_cfg,
                backtest_config=bt_cfg,
                initial_holdings=initial_holdings,
            )
            results[s_name] = res
        except Exception as e:
            print(f"[WARN] Strategy '{s_name}' failed to run: {e}")
    return results, price_history, bt_cfg


def print_metrics(title: str, res: Any) -> None:
    print(f"=== {title} ===")
    print("Strategy:", res.strategy_name)
    print("Period:", pd.to_datetime(res.start_date).date(), "to", pd.to_datetime(res.end_date).date())
    print(f"Total Return: {res.total_return:.2%}")
    print(f"Annualized Return: {res.annualized_return:.2%}")
    print(f"Volatility: {res.volatility:.2%}")
    print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {res.max_drawdown:.2%}")
    print(f"Benchmark ({getattr(res, 'benchmark', 'N/A')}): {res.benchmark_return:.2%}")
    if hasattr(res, "total_trades"):
        print(
            "Trades - total/wins/loses:",
            res.total_trades,
            getattr(res, "winning_trades", 0),
            getattr(res, "losing_trades", 0),
        )
    print()


def normalized_series(values: List[float], timestamps: List[pd.Timestamp]) -> pd.Series:
    s = pd.Series(values, index=pd.to_datetime(timestamps)).sort_index()
    if len(s) == 0 or not np.isfinite(s.iloc[0]) or s.iloc[0] == 0:
        raise RuntimeError("Invalid portfolio values for plotting.")
    return s / s.iloc[0]


def build_benchmark_series(price_history: Dict[str, pd.DataFrame], bt_cfg: BacktestConfig) -> Optional[pd.Series]:
    if bt_cfg.benchmark not in price_history:
        return None
    bench_df = price_history[bt_cfg.benchmark]
    bench_prices = bench_df["close"]

    if isinstance(bench_prices.index, pd.DatetimeIndex) and bench_prices.index.tz is not None:
        bench_prices = bench_prices.tz_localize(None)

    start_bound = pd.Timestamp(bt_cfg.start_date).tz_localize(None)
    end_bound = pd.Timestamp(bt_cfg.end_date).tz_localize(None)
    mask = (bench_prices.index >= start_bound) & (bench_prices.index <= end_bound)
    bench_prices_filtered = bench_prices[mask]

    if isinstance(bench_prices_filtered, pd.Series) and bench_prices_filtered.shape[0] > 1:
        series = bench_prices_filtered / bench_prices_filtered.iloc[0]
        return series
    return None


def plot_results(results: Dict[str, Any], benchmark_series: Optional[pd.Series]) -> None:
    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot each strategy
    union_index = None
    for name, res in results.items():
        s = normalized_series(res.portfolio_values, res.timestamps)
        if union_index is None:
            union_index = s.index
        else:
            union_index = union_index.union(s.index).sort_values()
        s_plot = s.reindex(union_index, method="pad")
        ax.plot(s_plot.index, s_plot.values, label=f"{name} (Cum: {(s_plot.iloc[-1]-1):.2%})", linewidth=2)

    # Plot benchmark aligned to union index
    if benchmark_series is not None and len(benchmark_series) > 1:
        bench_plot = benchmark_series.reindex(union_index, method="pad")
        ax.plot(
            bench_plot.index,
            bench_plot.values,
            label=f"{'Benchmark'} ({bench_plot.name if bench_plot.name else ''}) (Cum: {(bench_plot.iloc[-1]-1):.2%})",
            linewidth=2,
            color="#ff7f0e",
        )

    # Drawdown shading using the first strategy as reference, if available
    if results:
        first_name = next(iter(results.keys()))
        first_series = normalized_series(results[first_name].portfolio_values, results[first_name].timestamps)
        first_series = first_series.reindex(union_index, method="pad")
        running_max = first_series.cummax()
        ax.fill_between(
            first_series.index,
            first_series.values,
            running_max.values,
            where=(first_series.values < running_max.values),
            color="#1f77b4",
            alpha=0.10,
            interpolate=True,
            label="_ddshade",
        )

    # Title and labels
    if results:
        any_res = next(iter(results.values()))
        period_str = f"{pd.to_datetime(any_res.start_date).date()} to {pd.to_datetime(any_res.end_date).date()}"
    else:
        period_str = ""
    ax.set_title(f"Strategy Comparison vs Benchmark (Normalized to 1.0) {period_str}")
    ax.set_ylabel("Growth of $1")
    ax.set_xlabel("Date")
    ax.legend(loc="best", frameon=True)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
    plt.tight_layout()
    plt.show()


def main():
    # Defaults
    defaults = default_settings()

    # Services
    data_service = YFinanceDataService()
    backtester = BacktestingService(data_service)

    # Discover and run strategies
    strategies = discover_strategies()
    if not strategies:
        raise RuntimeError("No strategies discovered. Ensure they subclass BaseStrategy and are importable.")
    print(f"Discovered strategies: {[getattr(s, 'name', s.__class__.__name__) for s in strategies]}")

    results, price_history, bt_cfg = run_backtests_for_strategies(
        strategies=strategies,
        defaults=defaults,
        data_service=data_service,
        backtester=backtester,
    )

    # Print metrics
    for name, res in results.items():
        print_metrics(name, res)

    # Benchmark series for plotting
    bench_series = build_benchmark_series(price_history, bt_cfg)
    if bench_series is not None:
        # Name for legend context
        bench_series.name = bt_cfg.benchmark

    # Plot
    plot_results(results, bench_series)

    # Ending normalized values quick glance
    print("Ending normalized values:")
    for name, res in results.items():
        s = normalized_series(res.portfolio_values, res.timestamps)
        print(f"{name}: {round(float(s.iloc[-1]), 4)}")
    if bench_series is not None and len(bench_series) > 1:
        print(f"Benchmark ({bt_cfg.benchmark}): {round(float(bench_series.iloc[-1]), 4)}")
    else:
        print("Benchmark: n/a")


if __name__ == "__main__":
    main()
# %%
