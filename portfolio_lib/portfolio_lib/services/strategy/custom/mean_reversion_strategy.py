import pandas as pd
from datetime import datetime
from typing import Dict

from portfolio_lib.services.strategy.base import BaseStrategy
from portfolio_lib.models.strategy import Trade, TradeAction, StrategyResult, StrategyConfig


class MeanReversionStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("mean_reversion")

    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig,
    ) -> StrategyResult:
        self._validate_inputs(portfolio_weights, price_history, current_prices)

        lookback = getattr(config, "lookback", 20)
        z_threshold = getattr(config, "z_threshold", 2.0)
        max_weight = getattr(config, "max_weight", 0.3)
        min_weight = getattr(config, "min_weight", 0.0)

        # Compute z-scores and target weights
        z_scores: Dict[str, float] = {}
        target_weights: Dict[str, float] = {}

        for symbol, df in price_history.items():
            try:
                closes = df["close"] if "close" in df.columns else df["Close"]
            except Exception:
                continue
            if len(closes) < lookback:
                continue

            recent = closes.iloc[-lookback:]
            mean_price = float(recent.mean())
            std_price = float(recent.std())
            cp = current_prices.get(symbol)
            if std_price <= 0 or cp is None or cp == 0:
                continue
            z = (float(cp) - mean_price) / std_price
            z_scores[symbol] = float(z)

            # Mean reversion rule: below mean -> increase, above mean -> decrease
            if z < -z_threshold:
                target_weights[symbol] = max_weight
            elif z > z_threshold:
                target_weights[symbol] = min_weight
            else:
                # keep current weight otherwise
                target_weights[symbol] = float(portfolio_weights.get(symbol, 0.0))

        # Ensure all portfolio symbols are present in target
        for s in portfolio_weights.keys():
            target_weights.setdefault(s, float(portfolio_weights.get(s, 0.0)))

        # Normalize
        total = sum(target_weights.values())
        if total > 0:
            target_weights = {k: v / total for k, v in target_weights.items()}

        # Build trades as weight delta
        trades = []
        for s, current_w in portfolio_weights.items():
            tgt = float(target_weights.get(s, 0.0))
            delta = tgt - float(current_w)
            if abs(delta) > 1e-4:
                trades.append(
                    Trade(
                        symbol=s,
                        action=TradeAction.BUY if delta > 0 else TradeAction.SELL,
                        quantity=abs(delta),
                        price=0.0,
                        timestamp=datetime.utcnow(),
                        reason=f"Rebalance to target {tgt:.2%} from {current_w:.2%}",
                    )
                )

        return StrategyResult(
            strategy_name=self.name,
            timestamp=datetime.utcnow(),
            trades=trades,
            expected_return=0.0,
            confidence=0.5,
            new_weights=target_weights,
            scores=z_scores,
        )