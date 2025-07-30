"""
Service layer for portfolio operations.
Uses functional programming and Result monad for clean error handling.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from typing import Dict, Any
from datetime import datetime

from portfolio_lib.models.portfolio import Portfolio
from portfolio_lib.models.strategy import StrategyConfig, BacktestConfig
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.data.alphavantage import AlphaVantageDataService

from .core.result import Result, AppError, ErrorType, AppResult, safe_call, validate
from .schemas import (
    PortfolioCreate, PortfolioResponse, StrategyExecuteRequest, 
    BacktestRequest, MarketDataRequest, DataProvider
)


class PortfolioService:
    """Service for portfolio operations with functional error handling."""
    
    def __init__(self):
        self._portfolios: Dict[str, Portfolio] = {}
        self._data_services = {
            DataProvider.YFINANCE: YFinanceDataService(),
            DataProvider.ALPHAVANTAGE: AlphaVantageDataService(api_key="demo")
        }
    
    def create_portfolio(self, data: PortfolioCreate, provider: DataProvider = DataProvider.YFINANCE) -> AppResult[PortfolioResponse]:
        """Create a new portfolio."""
        return (
            self._validate_portfolio_name(data.name)
            .and_then(lambda _: self._create_portfolio_instance(data, provider))
            .map(self._store_portfolio)
            .map(self._portfolio_to_response)
        )
    
    def get_portfolio(self, name: str) -> AppResult[PortfolioResponse]:
        """Get a portfolio by name."""
        return (
            self._find_portfolio(name)
            .map(self._portfolio_to_response)
        )
    
    def list_portfolios(self) -> AppResult[list[PortfolioResponse]]:
        """List all portfolios."""
        return safe_call(
            lambda: [self._portfolio_to_response(p) for p in self._portfolios.values()]
        )
    
    def execute_strategy(self, portfolio_name: str, request: StrategyExecuteRequest) -> AppResult[Any]:
        """Execute a strategy on a portfolio."""
        return (
            self._find_portfolio(portfolio_name)
            .and_then(lambda p: self._run_strategy(p, request))
        )
    
    def run_backtest(self, portfolio_name: str, request: BacktestRequest) -> AppResult[Any]:
        """Run a backtest on a portfolio."""
        return (
            self._find_portfolio(portfolio_name)
            .and_then(lambda p: self._run_backtest(p, request))
        )
    
    def get_market_data(self, request: MarketDataRequest) -> AppResult[Dict[str, float]]:
        """Get current market data."""
        return (
            safe_call(lambda: self._data_services[request.provider])
            .and_then(lambda service: self._fetch_current_prices(service, request.symbols))
        )
    
    # Private helper methods
    
    def _validate_portfolio_name(self, name: str) -> AppResult[None]:
        """Validate portfolio name is unique."""
        if name in self._portfolios:
            return Result.err(AppError(ErrorType.VALIDATION_ERROR, f"Portfolio '{name}' already exists"))
        return Result.ok(None)
    
    def _create_portfolio_instance(self, data: PortfolioCreate, provider: DataProvider) -> AppResult[Portfolio]:
        """Create portfolio instance."""
        return safe_call(lambda: Portfolio(
            name=data.name,
            holdings=data.holdings,
            data_service=self._data_services[provider]
        ))
    
    def _store_portfolio(self, portfolio: Portfolio) -> Portfolio:
        """Store portfolio in memory."""
        self._portfolios[portfolio.name] = portfolio
        return portfolio
    
    def _find_portfolio(self, name: str) -> AppResult[Portfolio]:
        """Find portfolio by name."""
        portfolio = self._portfolios.get(name)
        if not portfolio:
            return Result.err(AppError(ErrorType.NOT_FOUND, f"Portfolio '{name}' not found"))
        return Result.ok(portfolio)
    
    def _portfolio_to_response(self, portfolio: Portfolio) -> PortfolioResponse:
        """Convert portfolio to response schema."""
        return PortfolioResponse(
            name=portfolio.name,
            holdings=portfolio.holdings,
            total_value=portfolio.total_value,
            current_weights=portfolio.current_weights,
            created_at=portfolio.created_at
        )
    
    def _run_strategy(self, portfolio: Portfolio, request: StrategyExecuteRequest) -> AppResult[Any]:
        """Execute strategy on portfolio."""
        return safe_call(lambda: portfolio.run_strategy(
            request.strategy_name,
            StrategyConfig(
                name=request.strategy_name,
                parameters=request.parameters,
                rebalance_frequency=request.rebalance_frequency,
                risk_tolerance=request.risk_tolerance,
                max_position_size=request.max_position_size
            )
        ))
    
    def _run_backtest(self, portfolio: Portfolio, request: BacktestRequest) -> AppResult[Any]:
        """Run backtest on portfolio."""
        return safe_call(lambda: portfolio.run_backtest(
            request.strategy_name,
            BacktestConfig(
                start_date=request.start_date,
                end_date=request.end_date,
                initial_capital=request.initial_capital,
                commission=request.commission,
                slippage=request.slippage,
                benchmark=request.benchmark
            )
        ))
    
    def _fetch_current_prices(self, service, symbols: list[str]) -> AppResult[Dict[str, float]]:
        """Fetch current prices from data service."""
        return safe_call(lambda: service.fetch_current_prices(symbols))


# Global service instance
portfolio_service = PortfolioService()
