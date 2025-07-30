"""
Pydantic schemas for API request/response validation.
Lean, functional design with clear data flow.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class PortfolioCreate(BaseModel):
    """Schema for creating a new portfolio."""
    name: str = Field(..., min_length=1, max_length=100)
    holdings: Dict[str, float] = Field(..., min_items=1)
    
    @validator('holdings')
    def validate_holdings(cls, v):
        for symbol, shares in v.items():
            if not symbol.strip():
                raise ValueError("Symbol cannot be empty")
            if shares <= 0:
                raise ValueError(f"Shares for {symbol} must be positive")
        return v


class PortfolioResponse(BaseModel):
    """Schema for portfolio API responses."""
    name: str
    holdings: Dict[str, float]
    total_value: float
    current_weights: Dict[str, float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class StrategyExecuteRequest(BaseModel):
    """Schema for strategy execution requests."""
    strategy_name: str = Field(..., pattern="^(momentum)$")
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
    strategy_name: str = Field(..., pattern="^(momentum)$")
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(100000.0, gt=0)
    commission: float = Field(0.001, ge=0.0, le=0.1)
    slippage: float = Field(0.0005, ge=0.0, le=0.1)
    benchmark: str = Field("SPY")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError("End date must be after start date")
        return v


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
    symbols: List[str] = Field(..., min_items=1, max_items=20)
    provider: DataProvider = DataProvider.YFINANCE
    
    @validator('symbols')
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
