//! Type definitions for portfolio data structures

use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RiskMetrics {
    pub volatility: f64,
    pub sharpe_ratio: f64,
    pub max_drawdown: f64,
    pub var_95: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PerformanceMetrics {
    pub total_return: f64,
    pub annualized_return: f64,
    pub alpha: f64,
    pub beta: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PricePoint {
    pub timestamp: DateTime<Utc>,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
}

/// Enhanced OHLCV bar with additional computed fields
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OhlcvBar {
    pub timestamp: DateTime<Utc>,
    pub open: f64,
    pub high: f64,
    pub low: f64,
    pub close: f64,
    pub volume: u64,
    pub adj_close: Option<f64>,
    pub typical_price: f64,  // (H + L + C) / 3
    pub price_change: f64,   // Close - Open
    pub price_change_pct: f64, // (Close - Open) / Open * 100
}

impl From<PricePoint> for OhlcvBar {
    fn from(point: PricePoint) -> Self {
        let typical_price = (point.high + point.low + point.close) / 3.0;
        let price_change = point.close - point.open;
        let price_change_pct = if point.open != 0.0 {
            (price_change / point.open) * 100.0
        } else {
            0.0
        };
        
        Self {
            timestamp: point.timestamp,
            open: point.open,
            high: point.high,
            low: point.low,
            close: point.close,
            volume: point.volume,
            adj_close: None,
            typical_price,
            price_change,
            price_change_pct,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BacktestResult {
    pub strategy_name: String,
    pub period: DateRange,
    pub performance: PerformanceMetrics,
    pub benchmark_performance: Option<PerformanceMetrics>,
    pub trades_executed: u32,
    pub final_portfolio_value: f64,
    pub equity_curve: Vec<EquityPoint>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub benchmark_curve: Option<Vec<EquityPoint>>, // optional benchmark equity curve for overlay
    #[serde(skip_serializing_if = "Option::is_none")]
    pub weights_over_time: Option<Vec<WeightsAtTime>>, // allocation snapshots per rebalance
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DateRange {
    pub start_date: DateTime<Utc>,
    pub end_date: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EquityPoint {
    pub date: DateTime<Utc>,
    pub value: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeightsAtTime {
    pub timestamp: DateTime<Utc>,
    pub weights: HashMap<String, f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategySignals {
    pub strategy_name: String,
    pub signals: HashMap<String, Signal>,
    pub last_updated: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Signal {
    pub symbol: String,
    pub signal_type: SignalType,
    pub strength: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SignalType {
    Buy,
    Sell,
    Hold,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataStatus {
    pub is_loading: bool,
    pub last_error: Option<String>,
    pub data_freshness: HashMap<String, DateTime<Utc>>,
    pub provider_status: ProviderStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ProviderStatus {
    Connected,
    Disconnected,
    RateLimited,
    Error(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Trade {
    pub symbol: String,
    pub action: TradeAction,
    pub shares: f64,
    pub price: f64,
    pub total_value: f64,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TradeAction {
    Buy,
    Sell,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TradeExecution {
    pub symbol: String,
    pub action: String, // "buy" | "sell"
    pub quantity_shares: f64,
    pub weight_fraction: f64,
    pub price: f64,
    pub gross_value: f64,
    pub commission: f64,
    pub slippage: f64,
    pub total_cost: f64,
    pub net_cash_delta: f64,
    pub timestamp: DateTime<Utc>,
    pub reason: Option<String>,
}
