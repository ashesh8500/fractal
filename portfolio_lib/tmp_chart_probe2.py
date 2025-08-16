from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.models.strategy import StrategyConfig, BacktestConfig
from portfolio_lib.services.strategy.momentum import MomentumStrategy

from portfolio_lib.ui.strategy_workbench import _build_close_frame


def compute_weights_over_time(res, price_history):
    idx = pd.to_datetime(res.timestamps)
    closes = _build_close_frame(price_history).reindex(idx).ffill()
    weights = []
    last_w = pd.Series(0.0, index=closes.columns)
    for i, ts in enumerate(idx):
        hh = res.holdings_history[i] if i < len(res.holdings_history) else {}
        hh_series = pd.Series({k: float(hh.get(k, 0.0)) for k in closes.columns})
        ssum = float(hh_series.sum())
        if 0.98 <= ssum <= 1.02:
            w = hh_series.clip(lower=0.0)
            w = w / float(w.sum()) if float(w.sum()) > 0 else w
            last_w = w
            weights.append(w)
            continue
        prices = closes.loc[ts].reindex(closes.columns).astype(float)
        pos_val = hh_series * prices
        tot = float(pos_val.sum())
        if not (tot > 0) or not np.isfinite(tot):
            weights.append(last_w)
            continue
        w = (pos_val / tot).clip(lower=0.0)
        last_w = w
        weights.append(w)
    wdf = pd.concat(weights, axis=1).T
    wdf.index = idx
    return wdf


def run():
    syms = ["AAPL","MSFT","NVDA","AMZN","GOOGL","QQQ"]
    end = datetime.today().date()
    start = end - timedelta(days=365*3)
    data = YFinanceDataService()
    svc = BacktestingService(data)

    ph = data.fetch_price_history(syms, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    strat = MomentumStrategy()

    cap = 100_000.0
    valid = [s for s in syms if s in ph and not ph[s].empty]
    start_prices = {s: float(ph[s]["close"].iloc[0]) for s in valid}
    hh = {s: (cap/len(valid))/start_prices[s] for s in valid}

    cfg = StrategyConfig(name="momentum", rebalance_frequency="monthly")
    bt = BacktestConfig(
        start_date=datetime.combine(start, datetime.min.time()),
        end_date=datetime.combine(end, datetime.min.time()),
        initial_capital=cap,
        commission=0.0005,
        slippage=0.0002,
        benchmark="QQQ",
    )

    res = svc.run_backtest(strat, cfg, bt, hh)
    wdf = compute_weights_over_time(res, ph)

    print("weights df shape:", wdf.shape)
    # print samples: first date, a mid date, last date
    for pos in [0, len(wdf)//2, len(wdf)-1]:
        ts = wdf.index[pos]
        w = wdf.iloc[pos]
        nz = w[w>1e-6].sort_values(ascending=False)
        print(f"sample {pos}@{ts.date()}: sum={w.sum():.3f}, top={nz.head(5).round(3).to_dict()}")

    # Benchmark presence
    closes = _build_close_frame(ph).reindex(pd.to_datetime(res.timestamps)).ffill()
    has_bench = "QQQ" in closes.columns and closes["QQQ"].notna().any()
    print("benchmark present in closes:", has_bench)

if __name__ == "__main__":
    run()
