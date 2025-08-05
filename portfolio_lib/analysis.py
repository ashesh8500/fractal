# %%
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.strategy.bollinger import BollingerAttractivenessStrategy
from portfolio_lib.services.strategy.momentum import MomentumStrategy

# 1) Universe: pick a Nasdaq-heavy basket (example subset of Nasdaq-100)
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

# 2) Data + backtester
data_service = YFinanceDataService()
backtester = BacktestingService(data_service)

# 3) Backtest window and config
end = pd.Timestamp.today().normalize()
start = end - pd.Timedelta(days=365 * 3)  # 3 years

bt_cfg = BacktestConfig(
    start_date=pd.Timestamp(start).to_pydatetime(),
    end_date=end.to_pydatetime(),
    initial_capital=100000.0,
    commission=0.0005,  # 5 bps
    slippage=0.0002,  # 2 bps
    benchmark="QQQ",  # Nasdaq-100 ETF
)

# 4) Fetch price history once (used to build initial holdings)
price_history = data_service.fetch_price_history(
    symbols + [bt_cfg.benchmark],
    bt_cfg.start_date.strftime("%Y-%m-%d"),
    bt_cfg.end_date.strftime("%Y-%m-%d"),
)
if not price_history:
    raise RuntimeError("No price data returned. Check internet, symbols, or dates.")

# Align first common date to price
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

start_prices = {}
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
        "Not enough valid symbols with start prices to run a momentum portfolio."
    )

# 5) Build initial equal-weight holdings (by shares)
capital_per = bt_cfg.initial_capital / len(symbols_valid)
initial_holdings = {s: capital_per / start_prices[s] for s in symbols_valid}

# 6) Configure strategies
bollinger_strategy = BollingerAttractivenessStrategy()
bollinger_cfg = StrategyConfig(
    name="Bollinger",
    parameters={"lookback_period": 90, "top_n": 5},
    rebalance_frequency="monthly",
    risk_tolerance=0.5,
    max_position_size=1.0,
)

momentum_strategy = MomentumStrategy()
# Keep momentum simple and minimal; share same rebalance cadence
momentum_cfg = StrategyConfig(
    name="Momentum",
    parameters={"lookback_period": 90, "top_n": 5},
    rebalance_frequency="monthly",
    risk_tolerance=0.5,
    max_position_size=1.0,
)

# 7) Run backtests
bollinger_result = backtester.run_backtest(
    strategy=bollinger_strategy,
    strategy_config=bollinger_cfg,
    backtest_config=bt_cfg,
    initial_holdings=initial_holdings,
)
momentum_result = backtester.run_backtest(
    strategy=momentum_strategy,
    strategy_config=momentum_cfg,
    backtest_config=bt_cfg,
    initial_holdings=initial_holdings,
)


# 8) Metrics summary
def print_metrics(title, res):
    print(f"=== {title} ===")
    print("Strategy:", res.strategy_name)
    print("Period:", res.start_date.date(), "to", res.end_date.date())
    print(f"Total Return: {res.total_return:.2%}")
    print(f"Annualized Return: {res.annualized_return:.2%}")
    print(f"Volatility: {res.volatility:.2%}")
    print(f"Sharpe Ratio: {res.sharpe_ratio:.2f}")
    print(f"Max Drawdown: {res.max_drawdown:.2%}")
    print(f"Benchmark (QQQ) Return: {res.benchmark_return:.2%}")
    if hasattr(res, "total_trades"):
        print(
            "Trades - total/wins/loses:",
            res.total_trades,
            getattr(res, "winning_trades", 0),
            getattr(res, "losing_trades", 0),
        )
    print()


print_metrics("Bollinger", bollinger_result)
print_metrics("Momentum", momentum_result)


# 9) Build normalized equity series
def norm_equity(values, timestamps):
    s = pd.Series(values, index=pd.to_datetime(timestamps)).sort_index()
    if len(s) == 0 or not np.isfinite(s.iloc[0]) or s.iloc[0] == 0:
        raise RuntimeError("Invalid portfolio values for plotting.")
    return s / s.iloc[0], s


bollinger_norm, bollinger_pv = norm_equity(
    bollinger_result.portfolio_values, bollinger_result.timestamps
)
momentum_norm, momentum_pv = norm_equity(
    momentum_result.portfolio_values, momentum_result.timestamps
)

# Benchmark via price history fallback (minimal dependency on BacktestResult internals)
bench_series = None
if bt_cfg.benchmark in price_history:
    bench_df = price_history[bt_cfg.benchmark]
    bench_prices = bench_df["close"]

    # Ensure all datetimes are tz-naive for comparison
    if (
        isinstance(bench_prices.index, pd.DatetimeIndex)
        and bench_prices.index.tz is not None
    ):
        bench_prices = bench_prices.tz_localize(None)

    # Filter to backtest period with tz-naive bounds
    start_bound = pd.Timestamp(bt_cfg.start_date).tz_localize(None)
    end_bound = pd.Timestamp(bt_cfg.end_date).tz_localize(None)
    mask = (bench_prices.index >= start_bound) & (bench_prices.index <= end_bound)
    bench_prices_filtered = bench_prices[mask]

    if (
        isinstance(bench_prices_filtered, pd.Series)
        and bench_prices_filtered.shape[0] > 1
    ):
        # Align benchmark to timeline (use Bollinger's index as reference)
        ref_index = bollinger_norm.index.union(momentum_norm.index).sort_values()
        bench_aligned = bench_prices_filtered.reindex(ref_index, method="pad").dropna()
        if (
            len(bench_aligned) > 1
            and bench_aligned.iloc[0] != 0
            and np.isfinite(bench_aligned.iloc[0])
        ):
            bench_series = bench_aligned / bench_aligned.iloc[0]

# 10) Plot strategies vs benchmark
fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    bollinger_norm.index,
    bollinger_norm.values,
    label=f"Bollinger (Cum: {(bollinger_norm.iloc[-1]-1):.2%})",
    linewidth=2,
    color="#1f77b4",
)
ax.plot(
    momentum_norm.index,
    momentum_norm.values,
    label=f"Momentum (Cum: {(momentum_norm.iloc[-1]-1):.2%})",
    linewidth=2,
    color="#2ca02c",
)

if bench_series is not None and len(bench_series) > 1:
    # Reindex again to ensure aligned with union of strategy indices
    ref_index = bollinger_norm.index.union(momentum_norm.index).sort_values()
    bench_plot = bench_series.reindex(ref_index, method="pad")
    ax.plot(
        bench_plot.index,
        bench_plot.values,
        label=f"{bt_cfg.benchmark} (Cum: {(bench_plot.iloc[-1]-1):.2%})",
        linewidth=2,
        color="#ff7f0e",
    )

# Drawdown shading based on the better performing strategy at each time for more context
# Choose Bollinger as default reference for shading
ref_norm = bollinger_norm.reindex(
    bollinger_norm.index.union(momentum_norm.index).sort_values(), method="pad"
)
running_max = ref_norm.cummax()
ax.fill_between(
    ref_norm.index,
    ref_norm.values,
    running_max.values,
    where=(ref_norm.values < running_max.values),
    color="#1f77b4",
    alpha=0.10,
    interpolate=True,
    label="_ddshade",
)

period_str = f"{pd.to_datetime(bollinger_result.start_date).date()} to {pd.to_datetime(bollinger_result.end_date).date()}"
ax.set_title(f"Strategy Comparison vs Benchmark (Normalized to 1.0) — {period_str}")
ax.set_ylabel("Growth of $1")
ax.set_xlabel("Date")

ax.legend(loc="best", frameon=True)
ax.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)

plt.tight_layout()
plt.show()

# Optional: print ending values for quick glance
print("Ending normalized values:")
print(
    "Bollinger:",
    round(float(bollinger_norm.iloc[-1]), 4),
    "Momentum:",
    round(float(momentum_norm.iloc[-1]), 4),
    "Benchmark:",
    round(float(bench_series.iloc[-1]), 4) if bench_series is not None else "n/a",
)

# %%
bollinger_result.strategy_name
