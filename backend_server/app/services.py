"""
Service layer for portfolio operations.
Uses functional programming and Result monad for clean error handling.
"""

from typing import Dict, Any
from datetime import datetime
import traceback
from .core.result import Result, AppError, ErrorType, AppResult, safe_call, validate
from .schemas import (
    PortfolioCreate, PortfolioResponse, StrategyExecuteRequest, 
    BacktestRequest, MarketDataRequest, DataProvider
)
from .storage import (
    init_db,
    upsert_portfolio,
    get_portfolio as db_get_portfolio,
    list_portfolios as db_list_portfolios,
    delete_portfolio as db_delete_portfolio,
)

# Ensure portfolio_lib is importable
import sys
import os
portfolio_lib_path = os.path.join(os.path.dirname(__file__), '../../portfolio_lib')
if portfolio_lib_path not in sys.path:
    sys.path.insert(0, portfolio_lib_path)

from portfolio_lib.models.portfolio import Portfolio
from portfolio_lib.models.strategy import StrategyConfig, BacktestConfig
from portfolio_lib.services.data.yfinance import YFinanceDataService
from portfolio_lib.services.data.alphavantage import AlphaVantageDataService


class PortfolioService:
    """Service for portfolio operations with functional error handling."""
    
    def __init__(self):
        self._portfolios: Dict[str, Portfolio] = {}
        self._data_services = {
            DataProvider.YFINANCE: YFinanceDataService(),
            # DataProvider.ALPHAVANTAGE: AlphaVantageDataService(api_key="demo")  # Commented out for now
        }
        # Initialize persistent storage
        try:
            init_db()
        except Exception:
            pass
    
    def create_portfolio(self, data: PortfolioCreate, provider: DataProvider = DataProvider.YFINANCE) -> AppResult[PortfolioResponse]:
        """Create a new portfolio."""
        return (
            self._validate_portfolio_name(data.name)
            .and_then(lambda _: self._create_portfolio_instance(data, provider))
            # Refresh market data post-create to initialize total_value/weights
            .and_then(lambda p: safe_call(lambda: (p.refresh_data(), p)[1]))
            .map(self._store_portfolio)
            .map(lambda p: (upsert_portfolio(p.name, p.holdings), p)[1])
            .map(self._portfolio_to_response)
        )
    
    def get_portfolio(self, name: str) -> AppResult[PortfolioResponse]:
        """Get a portfolio by name."""
        # If not in memory, try loading from DB and hydrate
        if name not in self._portfolios:
            db_row = db_get_portfolio(name)
            if db_row is not None:
                holdings = db_row.get("holdings", {})
                self._portfolios[name] = Portfolio(name=name, holdings=holdings, data_service=self._data_services[DataProvider.YFINANCE])
        return (self._find_portfolio(name).map(self._portfolio_to_response))
    
    def list_portfolios(self) -> AppResult[list[PortfolioResponse]]:
        """List all portfolios."""
        def _list():
            # Merge in DB ones not yet loaded
            db_rows = db_list_portfolios()
            for row in db_rows:
                n = row.get("name")
                if n and n not in self._portfolios:
                    holdings = row.get("holdings", {})
                    try:
                        self._portfolios[n] = Portfolio(name=n, holdings=holdings, data_service=self._data_services[DataProvider.YFINANCE])
                    except Exception:
                        continue
            return [self._portfolio_to_response(p) for p in self._portfolios.values()]
        return safe_call(_list)

    def update_portfolio(self, name: str, holdings: Dict[str, float]) -> AppResult[PortfolioResponse]:
        """Update a portfolio's holdings and persist to DB."""
        def _update() -> PortfolioResponse:
            # Update in-memory if exists, else create a new in-memory instance
            if name in self._portfolios:
                p = self._portfolios[name]
                p.holdings = holdings
                # Refresh derived values
                try:
                    p.refresh_data()
                except Exception:
                    pass
            else:
                p = Portfolio(name=name, holdings=holdings, data_service=self._data_services[DataProvider.YFINANCE])
                try:
                    p.refresh_data()
                except Exception:
                    pass
                self._portfolios[name] = p
            # Persist
            upsert_portfolio(name, holdings)
            return self._portfolio_to_response(self._portfolios[name])
        return safe_call(_update)

    def delete_portfolio(self, name: str) -> AppResult[Dict[str, Any]]:
        """Delete a portfolio from memory and DB."""
        self._portfolios.pop(name, None)
        ok = db_delete_portfolio(name)
        if not ok:
            return Result.err(AppError(ErrorType.NOT_FOUND, f"Portfolio '{name}' not found"))
        return Result.ok({"status": "deleted", "name": name})
    
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
            try:
                # Build StrategyConfig explicitly to match portfolio_lib signature
                if hasattr(request, "model_dump"):
                    data = request.model_dump()
                else:
                    data = request.__dict__

                cfg = StrategyConfig(
                    name=data.get("strategy_name") or getattr(request, "strategy_name", ""),
                    parameters=data.get("parameters") or {},
                    rebalance_frequency=data.get("rebalance_frequency", "monthly"),
                    risk_tolerance=data.get("risk_tolerance", 0.1),
                    max_position_size=data.get("max_position_size", 0.3),
                )

                result = portfolio.run_strategy(cfg.name, cfg)
            except Exception as e:
                traceback.print_exc()
                raise e
            # Normalize to dict if the model provides to_dict
            return result.to_dict() if hasattr(result, "to_dict") else result
        return safe_call(_exec)
    
    def _run_backtest(self, portfolio: Portfolio, request: BacktestRequest) -> AppResult[Any]:
        """Run backtest on portfolio using portfolio_lib implementation when available."""
        def _exec() -> Any:
            try:
                # Build BacktestConfig explicitly to avoid passing unsupported fields (e.g., strategy_name)
                if hasattr(request, "model_dump"):
                    data = request.model_dump()
                else:
                    data = request.__dict__

                cfg = BacktestConfig(
                    start_date=data.get("start_date"),
                    end_date=data.get("end_date"),
                    initial_capital=data.get("initial_capital", 100000.0),
                    commission=data.get("commission", 0.001),
                    slippage=data.get("slippage", 0.0005),
                    benchmark=data.get("benchmark", "SPY"),
                )

                strategy_name = data.get("strategy_name") or getattr(request, "strategy_name", "")
                result = portfolio.run_backtest(strategy_name, cfg)
            except Exception as e:
                traceback.print_exc()
                raise e
            return result.to_dict() if hasattr(result, "to_dict") else result
        return safe_call(_exec)
    
    def _fetch_current_prices(self, service, symbols: list[str]) -> AppResult[Dict[str, float]]:
        """Fetch current prices from data service."""
        return safe_call(lambda: service.fetch_current_prices(symbols))


# Global service instance
portfolio_service = PortfolioService()
