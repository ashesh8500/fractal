from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

from portfolio_lib.models.strategy import StrategyConfig, StrategyResult
from portfolio_lib.services.backtesting.backtester import Trade, TradeAction
from portfolio_lib.services.strategy import BaseStrategy


class BollingerAttractivenessStrategy(BaseStrategy):
    """Bollinger Bands-based attractiveness strategy for portfolio rebalancing with momentum and clipping."""

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

        # Hyperparameters (provide sensible defaults, overridable via config)
        bb_period = getattr(config, "bb_period", 20)
        bb_std = getattr(config, "bb_std", 2.0)
        momentum_window = getattr(config, "momentum_window", 252)  # ~1y daily trading days
        vol_window = getattr(config, "vol_window", 252)
        adjust_factor = getattr(config, "adjustment_factor", 0.2)
        min_weight = getattr(config, "min_weight", 0.0)
        max_weight = getattr(config, "max_weight", 0.6)
        use_vol_momentum = getattr(config, "use_vol_momentum", True)
        attractiveness_weight = getattr(config, "attractiveness_weight", 0.5)  # 0..1 to mix bollinger vs attractiveness
        initial_weights = getattr(config, "initial_weights", portfolio_weights)

        tickers = list(portfolio_weights.keys())

        # Build a unified close price DataFrame from provided price_history for needed tickers
        closes = self._extract_closes(price_history, tickers)

        # Compute indicators:
        # 1) Bollinger %b using current price and recent history
        pb_scores = self._compute_bollinger_pb(closes, current_prices, bb_period, bb_std)

        # 2) Volatility and momentum attractiveness (optional)
        if use_vol_momentum and len(closes) >= max(momentum_window, vol_window) // 2:
            vol_change, momentum_change = self._compute_vol_and_momentum_changes(closes, vol_window, momentum_window)
            attractiveness = self._calculate_attractiveness(vol_change, momentum_change)  # product form
            # Normalize attractiveness to positive values; fall back if all non-positive or NaN
            attractiveness = self._normalize_series_safe(attractiveness, tickers)
        else:
            attractiveness = pd.Series(1.0, index=tickers)

        # 3) Combine with Bollinger signal: lower %b is more attractive => score = 1 - %b
        bollinger_pref = (1.0 - pb_scores).clip(lower=0.0, upper=1.0)
        bollinger_pref = self._normalize_series_safe(bollinger_pref, tickers)

        # 4) Blend attractiveness with bollinger preference
        combined_scores = attractiveness_weight * bollinger_pref + (1.0 - attractiveness_weight) * attractiveness
        combined_scores = self._normalize_series_safe(combined_scores, tickers)

        # 5) Convert scores to target weights
        target_weights = combined_scores.to_dict()

        # 6) Fallback handling when all scores degenerate
        if sum(target_weights.values()) <= 0:
            target_weights = {t: float(initial_weights.get(t, 0.0)) for t in tickers}

        # 7) Normalize and clip weights, then renormalize
        target_weights = self._normalize_dict(target_weights)
        target_weights_series = pd.Series(target_weights).reindex(tickers).fillna(0.0)
        target_weights_series = self._clip_weights(target_weights_series, min_weight=min_weight, max_weight=max_weight)
        target_weights_series = self._renormalize_safe(target_weights_series)

        # 8) Blend with current weights using adjustment factor
        current_w_series = pd.Series({t: portfolio_weights.get(t, 0.0) for t in tickers})
        blended = (1.0 - adjust_factor) * current_w_series + adjust_factor * target_weights_series
        blended = self._clip_weights(blended, min_weight=min_weight, max_weight=max_weight)
        blended = self._renormalize_safe(blended)

        # 9) Build trades based on delta
        trades = self._build_trades_from_delta(current_w_series, blended)

        # Simple heuristic for expected return and confidence
        expected_return = 0.0
        confidence = 0.6 if use_vol_momentum else 0.5

        return StrategyResult(
            strategy_name="Bollinger Bands + Attractiveness",
            trades=trades,
            expected_return=expected_return,
            timestamp=datetime.now(timezone.utc),
            confidence=confidence,
            new_weights=blended.to_dict(),
        )

    def _extract_closes(self, price_history: Dict[str, pd.DataFrame], tickers: List[str]) -> pd.DataFrame:
        # Assumes each df has a 'close' or 'Close' column; will forward-fill and align
        series_list = []
        for t in tickers:
            df = price_history.get(t)
            if df is None or df.empty:
                continue
            col = None
            if "close" in df.columns:
                col = "close"
            elif "Close" in df.columns:
                col = "Close"
            if col is None:
                continue
            s = df[col].rename(t)
            series_list.append(s)
        if not series_list:
            return pd.DataFrame(columns=tickers)
        closes = pd.concat(series_list, axis=1).sort_index().ffill()
        # Keep only requested tickers order
        closes = closes.reindex(columns=tickers)
        return closes

    def _compute_bollinger_pb(
        self, closes: pd.DataFrame, current_prices: Dict[str, float], period: int, num_std: float
    ) -> pd.Series:
        tickers = list(closes.columns)
        pb = {}
        for t in tickers:
            series = closes[t].dropna()
            if len(series) < max(2, period):
                pb[t] = 0.5  # neutral if insufficient data
                continue
            sma = series.rolling(window=period).mean().iloc[-1]
            std = series.rolling(window=period).std().iloc[-1]
            upper = sma + num_std * std
            lower = sma - num_std * std
            price = float(current_prices.get(t, series.iloc[-1]))
            denom = upper - lower
            pb[t] = float((price - lower) / denom) if denom and denom != 0.0 else 0.5
        return pd.Series(pb)

    def _compute_vol_and_momentum_changes(
        self, closes: pd.DataFrame, vol_window: int, momentum_window: int
    ) -> Tuple[pd.Series, pd.Series]:
        returns = closes.pct_change()
        # Rolling volatility annualized-like (sqrt(252)) similar to reference, but windowed
        vol = returns.rolling(window=vol_window, min_periods=max(5, vol_window // 2)).std() * np.sqrt(252)
        vol_change = vol.pct_change().iloc[-1].replace([np.inf, -np.inf], np.nan)

        # Momentum as rolling sum of returns
        momentum = returns.rolling(window=momentum_window, min_periods=max(5, momentum_window // 2)).sum()
        momentum_change = momentum.pct_change().iloc[-1].replace([np.inf, -np.inf], np.nan)
        return vol_change, momentum_change

    def _calculate_attractiveness(self, vol_change: pd.Series, momentum_change: pd.Series) -> pd.Series:
        # Avoid division by zero and negative blowups
        vol_score = 1.0 / (1.0 + vol_change.fillna(0.0))
        momentum_score = 1.0 + momentum_change.fillna(0.0)
        attr = vol_score * momentum_score
        # Replace non-finite
        attr = attr.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return attr

    def _normalize_series_safe(self, s: pd.Series, tickers: List[str]) -> pd.Series:
        s = s.reindex(tickers).fillna(0.0)
        total = float(s.sum())
        if total > 0:
            return s / total
        # if all zeros or negative, default to equal weights
        n = len(tickers)
        if n == 0:
            return s
        return pd.Series({t: 1.0 / n for t in tickers})

    def _normalize_dict(self, d: Dict[str, float]) -> Dict[str, float]:
        total = float(sum(d.values()))
        if total > 0:
            return {k: v / total for k, v in d.items()}
        n = len(d)
        if n == 0:
            return d
        return {k: 1.0 / n for k in d.keys()}

    def _clip_weights(self, weights: pd.Series, min_weight: float, max_weight: float) -> pd.Series:
        if min_weight is None and max_weight is None:
            return weights
        min_w = 0.0 if min_weight is None else float(min_weight)
        max_w = 1.0 if max_weight is None else float(max_weight)
        clipped = weights.clip(lower=min_w, upper=max_w)
        return clipped

    def _renormalize_safe(self, weights: pd.Series) -> pd.Series:
        total = float(weights.sum())
        if total > 0:
            return weights / total
        # Fall back to equal weights if degenerate
        n = len(weights)
        if n == 0:
            return weights
        return pd.Series([1.0 / n] * n, index=weights.index)

    def _build_trades_from_delta(self, current: pd.Series, target: pd.Series) -> List[Trade]:
        trades: List[Trade] = []
        for tick in current.index:
            delta = float(target.get(tick, 0.0) - current.get(tick, 0.0))
            if delta > 0:
                trades.append(Trade(symbol=tick, action=TradeAction.BUY, quantity=delta))
            elif delta < 0:
                trades.append(Trade(symbol=tick, action=TradeAction.SELL, quantity=-delta))
        return trades
