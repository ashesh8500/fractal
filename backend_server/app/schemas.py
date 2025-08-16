"""
Pydantic schemas for API request/response validation.
Lean, functional design with clear data flow.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PortfolioCreate(BaseModel):
    """Schema for creating a new portfolio."""
    name: str = Field(..., min_length=1, max_length=100)
    holdings: Dict[str, float] = Field(...)
    
    @field_validator('holdings')
    def validate_holdings(cls, v):
        for symbol, shares in v.items():
            if not symbol.strip():
                raise ValueError("Symbol cannot be empty")
            if shares <= 0:
                raise ValueError(f"Shares for {symbol} must be positive")
        return v


class RiskMetrics(BaseModel):
    """Schema for risk metrics."""
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0


class PerformanceMetrics(BaseModel):
    """Schema for performance metrics."""
    total_return: float = 0.0
    annualized_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0


class PortfolioResponse(BaseModel):
    """Schema for portfolio API responses."""
    name: str
    holdings: Dict[str, float]
    total_value: float
    current_weights: Dict[str, float]
    created_at: datetime
    risk_metrics: RiskMetrics
    performance_metrics: PerformanceMetrics
    data_provider: str = "yfinance"
    
    class Config:
        from_attributes = True


class PortfolioUpdate(BaseModel):
    """Schema for updating portfolio holdings."""
    holdings: Dict[str, float]
    
    @field_validator('holdings')
    def validate_holdings(cls, v):
        for symbol, shares in v.items():
            if not symbol.strip():
                raise ValueError("Symbol cannot be empty")
            if shares <= 0:
                raise ValueError(f"Shares for {symbol} must be positive")
        return v


class StrategyExecuteRequest(BaseModel):
    """Schema for strategy execution requests."""
    strategy_name: str = Field(..., pattern="^(momentum|bollinger)$")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rebalance_frequency: str = Field("monthly", pattern="^(daily|weekly|monthly|quarterly)$")
    risk_tolerance: float = Field(0.1, ge=0.0, le=1.0)
    max_position_size: float = Field(0.3, ge=0.1, le=1.0)


class TradeResponse(BaseModel):
    """Schema for trade recommendations."""
    symbol: str
    action: str
    quantity: float
    price: Optional[float]
    reason: Optional[str]


class StrategyResponse(BaseModel):
    """Schema for strategy execution results."""
    strategy_name: str
    timestamp: datetime
    trades: List[TradeResponse]
    new_weights: Dict[str, float]
    expected_return: float
    confidence: float


class BacktestRequest(BaseModel):
    """Schema for backtest requests."""
    strategy_name: str = Field(..., pattern="^(momentum|bollinger)$")
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(100000.0, gt=0)
    commission: float = Field(0.001, ge=0.0, le=0.1)
    slippage: float = Field(0.0005, ge=0.0, le=0.1)
    benchmark: str = Field("SPY")
    
    @model_validator(mode='after')
    def validate_date_range(self):
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")
        return self


class BacktestResponse(BaseModel):
    """Schema for backtest results."""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    benchmark_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int


# --------------------
# Dynamic Strategy (LLM-assisted) schemas
# --------------------

class StrategyCodeRequest(BaseModel):
    """Submit raw strategy source code for validation.

    Exactly one class inheriting BaseStrategy must be defined. The API will exec the code
    inside an isolated namespace (no external imports beyond portfolio_lib) and report the class name.
    """
    code: str
    class_name: Optional[str] = None


class StrategyValidationResponse(BaseModel):
    ok: bool
    message: str
    module: Optional[str] = None
    class_name: Optional[str] = None


class StrategyRegisterRequest(BaseModel):
    class_name: str
    code: str
    strategy_name: Optional[str] = None


class StrategyRegisterResponse(BaseModel):
    ok: bool
    module_path: Optional[str] = None
    class_name: Optional[str] = None
    message: Optional[str] = None


class StrategyListResponse(BaseModel):
    strategies: List[str]


class StrategySourceResponse(BaseModel):
    module: str
    source: str


class InlineBacktestRequest(BaseModel):
    code: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    commission: float = 0.0005
    slippage: float = 0.0002
    rebalance: str = Field("monthly", pattern="^(daily|weekly|monthly|quarterly)$")
    benchmark: str = "SPY"


class InlineBacktestResponse(BaseModel):
    ok: bool
    message: Optional[str] = None
    strategy_name: Optional[str] = None
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    total_trades: Optional[int] = None
    portfolio_values: Optional[List[float]] = None
    timestamps: Optional[List[str]] = None
    executed_trades: Optional[List[Dict[str, Any]]] = None
    daily_returns: Optional[List[float]] = None
    drawdowns: Optional[List[float]] = None
    benchmark_values: Optional[List[float]] = None
    holdings_history: Optional[List[Dict[str, float]]] = None
    rebalance_details: Optional[List[Dict[str, Any]]] = None
    allocation_weights: Optional[List[Dict[str, float]]] = None


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class DataProvider(str, Enum):
    """Available data providers."""
    YFINANCE = "yfinance"
    ALPHAVANTAGE = "alphavantage"


class MarketDataRequest(BaseModel):
    """Schema for market data requests."""
    symbols: List[str] = Field(...)
    provider: DataProvider = DataProvider.YFINANCE
    
    @field_validator('symbols')
    def validate_symbols(cls, v):
        for symbol in v:
            if not symbol.strip():
                raise ValueError("Symbols cannot be empty")
        return [s.upper().strip() for s in v]


class PriceData(BaseModel):
    """Schema for price data."""
    symbol: str
    current_price: Optional[float]
    change: Optional[float]
    change_percent: Optional[float]


class MarketDataResponse(BaseModel):
    """Schema for market data responses."""
    timestamp: datetime
    provider: str
    data: List[PriceData]


# --------------------
# User / Auth schemas
# --------------------
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    is_admin: bool = False

    @field_validator('username')
    def normalize_username(cls, v):
        return v.strip().lower()


class UserResponse(BaseModel):
    """Public user response (never includes password)."""
    username: str
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Fields that can be updated for a user."""
    password: Optional[str] = None
    is_admin: Optional[bool] = None


class LoginRequest(BaseModel):
    """Login payload."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response for successful login."""
    access_token: str
    token_type: str = "bearer"
    username: Optional[str] = None


class GoogleLoginRequest(BaseModel):
    """Request payload containing a Google ID token to be verified by the backend."""
    id_token: str


class TokenData(BaseModel):
    """Parsed token data (used internally)."""
    username: Optional[str] = None
    is_admin: Optional[bool] = False
