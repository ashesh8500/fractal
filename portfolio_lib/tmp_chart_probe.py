from datetime import datetime, timedelta
import pandas as pd

from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.models.strategy import StrategyConfig, BacktestConfig
from portfolio_lib.services.strategy.momentum import MomentumStrategy


def run():
    syms = ["AAPL","MSFT","NVDA","AMZN","GOOGL","QQQ"]
    end = datetime.today().date()
    start = end - timedelta(days=365*3)
    data = YFinanceDataService()
    svc = BacktestingService(data)

    # fetch prices to inspect
    ph = data.fetch_price_history(syms, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print("symbols fetched:", list(ph.keys()))
    print("sample AAPL head:")
    print(ph["AAPL"].head() if "AAPL" in ph else None)

    # equal capital initial holdings
    valid = [s for s in syms if s in ph and not ph[s].empty]
    start_prices = {s: float(ph[s]["close"].iloc[0]) for s in valid}
    cap = 100_000.0
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

    strat = MomentumStrategy()
    res = svc.run_backtest(strat, cfg, bt, hh)

    print("timestamps:", len(res.timestamps), str(res.timestamps[0]) if res.timestamps else None, str(res.timestamps[-1]) if res.timestamps else None)
    print("portfolio_values:", len(res.portfolio_values), res.portfolio_values[:3])
    print("holdings_history len:", len(res.holdings_history))
    print("holdings first 2:", res.holdings_history[:2] if res.holdings_history else None)
    print("executed_trades count:", len(getattr(res, "executed_trades", [])))

    # Build closes frame like UI does
    def _build_close_frame(price_history):
        series = []
        for sym, df in price_history.items():
            if df is None or df.empty:
                continue
            col = 'close' if 'close' in df.columns else ('Close' if 'Close' in df.columns else None)
            if not col:
                continue
            s = pd.Series(df[col].values, index=pd.to_datetime(df.index), name=sym)
            series.append(s)
        return pd.concat(series, axis=1).sort_index().ffill() if series else pd.DataFrame()

    closes = _build_close_frame(ph).reindex(pd.to_datetime(res.timestamps)).ffill()
    print("closes shape:", closes.shape)
    print("weights sample day 0 computed from holdings*price:")
    if len(res.timestamps) > 0:
        ts0 = pd.to_datetime(res.timestamps[0])
        prices0 = closes.loc[ts0].reindex(closes.columns).astype(float)
        hh0 = pd.Series(res.holdings_history[0]).reindex(closes.columns).fillna(0.0)
        pv0 = hh0 * prices0
        tot0 = float(pv0.sum())
        w0 = (pv0/tot0) if tot0>0 else pv0
        print(w0[w0>0].round(3).to_dict())

if __name__ == "__main__":
    run()
