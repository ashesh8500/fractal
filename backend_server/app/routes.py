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

# Fallback data service if DI is unavailable: yfinance
try:
    from portfolio_lib.portfolio_lib.services.data.yfinance import YFinanceDataService  # type: ignore
except Exception:
    YFinanceDataService = None  # type: ignore


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
    # Accept multiple aliases for compatibility
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(None, description="Alias for start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Alias for end date (YYYY-MM-DD)"),
    provider: DataProvider = DataProvider.YFINANCE,
):
    """
    Historical price data endpoint:
    - Uses portfolio_lib DataService via DI when available
    - Falls back to YFinanceDataService if DI unavailable
    - Normalizes various DataFrame/dict shapes into a stable PricePoint-like list per symbol

    Returns:
      { "AAPL": [ { "timestamp": "YYYY-MM-DD", "open": f, "high": f, "low": f, "close": f, "volume": i }, ... ], ... }
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    # Resolve dates, defaulting to the last 180 days ending today
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

    # Resolve data service via DI or fallback to yfinance
    ds = None
    if get_data_service is not None:
        try:
            ds = get_data_service(provider.value if hasattr(provider, "value") else str(provider))
        except Exception:
            ds = None

    if ds is None:
        if YFinanceDataService is None:
            raise HTTPException(status_code=500, detail="Data service configuration unavailable")
        try:
            ds = YFinanceDataService()  # type: ignore
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to initialize fallback data service: {exc}")

    # Fetch price history from provider; library contract: fetch_price_history(symbols, start, end)
    try:
        raw_history = ds.fetch_price_history(symbol_list, start_iso, end_iso)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to fetch price history: {exc}")

    # Normalize to PricePoint list per symbol, independent of provider's internal format.
    out: Dict[str, List[Dict[str, Any]]] = {}

    # Lazy import pandas to support DataFrame normalization if available
    try:
        import pandas as pd  # type: ignore
        has_pandas = True
    except Exception:
        pd = None  # type: ignore
        has_pandas = False

    def normalize_df_to_rows(sym: str, df_obj) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not has_pandas:
            return rows
        try:
            if isinstance(df_obj, pd.DataFrame):
                df = df_obj

                # Handle MultiIndex columns: typical yfinance group_by='ticker'
                # Columns may look like: ('Open','AAPL'), ('High','AAPL'), ...
                if isinstance(df.columns, pd.MultiIndex):
                    # Try selecting the symbol level (second level often ticker)
                    # Normalize level order to (field, symbol)
                    level_names = list(df.columns.names) if df.columns.names else []
                    # Find which level is symbol by checking membership
                    sym_level = None
                    for lvl in range(df.columns.nlevels):
                        if sym in set([c[lvl] for c in df.columns]):
                            sym_level = lvl
                            break
                    if sym_level is not None:
                        try:
                            df = df.xs(sym, axis=1, level=sym_level, drop_level=False)
                        except Exception:
                            # alternative: swaplevel then xs
                            try:
                                df = df.copy()
                                df.columns = df.columns.swaplevel(0, sym_level)
                                df = df.xs(sym, axis=1, level=0, drop_level=True)
                            except Exception:
                                pass

                # After potential xs, columns might still be MultiIndex -> flatten best-effort
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ["_".join([str(p) for p in tup if p is not None]) for tup in df.columns.to_list()]

                cols_lower = {str(c).lower(): str(c) for c in df.columns}
                def col(*names):
                    for n in names:
                        l = n.lower()
                        if l in cols_lower:
                            return cols_lower[l]
                    return None

                c_open = col("open", "o", "1. open")
                c_high = col("high", "h", "2. high")
                c_low = col("low", "l", "3. low")
                c_close = col("close", "c", "4. close", "adj close", "adj_close", "adjusted close")
                c_volume = col("volume", "v", "6. volume")

                # If close missing but Adj Close present with different exact casing, try common variants
                if c_close is None:
                    for alt in ["adj close", "adj_close", "adjusted close"]:
                        if alt in cols_lower:
                            c_close = cols_lower[alt]
                            break

                # Iterate rows
                for idx, row in df.iterrows():
                    ts = str(idx.date()) if hasattr(idx, "date") else str(idx)
                    try:
                        item = {
                            "timestamp": ts,
                            "open": float(row[c_open]) if c_open else None,
                            "high": float(row[c_high]) if c_high else None,
                            "low": float(row[c_low]) if c_low else None,
                            "close": float(row[c_close]) if c_close else None,
                            "volume": int(row[c_volume]) if c_volume and not pd.isna(row[c_volume]) else 0,
                        }
                        # require core OHLC fields
                        if None in (item["open"], item["high"], item["low"], item["close"]):
                            continue
                        rows.append(item)
                    except Exception:
                        continue

                rows.sort(key=lambda x: x["timestamp"])
        except Exception:
            # On any failure, return empty rows to keep API stable per symbol
            return []
        return rows

    for sym, data in (raw_history or {}).items():
        sym_rows: List[Dict[str, Any]] = []

        if has_pandas:
            sym_rows = normalize_df_to_rows(sym, data)

        # Fallbacks for non-DataFrame shapes
        if not sym_rows:
            try:
                # List of dicts
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
                        # No strict OHLC check in dict path; include best-effort
                        sym_rows.append(item)
                    sym_rows.sort(key=lambda x: x["timestamp"])
                # Dict keyed by date
                elif isinstance(data, dict):
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
                        sym_rows.append(item)
                    sym_rows.sort(key=lambda x: x["timestamp"])
            except Exception:
                sym_rows = []

        out[sym] = sym_rows

    return out


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "portfolio-backend"}
