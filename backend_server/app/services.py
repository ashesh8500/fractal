"""
Service layer for portfolio operations.
Uses functional programming and Result monad for clean error handling.
"""

import sys
import os

# Add portfolio_lib to Python path
portfolio_lib_path = os.path.join(os.path.dirname(__file__), '../../portfolio_lib')
if portfolio_lib_path not in sys.path:
    sys.path.insert(0, portfolio_lib_path)

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
            # DataProvider.ALPHAVANTAGE: AlphaVantageDataService(api_key="demo")  # Commented out for now
        }
    
    def create_portfolio(self, data: PortfolioCreate, provider: DataProvider = DataProvider.YFINANCE) -> AppResult[PortfolioResponse]:
        """Create a new portfolio."""
        return (
            self._validate_portfolio_name(data.name)
            .and_then(lambda _: self._create_portfolio_instance(data, provider))
            # Refresh market data post-create to initialize total_value/weights
            .and_then(lambda p: safe_call(lambda: (p.refresh_data(), p)[1]))
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
        if provider not in self._data_services:
            return Result.err(AppError(ErrorType.VALIDATION_ERROR, f"Data provider {provider} not available"))
        
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
        from .schemas import RiskMetrics, PerformanceMetrics
        
        # Get risk and performance metrics from portfolio, with defaults if not available
        risk_metrics = getattr(portfolio, 'risk_metrics', None)
        if risk_metrics is None:
            risk_metrics = RiskMetrics()
        else:
            # Convert portfolio risk metrics to schema format
            risk_dict = risk_metrics.to_dict() if hasattr(risk_metrics, 'to_dict') else {}
            risk_metrics = RiskMetrics(
                volatility=risk_dict.get('volatility') or 0.0,
                sharpe_ratio=risk_dict.get('sharpe_ratio') or 0.0,
                max_drawdown=risk_dict.get('max_drawdown') or 0.0,
                var_95=risk_dict.get('var_95') or 0.0
            )
        
        performance_metrics = getattr(portfolio, 'performance_metrics', None)
        if performance_metrics is None:
            performance_metrics = PerformanceMetrics()
        else:
            # Convert portfolio performance metrics to schema format
            perf_dict = performance_metrics.to_dict() if hasattr(performance_metrics, 'to_dict') else {}
            performance_metrics = PerformanceMetrics(
                total_return=perf_dict.get('total_return') or 0.0,
                annualized_return=perf_dict.get('annualized_return') or 0.0,
                alpha=perf_dict.get('alpha') or 0.0,
                beta=perf_dict.get('beta') or 0.0
            )
        
        return PortfolioResponse(
            name=portfolio.name,
            holdings=portfolio.holdings,
            total_value=portfolio.total_value,
            current_weights=portfolio.current_weights,
            created_at=portfolio.created_at,
            risk_metrics=risk_metrics,
            performance_metrics=performance_metrics,
            data_provider=portfolio.data_service.get_data_source_name() if hasattr(portfolio.data_service, 'get_data_source_name') else "yfinance"
        )
    
    def _run_strategy(self, portfolio: Portfolio, request: StrategyExecuteRequest) -> AppResult[Any]:
        """Execute strategy on portfolio using portfolio_lib implementation when available."""
        def _exec() -> Any:
            # Convert request to StrategyConfig if needed
            cfg = StrategyConfig(**request.model_dump()) if hasattr(request, "model_dump") else StrategyConfig(**request.__dict__)
            result = portfolio.run_strategy(request.strategy_name, cfg)
            # Normalize to dict if the model provides to_dict
            return result.to_dict() if hasattr(result, "to_dict") else result
        return safe_call(_exec)
    
    def _run_backtest(self, portfolio: Portfolio, request: BacktestRequest) -> AppResult[Any]:
        """Run backtest on portfolio using portfolio_lib implementation when available."""
        def _exec() -> Any:
            cfg = BacktestConfig(**request.model_dump()) if hasattr(request, "model_dump") else BacktestConfig(**request.__dict__)
            result = portfolio.run_backtest(request.strategy_name, cfg)
            return result.to_dict() if hasattr(result, "to_dict") else result
        return safe_call(_exec)
    
    def _fetch_current_prices(self, service, symbols: list[str]) -> AppResult[Dict[str, float]]:
        """Fetch current prices from data service."""
        return safe_call(lambda: service.fetch_current_prices(symbols))


# Global service instance
portfolio_service = PortfolioService()
