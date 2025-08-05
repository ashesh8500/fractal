# %%
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import BacktestConfig, StrategyConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.strategy.bollinger import BollingerAttractivenessStrategy

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

# 6) Configure the Momentum strategy
# Parameters:
# - lookback_period: number of days to compute momentum
# - top_n: hold the top N momentum names equally
# - rebalance_frequency: 'daily'|'weekly'|'monthly'|'quarterly' (backtester rebalances on this cadence)
strategy = BollingerAttractivenessStrategy()
st_cfg = StrategyConfig(
    name="Bollinger",
    parameters={"lookback_period": 90, "top_n": 5},
    rebalance_frequency="monthly",
    risk_tolerance=0.5,
    max_position_size=1.0,
)

# 7) Run backtest
result = backtester.run_backtest(
    strategy=strategy,
    strategy_config=st_cfg,
    backtest_config=bt_cfg,
    initial_holdings=initial_holdings,
)

# 8) Metrics
print("Strategy:", result.strategy_name)
print("Period:", result.start_date.date(), "to", result.end_date.date())
print(f"Total Return: {result.total_return:.2%}")
print(f"Annualized Return: {result.annualized_return:.2%}")
print(f"Volatility: {result.volatility:.2%}")
print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.max_drawdown:.2%}")
print(f"Benchmark (QQQ) Return: {result.benchmark_return:.2%}")
print(
    "Trades - total/wins/loses:",
    result.total_trades,
    result.winning_trades,
    result.losing_trades,
)

# 9) Plot equity curve with benchmark
pv = pd.Series(result.portfolio_values, index=pd.to_datetime(result.timestamps))
pv = pv.sort_index()
fig, ax = plt.subplots(figsize=(12, 6))
pv.plot(ax=ax, label=f"{result.strategy_name} Portfolio", linewidth=2)

# Plot benchmark if available
# Remove reliance on unknown BacktestResult attributes; use fallback from price history
if bt_cfg.benchmark in price_history:
    bench_df = price_history[bt_cfg.benchmark]
    bench_prices = bench_df["close"]
    # Filter to backtest period
    start_bound = pd.Timestamp(bt_cfg.start_date)
    end_bound = pd.Timestamp(bt_cfg.end_date)
    mask = (bench_prices.index >= start_bound) & (bench_prices.index <= end_bound)
    bench_prices_filtered = bench_prices[mask]

    if (
        isinstance(bench_prices_filtered, pd.Series)
        and bench_prices_filtered.shape[0] > 1
    ):
        # Normalize to start at 1 for comparison
        first_val = float(bench_prices_filtered.iloc[0])
        if np.isfinite(first_val) and first_val != 0:
            bench_normalized = bench_prices_filtered / first_val
            bench_series = pd.Series(
                bench_normalized.values, index=bench_prices_filtered.index
            )
            bench_series.plot(ax=ax, label="Benchmark (QQQ)", linewidth=2)

ax.set_title("Portfolio Value vs Benchmark")
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.show()

# %%
result.portfolio_values
