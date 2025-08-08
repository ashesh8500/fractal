"""
FastAPI routes with functional error handling using Result monad.
Clean, composable API design.
"""

from datetime import UTC as DATETIME_UTC
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import os
import secrets
import hashlib
import base64
import time

from fastapi import APIRouter, HTTPException, Query, Header, status, Depends

from .core.result import ErrorType
from .schemas import (
    BacktestRequest,
    DataProvider,
    MarketDataRequest,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioResponse,
    StrategyExecuteRequest,
    # auth schemas
    UserCreate,
    UserResponse,
    UserUpdate,
    LoginRequest,
    LoginResponse,
    TokenData,
    GoogleLoginRequest,
)
from .services import portfolio_service

# Storage helpers for user persistence
from .storage import (
    list_users_public,
    create_user as storage_create_user,
    get_user_internal,
    get_user_public,
    update_user as storage_update_user,
    delete_user as storage_delete_user,
)

# Password hashing and JWT
try:
    from passlib.context import CryptContext
except Exception:
    CryptContext = None

try:
    from jose import jwt, JWTError
except Exception:
    jwt = None
    JWTError = Exception

# Google ID token verification (optional, used if available)
try:
    from google.oauth2 import id_token as google_id_token  # type: ignore
    from google.auth.transport import requests as google_requests  # type: ignore
except Exception:
    google_id_token = None  # type: ignore
    google_requests = None  # type: ignore

# Simple in-memory store for OAuth login sessions: state -> { verifier, done, token?, username? }
_OAUTH_SESSIONS: Dict[str, Dict[str, Any]] = {}

# Config for JWT
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

def _init_pwd_context():
    if CryptContext is None:
        return None
    try:
        return CryptContext(schemes=["bcrypt"], deprecated="auto")
    except Exception:
        # Fallback: disable hashing if bcrypt backend is broken in local env
        return None

pwd_context = _init_pwd_context()

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


# -----------------------
# Auth helpers (JWT)
# -----------------------
def _verify_password(plain: str, hashed: str) -> bool:
    if pwd_context is not None:
        try:
            return pwd_context.verify(plain, hashed)
        except Exception:
            return False
    # Fallback (insecure): direct compare
    return plain == hashed


def _get_password_hash(password: str) -> str:
    if pwd_context is not None:
        return pwd_context.hash(password)
    # Fallback (insecure): store plaintext (NOT RECOMMENDED for production)
    return password


def _create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT if jose is available, otherwise return a simple token."""
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": int(expire.timestamp())})
    if jwt is not None:
        try:
            return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        except Exception:
            pass
    # Fallback token format (unsigned) -- useful for local demo
    return f"demo-token:{to_encode.get('username','')}:admin={to_encode.get('is_admin', False)}:exp={int(expire.timestamp())}"


def _decode_access_token(token: str) -> TokenData:
    """Decode access token and return TokenData.
    Order of attempts:
      1) Verify as Google ID token if google-auth is installed (preferred minimal OAuth path)
      2) Verify as local JWT signed with SECRET_KEY (legacy)
      3) Fallback to demo-token parsing (local/dev only)
    """
    # 1) Google ID token path
    if google_id_token is not None and google_requests is not None:
        try:
            request = google_requests.Request()
            audience = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
            payload = google_id_token.verify_oauth2_token(token, request, audience)
            # Extract email as username
            username = payload.get("email") or payload.get("sub")
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token payload")
            # Minimal: no admin concept with Google OAuth
            return TokenData(username=username, is_admin=False)
        except Exception:
            # fall through to other methods
            pass

    # 2) Legacy local JWT
    if jwt is not None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username = payload.get("username")
            is_admin = payload.get("is_admin", False)
            return TokenData(username=username, is_admin=is_admin)
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token decode error")
    # Fallback parsing for demo-token format
    try:
        if token.startswith("demo-token:"):
            parts = token.split(":")
            username = parts[1] if len(parts) > 1 else None
            is_admin = "admin=True" in token or "admin=true" in token.lower()
            return TokenData(username=username, is_admin=is_admin)
    except Exception:
        pass
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _get_token_from_header(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")


async def get_current_token_data(authorization: Optional[str] = Header(None)) -> TokenData:
    token = _get_token_from_header(authorization)
    return _decode_access_token(token)


def require_admin(token_data: TokenData):
    if not token_data.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")


def require_same_user_or_admin(target_username: str, token_data: TokenData):
    if token_data.username != target_username and not token_data.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


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


# -----------------------
# User management endpoints
# -----------------------
@api_router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, authorization: Optional[str] = Header(None)):
    """
    Create a new user. If no users exist yet, allow creation of the first user (bootstrap).
    Otherwise the caller must be an admin (provide Bearer token).
    Password is hashed before storage.
    """
    # Normalize username
    username = user.username.strip().lower()

    # Check if any users exist - bootstrap logic
    existing = list_users_public()
    if existing:
        # Require admin
        token_data = await get_current_token_data(authorization)
        require_admin(token_data)

    try:
        password_hash = _get_password_hash(user.password)
        created = storage_create_user(username, password_hash, is_admin=user.is_admin)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {exc}")

    return created


@api_router.get("/users", response_model=List[UserResponse])
async def list_users(token_data: TokenData = Depends(get_current_token_data)):
    """List all users (admin only)."""
    require_admin(token_data)
    rows = list_users_public()
    return rows


@api_router.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, token_data: TokenData = Depends(get_current_token_data)):
    """Get public user info. Allowed for same user or admin."""
    require_same_user_or_admin(username, token_data)
    public = get_user_public(username)
    if public is None:
        raise HTTPException(status_code=404, detail="User not found")
    return public


@api_router.put("/users/{username}", response_model=UserResponse)
async def update_user(username: str, payload: UserUpdate, token_data: TokenData = Depends(get_current_token_data)):
    """Update user password or admin flag. Only same user or admin may update."""
    require_same_user_or_admin(username, token_data)

    password_hash = None
    if payload.password:
        password_hash = _get_password_hash(payload.password)

    try:
        updated = storage_update_user(username, password_hash=password_hash, is_admin=payload.is_admin)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {exc}")

    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return updated


@api_router.delete("/users/{username}")
async def delete_user(username: str, token_data: TokenData = Depends(get_current_token_data)):
    """Delete a user. Admins can delete any user; users can delete their own account."""
    require_same_user_or_admin(username, token_data)
    ok = storage_delete_user(username)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "deleted", "username": username}


# -----------------------
# Authentication endpoints
# -----------------------
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(creds: LoginRequest):
    """Authenticate and return an access token (JWT)."""
    username = creds.username.strip().lower()
    internal = get_user_internal(username)
    if internal is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    stored_hash = internal.get("password_hash")
    if not _verify_password(creds.password, str(stored_hash)):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {"username": username, "is_admin": bool(internal.get("is_admin", False))}
    access_token = _create_access_token(token_data)
    return {"access_token": access_token, "token_type": "bearer", "username": username}


@api_router.post("/auth/google", response_model=LoginResponse)
async def login_with_google(payload: GoogleLoginRequest):
    """Accept a Google ID token, verify it server-side, and return a bearer token.
    If google-auth isn't installed, this will return 501.
    """
    if google_id_token is None or google_requests is None:
        raise HTTPException(status_code=501, detail="Google auth not available on server")

    try:
        req = google_requests.Request()
        audience = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
        info = google_id_token.verify_oauth2_token(payload.id_token, req, audience)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Google ID token: {exc}")

    username = (info.get("email") or info.get("sub") or "").strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Google token missing email/sub")

    # Upsert a user record for visibility; password is irrelevant with OAuth.
    # If user doesn't exist, create with a random placeholder hash.
    internal = get_user_internal(username)
    if internal is None:
        try:
            placeholder = _get_password_hash(os.urandom(16).hex())
            storage_create_user(username, placeholder, is_admin=False)
        except Exception:
            # best-effort; continue even if user table is unavailable
            pass

    # Return a local access token that encodes username (and non-admin).
    access_token = _create_access_token({"username": username, "is_admin": False})
    return {"access_token": access_token, "token_type": "bearer", "username": username}


# -----------------------
# Google OAuth (Auth Code + PKCE) flow for native app redirect
# -----------------------
@api_router.post("/auth/google/start")
async def google_oauth_start():
    """Start Google OAuth Authorization Code with PKCE. Returns the URL and state.
    Frontend should open this URL in the user's browser and then poll /auth/google/status.
    """
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/auth/google/callback")
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_OAUTH_CLIENT_ID not configured")
    if not client_secret:
        # For PKCE, confidential client is still commonly used in server; warn if missing
        pass

    # Create state and PKCE verifier/challenge
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    # Store session (expires in 10 minutes)
    _OAUTH_SESSIONS[state] = {
        "verifier": verifier,
        "created": int(time.time()),
        "done": False,
    }

    scope = "openid email profile"
    enc_redirect = auth_urlencode(redirect_uri)
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={enc_redirect}"
        "&response_type=code"
        f"&scope={auth_urlencode(scope)}"
        "&access_type=offline"
        "&include_granted_scopes=true"
        f"&state={state}"
        "&prompt=consent"
        f"&code_challenge={challenge}"
        "&code_challenge_method=S256"
    )

    return {"auth_url": auth_url, "state": state}


def auth_urlencode(s: str) -> str:
    try:
        from urllib.parse import quote_plus

        return quote_plus(s)
    except Exception:
        return s.replace(" ", "+")


@api_router.get("/auth/google/callback")
async def google_oauth_callback(code: str, state: str):
    """Google redirects here after login. Exchange code for tokens, create app token, mark session done."""
    sess = _OAUTH_SESSIONS.get(state)
    if not sess:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Basic expiry (10 min)
    if int(time.time()) - int(sess.get("created", 0)) > 600:
        _OAUTH_SESSIONS.pop(state, None)
        raise HTTPException(status_code=400, detail="Login session expired")

    verifier = sess.get("verifier")
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/api/v1/auth/google/callback")

    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_OAUTH_CLIENT_ID not configured")

    # Exchange code -> tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    if client_secret:
        data["client_secret"] = client_secret

    try:
        import requests  # type: ignore

        resp = requests.post(token_url, data=data, timeout=10)
        if not resp.ok:
            detail = resp.text
            raise HTTPException(status_code=401, detail=f"Token exchange failed: {detail}")
        payload = resp.json()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Token exchange error: {exc}")

    id_tok = payload.get("id_token")
    if not id_tok:
        raise HTTPException(status_code=401, detail="No id_token returned")

    # Verify id token
    username = None
    if google_id_token is not None and google_requests is not None:
        try:
            req = google_requests.Request()
            info = google_id_token.verify_oauth2_token(id_tok, req, client_id)
            username = (info.get("email") or info.get("sub") or "").strip().lower()
        except Exception:
            pass
    if not username:
        # Fallback best-effort: accept token but don't verify (dev only)
        username = "user"

    # Upsert user and create app access token
    internal = get_user_internal(username)
    if internal is None:
        try:
            placeholder = _get_password_hash(os.urandom(16).hex())
            storage_create_user(username, placeholder, is_admin=False)
        except Exception:
            pass

    access_token = _create_access_token({"username": username, "is_admin": False})
    sess.update({"done": True, "access_token": access_token, "username": username})
    _OAUTH_SESSIONS[state] = sess

    # Return a simple HTML page to let user close the browser
    return (
        "<html><body><h3>Login successful. You can return to the app.</h3>"
        "<p>You may close this window now.</p></body></html>"
    )


@api_router.get("/auth/google/status", response_model=LoginResponse, responses={202: {"description": "Pending"}})
async def google_oauth_status(state: str):
    sess = _OAUTH_SESSIONS.get(state)
    if not sess:
        raise HTTPException(status_code=404, detail="Invalid state")
    if not sess.get("done"):
        # Pending
        raise HTTPException(status_code=202, detail="Pending")
    return {
        "access_token": sess.get("access_token"),
        "token_type": "bearer",
        "username": sess.get("username"),
    }


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


@api_router.put("/portfolios/{portfolio_name}", response_model=PortfolioResponse)
async def update_portfolio(portfolio_name: str, payload: PortfolioUpdate):
    """Update a portfolio's holdings."""
    result = portfolio_service.update_portfolio(portfolio_name, payload.holdings)
    return handle_result(result)


@api_router.delete("/portfolios/{portfolio_name}")
async def delete_portfolio(portfolio_name: str):
    """Delete a portfolio."""
    result = portfolio_service.delete_portfolio(portfolio_name)
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
