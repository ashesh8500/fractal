# %%
"""
Unified analysis runner:
- Automatically discovers available strategies in portfolio_lib.services.strategy package
  (classes inheriting BaseStrategy).
- Loads sensible default settings for backtests and per-strategy parameters.
- Runs backtests for each discovered strategy with minimal repeated code.
- Produces a comparison plot vs benchmark and prints key metrics.
- Provides standardized allocation charts for each strategy at each rebalance interval.
- Plots executed trades with FIFO PnL annotations.

Notes:
- Trade.quantity is interpreted by the backtester as a weight fraction (0..1) of the
  portfolio value at each rebalance. This script expects executed_trades emitted by the
  backtester and will plot them if available.

Usage:
    python -m portfolio_lib.analysis
"""

import importlib
import inspect
import pkgutil
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

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
    plot_allocations: bool = True  # whether to render allocation charts
    allocation_max_cols: int = 12  # cap symbols shown in allocation chart for readability


def default_settings() -> AnalysisDefaults:
    # Reasonable defaults for a diversified tech-heavy backtest
    symbols = [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
        "GOOG",
        "META",
        "AVGO",
        "ADBE",
        "AMD",
        "NFLX",
        "PEP",
        "TMUS",
        "INTC",
        "CMCSA",
        "CSCO",
        "TXN",
        "AMAT",
        "QCOM",
        "PYPL",
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
        # Optional per-strategy parameter overrides by class name or strategy display name
        strategy_overrides={
            # "BollingerAttractivenessStrategy": {"bb_period": 20, "bb_std": 2.0, "adjustment_factor": 0.2},
            # "Momentum": {"lookback_period": 90, "top_n": 5},
            # "ML Attractiveness (Momentum + Vol Change + Bollinger)": {"adjustment_factor": 0.25},
        },
        plot_allocations=True,
        allocation_max_cols=12,
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
            try:
                cond = issubclass(obj, BaseStrategy) and obj is not BaseStrategy
            except Exception:
                cond = False
            if cond and obj.__module__ == mod.__name__:
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


def fetch_aligned_price_history(
    data_service: YFinanceDataService, symbols: List[str], bt_cfg: BacktestConfig
) -> Dict[str, pd.DataFrame]:
    price_history = data_service.fetch_price_history(
        symbols,
        bt_cfg.start_date.strftime("%Y-%m-%d"),
        bt_cfg.end_date.strftime("%Y-%m-%d"),
    )
    if not price_history:
        raise RuntimeError("No price data returned. Check internet, symbols, or dates.")

    # Normalize indices to tz-naive to align with backtester assumptions
    for sym, df in list(price_history.items()):
        try:
            if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
                price_history[sym] = df.tz_localize(None)
        except Exception:
            pass
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
        if hasattr(df, "empty")
        and not df.empty
        and s in symbols
        and isinstance(df.index.min(), pd.Timestamp)
    ]
    if not first_dates:
        raise RuntimeError("Could not find any first dates for given symbols.")
    first_common = max(first_dates)

    start_prices: Dict[str, float] = {}
    for s in symbols:
        df = price_history.get(s)
        if (
            df is not None
            and isinstance(first_common, pd.Timestamp)
            and first_common in df.index
        ):
            start_prices[s] = float(df.loc[first_common, "close"])

    symbols_valid = [
        s
        for s in symbols
        if s in start_prices and start_prices[s] > 0 and np.isfinite(start_prices[s])
    ]
    if len(symbols_valid) < 3:
        raise RuntimeError(
            "Not enough valid symbols with start prices to build initial holdings."
        )

    capital_per = initial_capital / len(symbols_valid)
    initial_holdings = {s: capital_per / start_prices[s] for s in symbols_valid}
    return initial_holdings


def run_backtests_for_strategies(
    strategies: List[BaseStrategy],
    defaults: AnalysisDefaults,
    data_service: YFinanceDataService,
    backtester: BacktestingService,
) -> Tuple[Dict[str, Any], Dict[str, pd.DataFrame], BacktestConfig]:
    bt_cfg = build_backtest_config(defaults)

    # Fetch once: universe + benchmark
    symbols_full = list(dict.fromkeys(defaults.symbols + [bt_cfg.benchmark]))
    price_history = fetch_aligned_price_history(data_service, symbols_full, bt_cfg)

    # Build initial holdings using universe only (not benchmark)
    initial_holdings = compute_initial_holdings(
        price_history, defaults.symbols, bt_cfg.initial_capital
    )

    results: Dict[str, Any] = {}
    for strategy in strategies:
        s_name = getattr(strategy, "name", strategy.__class__.__name__)
        # Build per-strategy config merging defaults and overrides
        # Use overrides by class name first, then by display name for convenience
        override_params = (
            defaults.strategy_overrides.get(strategy.__class__.__name__)
            or defaults.strategy_overrides.get(s_name)
            or {}
        )
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
    print(
        "Period:",
        pd.to_datetime(res.start_date).date(),
        "to",
        pd.to_datetime(res.end_date).date(),
    )
    print(f"Total Return: {res.total_return:.2%}")
    print(f"Annualized Return: {res.annualized_return:.2%}")
    print(f"Volatility: {res.volatility:.2%}")
    print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {res.max_drawdown:.2%}")
    bench_name = getattr(getattr(res, "config", None), "benchmark", "Benchmark")
    print(f"Benchmark ({bench_name}): {res.benchmark_return:.2%}")
    if hasattr(res, "total_trades"):
        print(
            "Trades - total/wins/loses:",
            getattr(res, "total_trades", 0),
            getattr(res, "winning_trades", 0),
            getattr(res, "losing_trades", 0),
        )
    print()


def normalized_series(values: List[float], timestamps: List[pd.Timestamp]) -> pd.Series:
    s = pd.Series(values, index=pd.to_datetime(timestamps)).sort_index()
    if len(s) == 0 or not np.isfinite(s.iloc[0]) or s.iloc[0] == 0:
        raise RuntimeError("Invalid portfolio values for plotting.")
    return s / s.iloc[0]


def build_benchmark_series(
    price_history: Dict[str, pd.DataFrame], bt_cfg: BacktestConfig
) -> Optional[pd.Series]:
    if bt_cfg.benchmark not in price_history:
        return None
    bench_df = price_history[bt_cfg.benchmark]
    bench_prices = bench_df["close"]

    if (
        isinstance(bench_prices.index, pd.DatetimeIndex)
        and bench_prices.index.tz is not None
    ):
        bench_prices = bench_prices.tz_localize(None)

    start_bound = pd.Timestamp(bt_cfg.start_date).tz_localize(None)
    end_bound = pd.Timestamp(bt_cfg.end_date).tz_localize(None)
    mask = (bench_prices.index >= start_bound) & (bench_prices.index <= end_bound)
    bench_prices_filtered = bench_prices[mask]

    if (
        isinstance(bench_prices_filtered, pd.Series)
        and bench_prices_filtered.shape[0] > 1
    ):
        series = bench_prices_filtered / bench_prices_filtered.iloc[0]
        return series
    return None


def common_normalized_series(
    res: Any,
    common_start: Optional[pd.Timestamp],
    common_end: Optional[pd.Timestamp],
) -> pd.Series:
    """Normalize a strategy's equity curve to 1.0 at the common_start date."""
    s = pd.Series(
        res.portfolio_values, index=pd.to_datetime(res.timestamps)
    ).sort_index()
    if common_start is not None and common_end is not None:
        s = s[(s.index >= common_start) & (s.index <= common_end)]
    if s.empty:
        return pd.Series(dtype=float)
    # Normalize at the first value on/after common_start
    s = s / s.iloc[0]
    return s


def determine_common_period(
    results: Dict[str, Any],
) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    starts = []
    ends = []
    for res in results.values():
        ts = pd.to_datetime(res.timestamps)
        if len(ts) == 0:
            continue
        starts.append(ts.min())
        ends.append(ts.max())
    if not starts or not ends:
        return None, None
    # Use the latest first timestamp as the shared anchor (prevents early-start curves from getting padded)
    common_start = max(starts)
    common_end = min(ends)
    if common_start >= common_end:
        return None, None
    return common_start, common_end


def plot_results(
    results: Dict[str, Any], benchmark_series: Optional[pd.Series]
) -> None:
    # Determine a common period to normalize across all strategies
    common_start, common_end = determine_common_period(results)

    # Build normalized series set
    norm_curves: Dict[str, pd.Series] = {}
    union_index = None
    for name, res in results.items():
        s = common_normalized_series(res, common_start, common_end)
        if s.empty:
            continue
        union_index = (
            s.index if union_index is None else union_index.union(s.index).sort_values()
        )
        norm_curves[name] = s

    # Prepare benchmark aligned to common period
    bench_plot = None
    if benchmark_series is not None and (common_start is not None and common_end is not None):
        bench = benchmark_series[
            (benchmark_series.index >= common_start)
            & (benchmark_series.index <= common_end)
        ]
        if len(bench) > 1:
            bench = bench / bench.iloc[0]
            union_index = (
                union_index.union(bench.index).sort_values()
                if union_index is not None
                else bench.index
            )
            bench_plot = bench.reindex(union_index, method="pad")

    # Use Plotly for interactive visualization
    fig = go.Figure()
    if union_index is None and norm_curves:
        # fallback if only single curve
        union_index = next(iter(norm_curves.values())).index

    # Plot strategies
    for name, s in norm_curves.items():
        s_plot = s.reindex(union_index, method="pad")
        cum = (float(s_plot.iloc[-1]) - 1.0) if len(s_plot) else 0.0
        fig.add_trace(
            go.Scatter(
                x=s_plot.index,
                y=s_plot.values,
                mode="lines",
                name=f"{name} (Cum: {cum:.2%})",
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.3f}<extra>" + name + "</extra>",
            )
        )

    # Plot benchmark
    if bench_plot is not None and len(bench_plot) > 1:
        cum_b = float(bench_plot.iloc[-1]) - 1.0
        bench_name = bench_plot.name if bench_plot.name else "Benchmark"
        fig.add_trace(
            go.Scatter(
                x=bench_plot.index,
                y=bench_plot.values,
                mode="lines",
                name=f"{bench_name} (Cum: {cum_b:.2%})",
                line=dict(color="#ff7f0e", dash="dash"),
                hovertemplate="%{x|%Y-%m-%d}<br>%{y:.3f}<extra>"
                + bench_name
                + "</extra>",
            )
        )

    # Drawdown shading using first strategy
    if norm_curves and union_index is not None:
        first_name = next(iter(norm_curves.keys()))
        ref = norm_curves[first_name].reindex(union_index, method="pad")
        running_max = ref.cummax()
        dd = np.clip(running_max.values - ref.values, 0, None)
        fig.add_trace(
            go.Scatter(
                x=ref.index,
                y=running_max.values,
                mode="lines",
                line=dict(color="rgba(31,119,180,0)"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=ref.index,
                y=ref.values,
                mode="lines",
                line=dict(color="rgba(31,119,180,0)"),
                fill="tonexty",
                fillcolor="rgba(31,119,180,0.10)",
                name=f"Drawdown area ({first_name})",
                hoverinfo="skip",
            )
        )

    # Titles
    if results:
        any_res = next(iter(results.values()))
        period_str = f"{pd.to_datetime(any_res.start_date).date()} to {pd.to_datetime(any_res.end_date).date()}"
    else:
        period_str = ""

    fig.update_layout(
        title=f"Strategy Comparison vs Benchmark (Common-normalized) {period_str}",
        xaxis_title="Date",
        yaxis_title="Growth of $1",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.show()


# -----------------------------
# Allocation plotting
# -----------------------------


def extract_allocations(res: Any) -> Optional[pd.DataFrame]:
    """
    Attempt to extract allocation weights over time from StrategyResult/BacktestResult.
    Expected attributes:
        - res.weights_timestamps: list[datetime]
        - res.weights_series: list[dict[str, float]] or list[pd.Series]
    Returns a DataFrame indexed by timestamps, columns = symbols, values = weights (0..1).
    """
    # Try common possibilities
    timestamps = getattr(res, "weights_timestamps", None)
    series_list = getattr(res, "weights_series", None)

    if timestamps is None or series_list is None:
        # Fallback: if res has 'allocations' with list of dicts
        allocations = getattr(res, "allocations", None)
        if (
            allocations
            and isinstance(allocations, list)
            and all(isinstance(a, dict) for a in allocations)
        ):
            timestamps = [pd.to_datetime(a.get("timestamp")) for a in allocations]
            series_list = [a.get("weights") for a in allocations]

    if timestamps is None or series_list is None:
        return None

    ts = pd.to_datetime(timestamps)
    frames = []
    cols = set()
    for item in series_list:
        if isinstance(item, dict):
            s = pd.Series(item)
        elif isinstance(item, pd.Series):
            s = item
        else:
            continue
        cols.update(s.index)
        frames.append(s)
    if not frames:
        return None

    cols = sorted(list(cols))
    df = pd.DataFrame([s.reindex(cols).fillna(0.0) for s in frames], index=ts)
    # Normalize each row to sum to 1.0 just in case
    row_sums = df.sum(axis=1).replace(0, np.nan)
    df = df.div(row_sums, axis=0).fillna(0.0)
    return df


def plot_allocation_stack(
    df_alloc: pd.DataFrame, title: str, max_cols: int = 12
) -> None:
    if df_alloc is None or df_alloc.empty:
        print(f"[INFO] No allocation data to plot for {title}")
        return
    # Limit columns for readability
    cols = list(df_alloc.columns)
    if len(cols) > max_cols:
        # Take top N by average weight
        avg = df_alloc.mean().sort_values(ascending=False)
        top_cols = list(avg.iloc[:max_cols].index)
        other_cols = [c for c in cols if c not in top_cols]
        df_top = df_alloc[top_cols].copy()
        if other_cols:
            df_top["OTHER"] = df_alloc[other_cols].sum(axis=1)
        dfp = df_top
    else:
        dfp = df_alloc

    # Ensure monotonic index
    dfp = dfp.sort_index()

    # Plotly stacked area chart
    fig = go.Figure()
    cum = np.zeros(len(dfp))
    xvals = dfp.index
    for col in dfp.columns:
        y = dfp[col].values
        fig.add_trace(
            go.Scatter(
                x=xvals,
                y=cum + y,
                mode="lines",
                line=dict(width=0.5),
                name=col,
                hovertemplate="%{x|%Y-%m-%d}<br>"
                + col
                + ": %{text:.2%}<extra></extra>",
                text=y,
                stackgroup="one",
            )
        )
        cum = cum + y

    fig.update_layout(
        title=f"Allocation Over Time - {title}",
        xaxis_title="Date",
        yaxis_title="Portfolio Weight",
        yaxis=dict(range=[0, 1]),
        template="plotly_white",
        legend=dict(orientation="v"),
        hovermode="x unified",
    )
    fig.show()


def plot_trade_markers(
    res: Any,
    price_history: Dict[str, pd.DataFrame],
    title: str,
) -> None:
    """
    Plot trade markers (BUY/SELL) over the benchmark or primary price series.
    Uses `executed_trades` exposed by BacktestingService. If not present, falls back to empty plot.

    Enhancements:
      - Compute realized PnL per symbol using FIFO entry-exit pairing.
      - Annotate SELL markers with realized PnL and remaining position.
      - Annotate BUY markers with cumulative position after the trade.

    Assumptions:
      - res.executed_trades: List[Dict] with keys:
          symbol, action ('buy'/'sell'), quantity_shares, price, timestamp, reason (optional)
      - price_history: Dict[str, DataFrame] with a 'close' column per symbol
      - Use the strategy's top-weighted symbol price history if available, otherwise benchmark if present
    """
    trades = getattr(res, "executed_trades", None)
    if not trades:
        # Nothing to plot
        return

    # Build a mapping: symbol -> list of trades
    symbol_trades: Dict[str, List[Dict]] = defaultdict(list)
    for t in trades:
        if t.get("symbol") and t.get("action") in ("buy", "sell"):
            # Normalize timestamp to pandas Timestamp
            ts = t.get("timestamp")
            try:
                t["timestamp"] = pd.to_datetime(ts) if ts is not None else None
            except Exception:
                t["timestamp"] = None
            symbol_trades[t["symbol"]].append(t)

    # Sort trades by timestamp per symbol for consistent FIFO matching
    for sym in list(symbol_trades.keys()):
        symbol_trades[sym].sort(key=lambda x: (x.get("timestamp") or pd.Timestamp.min))

    # FIFO PnL calculator per symbol
    def compute_fifo_pnl_for_symbol(trds: List[Dict]) -> List[Dict]:
        """
        For a list of trades for one symbol, compute realized PnL on SELLs using FIFO.
        Adds keys on each trade dict:
          - position_after: cumulative position after applying this trade
          - avg_cost_after: average cost basis after this trade (for buys and remaining after sells)
          - realized_pnl: realized PnL realized on this trade if action is SELL else 0.0
          - realized_pnl_per_share: realized PnL per share for the matched quantity (SELL only)
        """
        position = 0.0
        # FIFO lots: list of (quantity_remaining, unit_cost)
        lots: List[Tuple[float, float]] = []
        avg_cost = 0.0
        out: List[Dict] = []

        for t in trds:
            action = t.get("action")
            qty = float(t.get("quantity_shares") or t.get("quantity") or 0.0)
            price = float(t.get("price") or 0.0)
            realized_pnl = 0.0
            realized_pnl_per_share = 0.0

            if action == "buy" and qty > 0:
                # Add as a new lot
                lots.append((qty, price))
                position += qty
                # Update average cost
                total_shares = sum(q for q, _ in lots)
                total_cost = sum(q * c for q, c in lots)
                avg_cost = (total_cost / total_shares) if total_shares > 0 else 0.0

            elif action == "sell" and qty > 0:
                sell_qty = qty
                # Match against FIFO lots
                pnl_accum = 0.0
                matched_shares = 0.0
                new_lots: List[Tuple[float, float]] = []
                for lot_qty, lot_cost in lots:
                    if sell_qty <= 0:
                        new_lots.append((lot_qty, lot_cost))
                        continue
                    take = min(lot_qty, sell_qty)
                    pnl_accum += (price - lot_cost) * take
                    matched_shares += take
                    remaining = lot_qty - take
                    if remaining > 0:
                        new_lots.append((remaining, lot_cost))
                    sell_qty -= take
                lots = new_lots
                position -= qty
                realized_pnl = pnl_accum
                realized_pnl_per_share = (
                    (pnl_accum / matched_shares) if matched_shares > 0 else 0.0
                )
                # Update average cost after selling (based on remaining lots)
                total_shares = sum(q for q, _ in lots)
                total_cost = sum(q * c for q, c in lots)
                avg_cost = (total_cost / total_shares) if total_shares > 0 else 0.0

            # Persist annotations
            t_ann = dict(t)
            t_ann["position_after"] = position
            t_ann["avg_cost_after"] = avg_cost
            t_ann["realized_pnl"] = realized_pnl
            t_ann["realized_pnl_per_share"] = realized_pnl_per_share
            out.append(t_ann)

        return out

    # Compute FIFO PnL per symbol
    for sym in list(symbol_trades.keys()):
        symbol_trades[sym] = compute_fifo_pnl_for_symbol(symbol_trades[sym])

    # Choose a primary symbol for plotting background price:
    # Prefer the benchmark if present, else the most-traded symbol
    primary_symbol = None
    benchmark = getattr(getattr(res, "config", None), "benchmark", None)
    if benchmark and benchmark in price_history:
        primary_symbol = benchmark
    else:
        # pick the symbol with most trades that also exists in price history
        candidates = sorted(
            [
                (sym, len(trds))
                for sym, trds in symbol_trades.items()
                if sym in price_history
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        if candidates:
            primary_symbol = candidates[0][0]

    if primary_symbol is None:
        # No suitable price series found
        return

    dfp = price_history[primary_symbol].copy()
    if dfp.empty or "close" not in dfp.columns:
        return
    if isinstance(dfp.index, pd.DatetimeIndex) and dfp.index.tz is not None:
        dfp = dfp.tz_localize(None)

    # Figure with background price line
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dfp.index,
            y=dfp["close"].values,
            mode="lines",
            name=f"{primary_symbol} Close",
            line=dict(color="#444"),
            hovertemplate="%{x|%Y-%m-%d}<br>Close: %{y:.2f}<extra></extra>",
        )
    )

    # Overlay trade markers for each symbol
    colors = {"buy": "green", "sell": "red"}
    for sym, trds in symbol_trades.items():
        if not trds:
            continue
        # Align a price series for this symbol if we have it; otherwise use primary symbol close for y
        sym_df = price_history.get(sym)
        if sym_df is not None and not sym_df.empty and "close" in sym_df.columns:
            if (
                isinstance(sym_df.index, pd.DatetimeIndex)
                and sym_df.index.tz is not None
            ):
                sym_df = sym_df.tz_localize(None)
            price_series = sym_df["close"]
        else:
            price_series = dfp["close"]

        # Split into buys and sells
        buys_x, buys_y, buys_text = [], [], []
        sells_x, sells_y, sells_text = [], [], []

        for t in trds:
            ts = t.get("timestamp")
            if ts is None:
                continue
            # Y from explicit trade price if available else from price series
            y = t.get("price")
            if y is None:
                # pick nearest available close
                if ts in price_series.index:
                    y = float(price_series.loc[ts])
                else:
                    # fallback to nearest index
                    try:
                        idx = price_series.index.get_indexer([ts], method="nearest")[0]
                        if idx >= 0:
                            y = float(price_series.iloc[idx])
                    except Exception:
                        y = None
            # Build hover text with PnL annotations
            reason = t.get("reason") or ""
            qty = float(t.get("quantity_shares") or t.get("quantity") or 0.0)
            gross = float(t.get("gross_value") or 0.0)
            commission = float(t.get("commission") or 0.0)
            slippage = float(t.get("slippage") or 0.0)
            total_cost = float(t.get("total_cost") or 0.0)
            pos_after = float(t.get("position_after") or 0.0)
            avg_cost_after = float(t.get("avg_cost_after") or 0.0)
            realized_pnl = float(t.get("realized_pnl") or 0.0)
            realized_pnl_ps = float(t.get("realized_pnl_per_share") or 0.0)
            base = (
                f"{sym} {t.get('action','').upper()}<br>"
                f"Time: {pd.to_datetime(ts).strftime('%Y-%m-%d %H:%M:%S')}<br>"
                f"Qty(sh): {qty:.4f}  Price: {float(y) if y is not None else float('nan'):.2f}<br>"
                f"Gross: {gross:.2f}  Comm: {commission:.2f}  Slip: {slippage:.2f}  TxnCost: {total_cost:.2f}<br>"
            )
            if t.get("action") == "buy":
                hover = (
                    base
                    + f"Position After: {pos_after:.4f}  Avg Cost: {avg_cost_after:.2f}<br>{reason}"
                )
                buys_x.append(ts)
                buys_y.append(y)
                buys_text.append(hover)
            elif t.get("action") == "sell":
                hover = (
                    base
                    + f"Realized PnL: {realized_pnl:.2f} ({realized_pnl_ps:.2f}/sh)<br>Position After: {pos_after:.4f}  Avg Cost: {avg_cost_after:.2f}<br>{reason}"
                )
                sells_x.append(ts)
                sells_y.append(y)
                sells_text.append(hover)

        if buys_x:
            fig.add_trace(
                go.Scatter(
                    x=buys_x,
                    y=buys_y,
                    mode="markers",
                    name=f"{sym} BUY",
                    marker=dict(
                        color=colors["buy"],
                        symbol="triangle-up",
                        size=10,
                        line=dict(width=1, color="#222"),
                    ),
                    hovertemplate="%{text}<extra></extra>",
                    text=buys_text,
                )
            )
        if sells_x:
            fig.add_trace(
                go.Scatter(
                    x=sells_x,
                    y=sells_y,
                    mode="markers",
                    name=f"{sym} SELL",
                    marker=dict(
                        color=colors["sell"],
                        symbol="triangle-down",
                        size=10,
                        line=dict(width=1, color="#222"),
                    ),
                    hovertemplate="%{text}<extra></extra>",
                    text=sells_text,
                )
            )

    # Title and layout
    period_str = (
        f"{pd.to_datetime(res.start_date).date()} to {pd.to_datetime(res.end_date).date()}"
        if hasattr(res, "start_date")
        else ""
    )
    fig.update_layout(
        title=f"Trade Markers over Price - {title} {period_str}",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white",
        hovermode="x",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.show()


def main():
    # Defaults
    defaults = default_settings()

    # Services
    data_service = YFinanceDataService()
    backtester = BacktestingService(data_service)

    # Discover and run strategies
    strategies = discover_strategies()
    if not strategies:
        raise RuntimeError(
            "No strategies discovered. Ensure they subclass BaseStrategy and are importable."
        )
    print(
        f"Discovered strategies: {[getattr(s, 'name', s.__class__.__name__) for s in strategies]}"
    )

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

    # Plot equity curves with common normalization period
    plot_results(results, bench_series)

    # Allocation charts per strategy
    if defaults.plot_allocations:
        for name, res in results.items():
            alloc_df = extract_allocations(res)
            plot_allocation_stack(
                alloc_df, title=name, max_cols=defaults.allocation_max_cols
            )

    # Trade markers per strategy (if executed_trades available)
    for name, res in results.items():
        plot_trade_markers(res, price_history, title=name)

    # Ending normalized values quick glance
    print("Ending normalized values:")
    for name, res in results.items():
        s = normalized_series(res.portfolio_values, res.timestamps)
        print(f"{name}: {round(float(s.iloc[-1]), 4)}")
    if bench_series is not None and len(bench_series) > 1:
        print(
            f"Benchmark ({bt_cfg.benchmark}): {round(float(bench_series.iloc[-1]), 4)}"
        )
    else:
        print("Benchmark: n/a")


if __name__ == "__main__":
    main()
# %%
