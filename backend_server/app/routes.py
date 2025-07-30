"""
FastAPI routes with functional error handling using Result monad.
Clean, composable API design.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from .schemas import (
    PortfolioCreate, PortfolioResponse, StrategyExecuteRequest, 
    BacktestRequest, MarketDataRequest, DataProvider, ErrorResponse
)
from .services import portfolio_service
from .core.result import Result, AppError, ErrorType


# Create API router
api_router = APIRouter(prefix="/api/v1", tags=["portfolio"])


def handle_result(result, success_status: int = 200):
    """Convert Result monad to FastAPI response."""
    if result.is_ok():
        return result.unwrap()
    
    error = result.unwrap_err()
    status_map = {
        ErrorType.VALIDATION_ERROR: 400,
        ErrorType.NOT_FOUND: 404,
        ErrorType.DATA_SERVICE_ERROR: 503,
        ErrorType.STRATEGY_ERROR: 400,
        ErrorType.INTERNAL_ERROR: 500
    }
    
    status_code = status_map.get(error.error_type, 500)
    raise HTTPException(status_code=status_code, detail=error.to_dict())


@api_router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    portfolio: PortfolioCreate,
    provider: DataProvider = DataProvider.YFINANCE
):
    """Create a new portfolio."""
    result = portfolio_service.create_portfolio(portfolio, provider)
    return handle_result(result, 201)


@api_router.get("/portfolios", response_model=List[PortfolioResponse])
async def list_portfolios():
    """List all portfolios."""
    result = portfolio_service.list_portfolios()
    return handle_result(result)


@api_router.get("/portfolios/{portfolio_name}", response_model=PortfolioResponse)
async def get_portfolio(portfolio_name: str):
    """Get a specific portfolio."""
    result = portfolio_service.get_portfolio(portfolio_name)
    return handle_result(result)


@api_router.post("/portfolios/{portfolio_name}/strategies/execute")
async def execute_strategy(
    portfolio_name: str,
    request: StrategyExecuteRequest
):
    """Execute a trading strategy on a portfolio."""
    result = portfolio_service.execute_strategy(portfolio_name, request)
    return handle_result(result)


@api_router.post("/portfolios/{portfolio_name}/backtests")
async def run_backtest(
    portfolio_name: str,
    request: BacktestRequest
):
    """Run a backtest on a portfolio."""
    result = portfolio_service.run_backtest(portfolio_name, request)
    return handle_result(result)


@api_router.get("/market-data")
async def get_market_data(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    provider: DataProvider = DataProvider.YFINANCE
):
    """Get current market data for symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol required")
    
    request = MarketDataRequest(symbols=symbol_list, provider=provider)
    result = portfolio_service.get_market_data(request)
    return handle_result(result)


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "portfolio-backend"}
