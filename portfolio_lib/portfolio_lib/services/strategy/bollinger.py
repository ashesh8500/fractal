from typing import Dict

import pandas as pd

from portfolio_lib.models.strategy import StrategyConfig, StrategyResult
from portfolio_lib.services.backtesting.backtester import Trade, TradeAction
from portfolio_lib.services.strategy import BaseStrategy


class BollingerAttractivenessStrategy(BaseStrategy):
    """Bollinger Bands-based attractiveness strategy for portfolio rebalancing."""

    def __init__(self):
        super().__init__("bollinger_attractiveness")

    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig,
    ) -> StrategyResult:
        # Local imports to satisfy typing without altering module-level imports
        from datetime import datetime, timezone

        self._validate_inputs(portfolio_weights, price_history, current_prices)

        tickers = list(portfolio_weights.keys())
        bb_period = getattr(config, "bb_period", 20)
        bb_std = getattr(config, "bb_std", 2.0)
        initial_weights = getattr(
            config, "initial_weights", portfolio_weights
        )  # Fallback to current if not provided

        scores: Dict[str, float] = {}
        for tick in tickers:
            if tick not in price_history or len(price_history[tick]) < bb_period:
                scores[tick] = 0.0
                continue

            hist = price_history[tick]["close"].tail(bb_period)
            sma = hist.rolling(window=bb_period).mean()
            std = hist.rolling(window=bb_period).std()
            # Use the last numeric values for upper/lower bands to avoid array operations in comparisons
            upper_last = float((sma + bb_std * std).iloc[-1])
            lower_last = float((sma - bb_std * std).iloc[-1])
            price = float(current_prices[tick])

            denom = upper_last - lower_last
            if denom != 0.0:
                pb = (price - lower_last) / denom
                pb = float(pb)
            else:
                pb = 0.5

            # Ensure scalar float for score to satisfy typing
            score = max(0.0, float(1.0 - pb))
            scores[tick] = score

        sum_scores = sum(scores.values())
        if sum_scores > 0:
            target_weights = {t: scores[t] / sum_scores for t in tickers}
        else:
            target_weights = {t: float(initial_weights.get(t, 0.0)) for t in tickers}

        # Normalize target weights to sum to 1 (in case of fallback or rounding)
        total = sum(target_weights.values())
        if total > 0:
            target_weights = {t: w / total for t, w in target_weights.items()}
        else:
            # If total is zero, fall back to current portfolio weights
            target_weights = dict(portfolio_weights)

        trades = []
        for tick in tickers:
            delta = target_weights.get(tick, 0.0) - portfolio_weights.get(tick, 0.0)
            if delta > 0:
                trades.append(
                    Trade(symbol=tick, action=TradeAction.BUY, quantity=delta)
                )
            elif delta < 0:
                trades.append(
                    Trade(symbol=tick, action=TradeAction.SELL, quantity=-delta)
                )

        # Simple heuristic for expected return and confidence
        expected_return = 0.0
        confidence = 0.5

        return StrategyResult(
            strategy_name="Bollinger Bands",
            trades=trades,
            expected_return=expected_return,
            timestamp=datetime.now(timezone.utc),
            confidence=confidence,
            new_weights=target_weights,
        )
