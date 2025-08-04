"""
FastAPI routes with functional error handling using Result monad.
Clean, composable API design.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .schemas import (
    PortfolioCreate, PortfolioResponse, StrategyExecuteRequest, 
    BacktestRequest, MarketDataRequest, DataProvider, ErrorResponse
)
from .services import portfolio_service
from .core.result import Result, AppError, ErrorType

# In accordance with the Architecture Plan, the backend is a thin orchestration
# layer over the portfolio_lib. For historical prices, we expose a dedicated
# endpoint that uses the configured DataService via DI and returns a stable,
# typed shape that mirrors the frontend's PricePoint.
try:
    from portfolio_lib.portfolio_lib.config import get_data_service
except Exception:
    get_data_service = None  # If portfolio_lib is not available, we will error on use


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


@api_router.get("/market-data/history")
async def get_market_data_history(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    # As per plan: accept multiple aliases to be resilient with clients
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Alias for start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Alias for end date (YYYY-MM-DD)"),
    provider: DataProvider = DataProvider.YFINANCE,
):
    """
    Historical price data endpoint aligned with the Architecture Plan:
    - Thin orchestration: leverages portfolio_lib DataService via DI.
    - Stable shape to align with frontend types (PricePoint).
    - Provider is pluggable via DataProvider enum.

    Returns:
      {
        "AAPL": [
          { "timestamp": "YYYY-MM-DD", "open": float, "high": float, "low": float, "close": float, "volume": int },
          ...
        ],
        "MSFT": [ ... ],
        ...
      }
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    # Resolve and validate dates
    # If not provided, default to a reasonable lookback window (e.g., 180 days ending today)
    def parse_date_str(label: str, v: Optional[str]) -> Optional[datetime]:
        if not v:
            return None
        try:
            return datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid {label} format (expected YYYY-MM-DD): {v}")

    start_s = start or start_date
    end_s = end or end_date

    end_dt = parse_date_str("end", end_s) or datetime.utcnow()
    start_dt = parse_date_str("start", start_s) or (end_dt - timedelta(days=180))

    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be <= end date")

    start_iso = start_dt.date().isoformat()
    end_iso = end_dt.date().isoformat()

    if get_data_service is None:
        raise HTTPException(status_code=500, detail="Data service configuration unavailable")

    # Obtain data service via DI (honors provider selection)
    try:
        ds = get_data_service(provider.value if hasattr(provider, "value") else str(provider))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to initialize data service: {exc}")

    # Fetch price history from provider; library contract: fetch_price_history(symbols, start, end)
    try:
        raw_history = ds.fetch_price_history(symbol_list, start_iso, end_iso)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch price history: {exc}")

    # Normalize to PricePoint list per symbol, independent of provider's internal format.
    # We expect either:
    #  - pandas.DataFrame with OHLCV columns, indexed by date
    #  - dict-like structure containing iterables of OHLCV items
    out: Dict[str, List[Dict[str, Any]]] = {}

    # Lazy import pandas to avoid hard dependency if provider returns pure dicts
    try:
        import pandas as pd  # type: ignore
        has_pandas = True
    except Exception:
        pd = None  # type: ignore
        has_pandas = False

    for sym, data in (raw_history or {}).items():
        out_list: List[Dict[str, Any]] = []

        # pandas DataFrame path
        if has_pandas:
            try:
                if isinstance(data, pd.DataFrame):
                    # Try common column name variants
                    cols = {c.lower(): c for c in data.columns}
                    def col(*names):
                        for n in names:
                            if n in cols:
                                return cols[n]
                        return None

                    c_open = col("open", "o", "1. open")
                    c_high = col("high", "h", "2. high")
                    c_low = col("low", "l", "3. low")
                    c_close = col("close", "c", "4. close", "adj close", "adj_close", "adjusted close")
                    c_volume = col("volume", "v", "6. volume")

                    # Iterate by row
                    for idx, row in data.iterrows():
                        # idx can be Timestamp or date string
                        if hasattr(idx, "strftime"):
                            ts = idx.strftime("%Y-%m-%d")
                        else:
                            # fallback for string-like index
                            ts = str(idx)
                        item = {
                            "timestamp": ts,
                            "open": float(row[c_open]) if c_open else None,
                            "high": float(row[c_high]) if c_high else None,
                            "low": float(row[c_low]) if c_low else None,
                            "close": float(row[c_close]) if c_close else None,
                            "volume": int(row[c_volume]) if c_volume else 0,
                        }
                        # Ensure required numeric fields exist; skip rows with missing critical data
                        if item["open"] is None or item["high"] is None or item["low"] is None or item["close"] is None:
                            continue
                        out_list.append(item)
                    # Sort ascending by timestamp (string YYYY-MM-DD sorts lexically correctly)
                    out_list.sort(key=lambda x: x["timestamp"])
                    out[sym] = out_list
                    continue
            except Exception:
                # fall through to dict-like path
                pass

        # Dict-like or list-like path
        try:
            # Common shapes:
            # { "timestamp": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ... }
            # or list of such dicts
            if isinstance(data, list):
                for row in data:
                    ts = row.get("timestamp") or row.get("date")
                    if not ts:
                        continue
                    item = {
                        "timestamp": ts,
                        "open": float(row.get("open", row.get("o", 0.0))),
                        "high": float(row.get("high", row.get("h", 0.0))),
                        "low": float(row.get("low", row.get("l", 0.0))),
                        "close": float(row.get("close", row.get("c", row.get("adj_close", 0.0)))),
                        "volume": int(row.get("volume", row.get("v", 0))),
                    }
                    out_list.append(item)
                out_list.sort(key=lambda x: x["timestamp"])
                out[sym] = out_list
                continue

            if isinstance(data, dict):
                # Potentially keyed by date: { "YYYY-MM-DD": {"open":..., ...}, ... }
                # or contains a nested "prices" array
                if "prices" in data and isinstance(data["prices"], list):
                    for row in data["prices"]:
                        ts = row.get("timestamp") or row.get("date")
                        if not ts:
                            continue
                        item = {
                            "timestamp": ts,
                            "open": float(row.get("open", row.get("o", 0.0))),
                            "high": float(row.get("high", row.get("h", 0.0))),
                            "low": float(row.get("low", row.get("l", 0.0))),
                            "close": float(row.get("close", row.get("c", row.get("adj_close", 0.0)))),
                            "volume": int(row.get("volume", row.get("v", 0))),
                        }
                        out_list.append(item)
                    out_list.sort(key=lambda x: x["timestamp"])
                    out[sym] = out_list
                    continue

                # Keyed by date map
                if all(isinstance(k, str) for k in data.keys()):
                    for ts, row in data.items():
                        if not isinstance(row, dict):
                            continue
                        item = {
                            "timestamp": ts,
                            "open": float(row.get("open", row.get("o", 0.0))),
                            "high": float(row.get("high", row.get("h", 0.0))),
                            "low": float(row.get("low", row.get("l", 0.0))),
                            "close": float(row.get("close", row.get("c", row.get("adj_close", 0.0)))),
                            "volume": int(row.get("volume", row.get("v", 0))),
                        }
                        out_list.append(item)
                    out_list.sort(key=lambda x: x["timestamp"])
                    out[sym] = out_list
                    continue
        except Exception:
            # If normalization fails, return a 500 with a clear message for debugging
            raise HTTPException(status_code=500, detail=f"Failed to normalize history for symbol {sym}")

        # If we couldn't parse this symbol at all, return empty list to keep schema stable
        out[sym] = out_list

    return out


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "portfolio-backend"}
