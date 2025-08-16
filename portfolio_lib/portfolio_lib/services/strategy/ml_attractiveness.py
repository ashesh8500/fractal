from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from portfolio_lib.models.strategy import StrategyConfig, StrategyResult, Trade, TradeAction
from portfolio_lib.services.strategy import BaseStrategy


class MLAttractivenessStrategy(BaseStrategy):
    """
    Momentum + Volatility-change based 'attractiveness' strategy,
    blended with Bollinger %b preference, with clipping and gradual adjustment.

    This adapts the provided algorithmic essence to the BaseStrategy interface.
    """

    def __init__(self):
        super().__init__("ml_attractiveness")

    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig,
    ) -> StrategyResult:
        from datetime import datetime, timezone

        self._validate_inputs(portfolio_weights, price_history, current_prices)

        # Hyperparameters with sensible defaults (overridable via config)
        bb_period = getattr(config, "bb_period", 20)
        bb_std = getattr(config, "bb_std", 2.0)
        momentum_window = getattr(config, "momentum_window", 252)
        vol_window = getattr(config, "vol_window", 252)
        adjust_factor = getattr(config, "adjustment_factor", 0.2)
        min_weight = getattr(config, "min_weight", 0.05)
        max_weight = getattr(config, "max_weight", 0.40)
        attractiveness_weight = getattr(config, "attractiveness_weight", 0.5)  # blend between bollinger and attractiveness
        use_bollinger = getattr(config, "use_bollinger", True)
        use_vol_momentum = getattr(config, "use_vol_momentum", True)

        tickers = list(portfolio_weights.keys())

        closes = self._extract_closes(price_history, tickers)

        # Compute attractiveness from volatility change and momentum change
        if use_vol_momentum and not closes.empty:
            vol_chg, mom_chg = self._compute_vol_and_momentum_changes(closes, vol_window, momentum_window)
            attractiveness = self._calculate_attractiveness(vol_chg, mom_chg)
            attractiveness = self._normalize_series_safe(attractiveness, tickers)
        else:
            attractiveness = pd.Series(1.0, index=tickers)
            attractiveness = self._normalize_series_safe(attractiveness, tickers)

        # Compute Bollinger preference (lower %b implies more attractive)
        if use_bollinger and not closes.empty:
            pb = self._compute_bollinger_pb(closes, current_prices, bb_period, bb_std)
            bollinger_pref = (1.0 - pb).clip(lower=0.0, upper=1.0)
            bollinger_pref = self._normalize_series_safe(bollinger_pref, tickers)
        else:
            bollinger_pref = pd.Series(1.0, index=tickers)
            bollinger_pref = self._normalize_series_safe(bollinger_pref, tickers)

        # Combine signals
        combined_scores = attractiveness_weight * bollinger_pref + (1.0 - attractiveness_weight) * attractiveness
        combined_scores = self._normalize_series_safe(combined_scores, tickers)

        # Convert to target weights, clip and renormalize
        target = combined_scores.reindex(tickers).fillna(0.0)
        target = self._clip_weights(target, min_weight=min_weight, max_weight=max_weight)
        target = self._renormalize_safe(target)

        # Gradual adjustment
        current_w = pd.Series({t: float(portfolio_weights.get(t, 0.0)) for t in tickers})
        blended = (1.0 - adjust_factor) * current_w + adjust_factor * target
        blended = self._clip_weights(blended, min_weight=min_weight, max_weight=max_weight)
        blended = self._renormalize_safe(blended)

        trades = self._build_trades_from_delta(current_w, blended)

        # Heuristic expected return/confidence placeholders
        expected_return = 0.0
        confidence = 0.6 if use_vol_momentum or use_bollinger else 0.5

        return StrategyResult(
            strategy_name="ML Attractiveness (Momentum + Vol Change + Bollinger)",
            trades=trades,
            expected_return=expected_return,
            timestamp=datetime.now(timezone.utc),
            confidence=confidence,
            new_weights=blended.to_dict(),
        )

    def _extract_closes(self, price_history: Dict[str, pd.DataFrame], tickers: List[str]) -> pd.DataFrame:
        series_list = []
        for t in tickers:
            df = price_history.get(t)
            if df is None or df.empty:
                continue
            col = "close" if "close" in df.columns else ("Close" if "Close" in df.columns else None)
            if col is None:
                continue
            s = df[col].rename(t)
            series_list.append(s)
        if not series_list:
            return pd.DataFrame(columns=tickers)
        closes = pd.concat(series_list, axis=1).sort_index().ffill()
        return closes.reindex(columns=tickers)

    def _compute_bollinger_pb(self, closes: pd.DataFrame, current_prices: Dict[str, float], period: int, num_std: float) -> pd.Series:
        tickers = list(closes.columns)
        pb = {}
        for t in tickers:
            series = closes[t].dropna()
            if len(series) < max(2, period):
                pb[t] = 0.5
                continue
            sma = series.rolling(window=period).mean().iloc[-1]
            std = series.rolling(window=period).std().iloc[-1]
            upper = sma + num_std * std
            lower = sma - num_std * std
            cp_val = current_prices.get(t, None)
            price = float(series.iloc[-1] if cp_val is None else cp_val)
            denom = upper - lower
            pb[t] = float((price - lower) / denom) if denom and denom != 0.0 else 0.5
        return pd.Series(pb)

    def _compute_vol_and_momentum_changes(self, closes: pd.DataFrame, vol_window: int, momentum_window: int) -> Tuple[pd.Series, pd.Series]:
        returns = closes.pct_change()
        vol = returns.rolling(window=vol_window, min_periods=max(5, vol_window // 2)).std() * np.sqrt(252)
        vol_change = vol.pct_change().iloc[-1].replace([np.inf, -np.inf], np.nan)

        momentum = returns.rolling(window=momentum_window, min_periods=max(5, momentum_window // 2)).sum()
        momentum_change = momentum.pct_change().iloc[-1].replace([np.inf, -np.inf], np.nan)
        return vol_change, momentum_change

    def _calculate_attractiveness(self, vol_change: pd.Series, momentum_change: pd.Series) -> pd.Series:
        vol_score = 1.0 / (1.0 + vol_change.fillna(0.0))
        momentum_score = 1.0 + momentum_change.fillna(0.0)
        attr = (vol_score * momentum_score).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return attr

    def _clip_weights(self, weights: pd.Series, min_weight: float, max_weight: float) -> pd.Series:
        min_w = 0.0 if min_weight is None else float(min_weight)
        max_w = 1.0 if max_weight is None else float(max_weight)
        return weights.clip(lower=min_w, upper=max_w)

    def _renormalize_safe(self, weights: pd.Series) -> pd.Series:
        total = float(weights.sum())
        if total > 0:
            return weights / total
        n = len(weights)
        if n == 0:
            return weights
        return pd.Series([1.0 / n] * n, index=weights.index)

    def _normalize_series_safe(self, s: pd.Series, tickers: List[str]) -> pd.Series:
        s = s.reindex(tickers).fillna(0.0)
        total = float(s.sum())
        if total > 0:
            return s / total
        n = len(tickers)
        if n == 0:
            return s
        return pd.Series({t: 1.0 / n for t in tickers})

    def _build_trades_from_delta(self, current: pd.Series, target: pd.Series) -> List[Trade]:
        trades: List[Trade] = []
        eps = 1e-6
        for tick in current.index:
            delta = float(target.get(tick, 0.0) - current.get(tick, 0.0))
            if delta > eps:
                trades.append(Trade(symbol=tick, action=TradeAction.BUY, quantity=delta))
            elif delta < -eps:
                trades.append(Trade(symbol=tick, action=TradeAction.SELL, quantity=-delta))
        return trades
