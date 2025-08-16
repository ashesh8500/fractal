import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from portfolio_lib.models.strategy import StrategyConfig, BacktestConfig
from portfolio_lib.services.backtesting.backtester import BacktestingService
from portfolio_lib.services.data.base import DataService
from portfolio_lib.services.strategy.bollinger import BollingerAttractivenessStrategy
from portfolio_lib.services.strategy.ml_attractiveness import MLAttractivenessStrategy
from portfolio_lib.services.strategy.custom.mean_reversion_strategy import MeanReversionStrategy
from portfolio_lib.services.strategy.momentum import MomentumStrategy


class MockDataService(DataService):
    def fetch_price_history(self, symbols, start_date, end_date):
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        result = {}
        for symbol in symbols:
            rng = np.random.default_rng(abs(hash(symbol)) % (2**32))
            base = 100.0 + (abs(hash(symbol)) % 50)
            prices = base + rng.normal(0, 1, size=len(dates)).cumsum() / 5.0
            df = pd.DataFrame({
                'open': prices,
                'high': prices * 1.01,
                'low': prices * 0.99,
                'close': prices,
                'volume': np.full(len(dates), 1_000_000),
            }, index=dates)
            result[symbol] = df
        return result

    def fetch_current_prices(self, symbols):
        # Not used by backtester core loop, but included for interface completeness
        return {s: 100.0 for s in symbols}

    def get_data_source_name(self) -> str:
        return "mock"

    def is_market_open(self) -> bool:
        return True


def _run_backtest(strategy, symbols):
    ds = MockDataService()
    svc = BacktestingService(ds)
    start = datetime.now() - timedelta(days=365)
    end = datetime.now()
    initial_holdings = {s: 10.0 for s in symbols}
    strat_cfg = StrategyConfig(name=strategy.name if hasattr(strategy, 'name') else 'test')
    backtest_cfg = BacktestConfig(start_date=start, end_date=end, initial_capital=100_000.0, benchmark='SPY')
    # Ensure benchmark is included in mock data implicitly by backtester when needed
    return svc.run_backtest(strategy, strat_cfg, backtest_cfg, initial_holdings)


def test_rebalance_trade_prices_bollinger():
    res = _run_backtest(BollingerAttractivenessStrategy(), ["AAPL", "MSFT", "GOOGL"]) 
    assert len(res.rebalance_details) >= 1
    for step in res.rebalance_details:
        for t in step.get("trades", []):
            assert t.get("price") is not None and t.get("price") > 0.0
            assert isinstance(t.get("timestamp"), str)


def test_rebalance_trade_prices_mlattractiveness():
    res = _run_backtest(MLAttractivenessStrategy(), ["AAPL", "MSFT", "GOOGL"]) 
    assert len(res.rebalance_details) >= 1
    for step in res.rebalance_details:
        for t in step.get("trades", []):
            assert t.get("price") is not None and t.get("price") > 0.0
            assert isinstance(t.get("timestamp"), str)


def test_rebalance_trade_prices_mean_reversion():
    res = _run_backtest(MeanReversionStrategy(), ["AAPL", "MSFT", "GOOGL"]) 
    assert len(res.rebalance_details) >= 1
    for step in res.rebalance_details:
        for t in step.get("trades", []):
            assert t.get("price") is not None and t.get("price") > 0.0
            assert isinstance(t.get("timestamp"), str)


def test_rebalance_trade_prices_momentum():
    res = _run_backtest(MomentumStrategy(), ["AAPL", "MSFT", "GOOGL"]) 
    assert len(res.rebalance_details) >= 1
    for step in res.rebalance_details:
        for t in step.get("trades", []):
            assert t.get("price") is not None and t.get("price") > 0.0
            assert isinstance(t.get("timestamp"), str)
