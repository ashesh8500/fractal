"""
Momentum Trading Strategy Implementation.

This strategy identifies assets with the strongest recent performance (momentum)
and rebalances the portfolio to hold these top-performing assets.
"""

import logging
from datetime import datetime
from typing import Dict, List
import pandas as pd

from portfolio_lib.models.strategy import (
    StrategyConfig, StrategyResult, Trade, TradeAction
)
from .base import BaseStrategy

logger = logging.getLogger(__name__)

class MomentumStrategy(BaseStrategy):
    """
    A simple momentum-based trading strategy.
    
    The strategy calculates the momentum of each asset over a specified
    lookback period and allocates funds to the top N performers.
    """

    def __init__(self):
        super().__init__(name="Momentum")

    def execute(
        self,
        portfolio_weights: Dict[str, float],
        price_history: Dict[str, pd.DataFrame],
        current_prices: Dict[str, float],
        config: StrategyConfig
    ) -> StrategyResult:
        """
        Execute the momentum strategy.

        Args:
            portfolio_weights: Current weights of assets in the portfolio.
            price_history: Historical price data for all assets.
            current_prices: Current market prices of all assets.
            config: Strategy configuration, including parameters like lookback period.

        Returns:
            A StrategyResult object with recommended trades and new weights.
        """
        self._validate_inputs(portfolio_weights, price_history, current_prices)

        # Get strategy parameters from config, with defaults
        lookback_period = config.parameters.get("lookback_period", 90)
        top_n = config.parameters.get("top_n", 3)

        self.logger.info(f"Executing momentum strategy with lookback={lookback_period} days, selecting top {top_n} assets.")

        # 1. Calculate momentum for each asset
        momentum_scores = {}
        for symbol, history_df in price_history.items():
            if len(history_df) >= lookback_period:
                # Use closing prices for momentum calculation
                close_prices = history_df['close']
                momentum = (close_prices.iloc[-1] / close_prices.iloc[-lookback_period]) - 1
                momentum_scores[symbol] = momentum
            else:
                momentum_scores[symbol] = -1 # Not enough data, low score

        # 2. Rank assets by momentum
        if not momentum_scores:
            self.logger.warning("No momentum scores could be calculated. No trades will be generated.")
            return self._create_empty_result(config)

        sorted_assets = sorted(momentum_scores.items(), key=lambda item: item[1], reverse=True)
        
        # 3. Select top N assets and determine new target weights
        top_assets = [asset for asset, score in sorted_assets[:top_n] if score > 0]
        
        if not top_assets:
            self.logger.warning("No assets with positive momentum found. Recommending holding all cash.")
            target_weights = {symbol: 0.0 for symbol in portfolio_weights}
        else:
            # Equal weighting for the top assets
            equal_weight = 1.0 / len(top_assets)
            target_weights = {symbol: equal_weight for symbol in top_assets}
        
        # Ensure all portfolio symbols are in the target_weights map
        for symbol in portfolio_weights:
            if symbol not in target_weights:
                target_weights[symbol] = 0.0

        # 4. Generate trades to rebalance to target weights
        trades = self._generate_rebalance_trades(portfolio_weights, target_weights, current_prices)

        self.logger.info(f"Momentum strategy recommends {len(trades)} trades.")

        return StrategyResult(
            strategy_name=self.name,
            timestamp=datetime.now(),
            trades=trades,
            new_weights=target_weights,
            expected_return=0.0,  # Placeholder, could be estimated from historical data
            confidence=0.8       # Placeholder confidence score
        )

    def _generate_rebalance_trades(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        current_prices: Dict[str, float]
    ) -> List[Trade]:
        """Compares current and target weights to generate trades."""
        trades = []
        all_symbols = set(current_weights.keys()) | set(target_weights.keys())

        # Assuming a total portfolio value of 1.0 for weight calculations
        total_portfolio_value = 1.0 

        for symbol in all_symbols:
            current_weight = current_weights.get(symbol, 0.0)
            target_weight = target_weights.get(symbol, 0.0)
            weight_diff = target_weight - current_weight

            if abs(weight_diff) > 1e-6: # Avoid tiny, insignificant trades
                price = current_prices.get(symbol)
                if not price or price <= 0:
                    self.logger.warning(f"Cannot generate trade for {symbol} due to missing or invalid price.")
                    continue

                # Quantity is relative to total value; actual shares depend on portfolio size
                quantity = (weight_diff * total_portfolio_value) / price

                if weight_diff > 0:
                    action = TradeAction.BUY
                    reason = f"Increasing weight from {current_weight:.2%} to {target_weight:.2%} based on momentum."
                else:
                    action = TradeAction.SELL
                    reason = f"Decreasing weight from {current_weight:.2%} to {target_weight:.2%} based on momentum."
                
                trades.append(Trade(
                    symbol=symbol,
                    action=action,
                    quantity=abs(quantity),
                    price=price,
                    timestamp=datetime.now(),
                    reason=reason
                ))
        return trades

    def _create_empty_result(self, config: StrategyConfig) -> StrategyResult:
        """Creates a result with no trades or weight changes."""
        return StrategyResult(
            strategy_name=config.name,
            timestamp=datetime.now(),
            trades=[],
            new_weights={},
            expected_return=0.0,
            confidence=0.0
        )

