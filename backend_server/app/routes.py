"""
FastAPI routes with functional error handling using Result monad.
Clean, composable API design.
"""

from datetime import UTC as DATETIME_UTC
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from .core.result import ErrorType
from .schemas import (
    BacktestRequest,
    DataProvider,
    MarketDataRequest,
    PortfolioCreate,
    PortfolioResponse,
    StrategyExecuteRequest,
)
from .services import portfolio_service

# In accordance with the Architecture Plan, the backend is a thin orchestration
# layer over the portfolio_lib. For historical prices, we expose a dedicated
# endpoint that uses the configured DataService via DI and returns a stable,
# typed shape that mirrors the frontend's PricePoint.
try:
    from portfolio_lib.portfolio_lib.config import get_data_service
except Exception:
    get_data_service = None  # If portfolio_lib is not available, we will error on use

# Fallback data service if DI is unavailable: yfinance (from portfolio_lib)
try:
    from portfolio_lib.portfolio_lib.services.data.yfinance import (
        YFinanceDataService,  # type: ignore
    )
except Exception:
    YFinanceDataService = None  # type: ignore


# Local fallback using yfinance directly to ensure endpoint works without portfolio_lib
class LocalYFinanceFallback:
    def __init__(self) -> None:
        try:
            import yfinance as yf  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"yfinance not installed: {exc}")
        self.yf = yf

    def fetch_price_history(
        self, symbols: List[str], start_date: str, end_date: str
    ) -> Dict[str, Any]:
        import pandas as pd  # type: ignore

        out: Dict[str, Any] = {}
        start = start_date
        end = end_date

        # yfinance can fetch multiple symbols; however, handle one-by-one for simpler normalization
        for sym in symbols:
            try:
                df = self.yf.download(
                    sym,
                    start=start,
                    end=end,
                    progress=False,
                    auto_adjust=False,
                    group_by="column",
                )
                # Ensure DataFrame
                if isinstance(df, pd.DataFrame) and not df.empty:
                    out[sym] = df
                else:
                    out[sym] = pd.DataFrame()
            except Exception:
                out[sym] = self._empty_df()
        return out

    @staticmethod
    def _empty_df():
        try:
            import pandas as pd  # type: ignore

            return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        except Exception:
            return []  # last resort

    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        for sym in symbols:
            try:
                t = self.yf.Ticker(sym)
                info = t.fast_info if hasattr(t, "fast_info") else {}
                price = None
                if info:
                    price = (
                        info.get("last_price")
                        or info.get("last_trade")
                        or info.get("regular_market_price")
                    )
                if price is None:
                    hist = t.history(period="1d")
                    if not hist.empty:
                        price = float(hist["Close"].iloc[-1])
                if price is not None:
                    prices[sym] = float(price)
            except Exception:
                continue
        return prices

    def get_data_source_name(self) -> str:
        return "yfinance-local"


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
        ErrorType.INTERNAL_ERROR: 500,
    }

    status_code = status_map.get(error.error_type, 500)
    raise HTTPException(status_code=status_code, detail=error.to_dict())


@api_router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio(
    portfolio: PortfolioCreate, provider: DataProvider = DataProvider.YFINANCE
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
async def execute_strategy(portfolio_name: str, request: StrategyExecuteRequest):
    """Execute a trading strategy on a portfolio."""
    result = portfolio_service.execute_strategy(portfolio_name, request)
    return handle_result(result)


@api_router.post("/portfolios/{portfolio_name}/backtests")
async def run_backtest(portfolio_name: str, request: BacktestRequest):
    """Run a backtest on a portfolio."""
    result = portfolio_service.run_backtest(portfolio_name, request)
    return handle_result(result)


@api_router.get("/market-data")
async def get_market_data(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    provider: DataProvider = DataProvider.YFINANCE,
):
    """Get current market data for symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    request = MarketDataRequest(symbols=symbol_list, provider=provider)
    result = portfolio_service.get_market_data(request)
    return handle_result(result)


def _parse_date_param(label: str, v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").replace(tzinfo=DATETIME_UTC)
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"Invalid {label} format (expected YYYY-MM-DD): {v}"
        )


def _to_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            val = val.strip()
            if not val:
                return None
            return float(val)
        # pandas NA or numpy types handling
        try:
            import math

            if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
                return None
        except Exception:
            pass
        return float(val)
    except Exception:
        return None


def _to_int(val: Any) -> int:
    try:
        if val is None:
            return 0
        if isinstance(val, (int,)):
            return int(val)
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str):
            s = val.strip()
            if not s:
                return 0
            # Some APIs return volume as float string; cast through float first
            return int(float(s))
        return int(val)
    except Exception:
        return 0


@api_router.get("/market-data/history")
async def get_market_data_history(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    # Accept multiple aliases for compatibility
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    start_date: Optional[str] = Query(
        None, description="Alias for start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Alias for end date (YYYY-MM-DD)"
    ),
    provider: DataProvider = DataProvider.YFINANCE,
):
    """
    Historical price data endpoint:
    - Uses portfolio_lib DataService via DI when available
    - Falls back to YFinanceDataService if DI unavailable
    - As a last resort, uses a local yfinance-based fallback to ensure functionality
    - Normalizes various DataFrame/dict shapes into a stable PricePoint-like list per symbol

    Returns:
      { "AAPL": [ { "timestamp": "YYYY-MM-DD", "open": f, "high": f, "low": f, "close": f, "volume": i }, ... ], ... }
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol required")

    # Resolve dates, defaulting to the last 180 days ending today (UTC)
    start_s = start or start_date
    end_s = end or end_date
    end_dt = _parse_date_param("end", end_s) or datetime.now(DATETIME_UTC)
    start_dt = _parse_date_param("start", start_s) or (end_dt - timedelta(days=180))
    if start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start date must be <= end date")

    start_iso = start_dt.date().isoformat()
    end_iso = end_dt.date().isoformat()

    # Resolve data service via DI or fallback to portfolio_lib yfinance, then local yfinance
    ds = None
    if get_data_service is not None:
        try:
            prov_name: str = (
                provider.value if hasattr(provider, "value") else str(provider)
            )
            ds = get_data_service(prov_name)
        except Exception:
            ds = None

    if ds is None and YFinanceDataService is not None:
        try:
            ds = YFinanceDataService()  # type: ignore
        except Exception:
            ds = None

    if ds is None:
        try:
            ds = LocalYFinanceFallback()
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Data service configuration unavailable: {exc}"
            )

    # Fetch price history from provider; library contract: fetch_price_history(symbols, start, end)
    try:
        raw_history = ds.fetch_price_history(symbol_list, start_iso, end_iso)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Failed to fetch price history: {exc}"
        )

    # Normalize to PricePoint list per symbol, independent of provider's internal format.
    out: Dict[str, List[Dict[str, Any]]] = {}

    # Lazy import pandas to support DataFrame normalization if available
    try:
        import pandas as pd  # type: ignore

        has_pandas = True
    except Exception:
        pd = None  # type: ignore
        has_pandas = False

    def normalize_df_to_rows(sym: str, df_obj: Any) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not has_pandas:
            return rows
        try:
            if isinstance(df_obj, pd.Series):
                df = df_obj.to_frame()
            elif isinstance(df_obj, pd.DataFrame):
                df = df_obj
            else:
                return rows

            # Ensure index is datetime-like; if not, try to parse
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df = df.copy()
                    df.index = pd.to_datetime(df.index, errors="coerce")
                    df = df[df.index.notna()]
                except Exception:
                    pass

            # Handle MultiIndex columns: typical yfinance group_by='ticker'
            if isinstance(df.columns, pd.MultiIndex):
                # Try to select symbol level
                level_hit = None
                for lvl in range(df.columns.nlevels):
                    try:
                        candidates = {c[lvl] for c in df.columns}
                        if sym in candidates:
                            level_hit = lvl
                            break
                    except Exception:
                        continue
                if level_hit is not None:
                    try:
                        df = df.xs(sym, axis=1, level=level_hit, drop_level=True)
                    except Exception:
                        try:
                            tmp = df.copy()
                            tmp.columns = tmp.columns.swaplevel(0, level_hit)
                            df = tmp.xs(sym, axis=1, level=0, drop_level=True)
                        except Exception:
                            # if cannot slice, attempt to flatten and continue best-effort
                            pass

            # If still MultiIndex, flatten
            if isinstance(df.columns, pd.MultiIndex):
                df = df.copy()
                df.columns = [
                    "_".join([str(p) for p in tup if p is not None])
                    for tup in df.columns.to_list()
                ]

            # Build lowercase map
            cols_lower = {str(c).lower(): str(c) for c in df.columns}

            def col(*names):
                for n in names:
                    key = n.lower()
                    if key in cols_lower:
                        return cols_lower[key]
                # try partial contains for common alpha-vantage/yfinance columns
                for key, orig in cols_lower.items():
                    for n in names:
                        if n.lower() in key:
                            return orig
                return None

            c_open = col("open", "o", "1. open")
            c_high = col("high", "h", "2. high")
            c_low = col("low", "l", "3. low")
            c_close = col(
                "close", "c", "4. close", "adj close", "adj_close", "adjusted close"
            )
            if c_close is None:
                for alt in ["adj close", "adj_close", "adjusted close", "close"]:
                    alt_col = col(alt)
                    if alt_col:
                        c_close = alt_col
                        break
            c_volume = col("volume", "v", "6. volume")

            # Iterate rows safely
            for idx, row in df.iterrows():
                try:
                    ts = idx.date().isoformat() if hasattr(idx, "date") else str(idx)
                except Exception:
                    ts = str(idx)
                o = _to_float(row[c_open]) if c_open and c_open in row else None
                h = _to_float(row[c_high]) if c_high and c_high in row else None
                l = _to_float(row[c_low]) if c_low and c_low in row else None
                c = _to_float(row[c_close]) if c_close and c_close in row else None
                v = _to_int(row[c_volume]) if c_volume and c_volume in row else 0

                # require core OHLC fields
                if None in (o, h, l, c):
                    continue

                rows.append(
                    {
                        "timestamp": ts,
                        "open": o,
                        "high": h,
                        "low": l,
                        "close": c,
                        "volume": v,
                    }
                )

            rows.sort(key=lambda x: x["timestamp"])
        except Exception:
            # Keep API stable: return empty array for this symbol on failure
            return []
        return rows

    for sym in symbol_list:
        sym_rows: List[Dict[str, Any]] = []
        data: Any = None

        if isinstance(raw_history, dict):
            if sym in raw_history:
                data = raw_history[sym]
            else:
                for k in raw_history.keys():
                    try:
                        if str(k).upper() == sym:
                            data = raw_history[k]
                            break
                    except Exception:
                        continue

        if data is None:
            out[sym] = []
            continue

        # DataFrame path
        if has_pandas:
            sym_rows = normalize_df_to_rows(sym, data)

        # Fallbacks for non-DataFrame shapes
        if not sym_rows:
            try:
                # List of dicts
                if isinstance(data, list):
                    for row in data:
                        if not isinstance(row, dict):
                            continue
                        ts = row.get("timestamp") or row.get("date") or row.get("time")
                        if isinstance(ts, (datetime,)):
                            ts = ts.date().isoformat()
                        elif ts is not None:
                            ts = str(ts)
                        else:
                            continue
                        item = {
                            "timestamp": ts,
                            "open": _to_float(row.get("open") or row.get("o")),
                            "high": _to_float(row.get("high") or row.get("h")),
                            "low": _to_float(row.get("low") or row.get("l")),
                            "close": _to_float(
                                row.get("close") or row.get("c") or row.get("adj_close")
                            ),
                            "volume": _to_int(row.get("volume") or row.get("v")),
                        }
                        if item["close"] is None:
                            continue
                        for k in ("open", "high", "low"):
                            if item[k] is None:
                                item[k] = item["close"]
                        sym_rows.append(item)
                    sym_rows.sort(key=lambda x: x["timestamp"])
                # Dict keyed by date
                elif isinstance(data, dict):
                    for ts_k, row in data.items():
                        if not isinstance(row, dict):
                            continue
                        ts = ts_k
                        if isinstance(ts, (datetime,)):
                            ts = ts.date().isoformat()
                        else:
                            ts = str(ts)
                        item = {
                            "timestamp": ts,
                            "open": _to_float(row.get("open") or row.get("o")),
                            "high": _to_float(row.get("high") or row.get("h")),
                            "low": _to_float(row.get("low") or row.get("l")),
                            "close": _to_float(
                                row.get("close") or row.get("c") or row.get("adj_close")
                            ),
                            "volume": _to_int(row.get("volume") or row.get("v")),
                        }
                        if item["close"] is None:
                            continue
                        for k in ("open", "high", "low"):
                            if item[k] is None:
                                item[k] = item["close"]
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
