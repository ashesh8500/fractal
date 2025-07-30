//! Portfolio data models and types
//! 
//! This module contains the core Portfolio struct that serves as the central
//! data holder for all UI components. It mirrors the Python backend models
//! and provides a unified interface for accessing portfolio data, metrics,
//! backtest results, and strategy signals.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};

pub mod types;

pub use types::*;

/// Central Portfolio data structure that holds all state for UI components
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Portfolio {
    pub name: String,
    pub holdings: HashMap<String, f64>,
    pub total_value: f64,
    pub current_weights: HashMap<String, f64>,
    pub risk_metrics: RiskMetrics,
    pub performance_metrics: PerformanceMetrics,
    pub data_provider: String,
    pub last_updated: DateTime<Utc>,
    
    // Extended state for UI components
    #[serde(skip_serializing_if = "Option::is_none")]
    pub price_history: Option<HashMap<String, Vec<PricePoint>>>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub backtest_results: Option<BacktestResult>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub strategy_signals: Option<StrategySignals>,
    
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data_status: Option<DataStatus>,
}

impl Portfolio {
    /// Create a new empty portfolio
    pub fn new(name: String) -> Self {
        Self {
            name,
            holdings: HashMap::new(),
            total_value: 0.0,
            current_weights: HashMap::new(),
            risk_metrics: RiskMetrics::default(),
            performance_metrics: PerformanceMetrics::default(),
            data_provider: "yfinance".to_string(),
            last_updated: Utc::now(),
            price_history: None,
            backtest_results: None,
            strategy_signals: None,
            data_status: None,
        }
    }
    
    /// Get symbols in the portfolio
    pub fn symbols(&self) -> Vec<String> {
        self.holdings.keys().cloned().collect()
    }
    
    /// Check if portfolio has valid data
    pub fn has_data(&self) -> bool {
        !self.holdings.is_empty() && self.total_value > 0.0
    }
    
    /// Get position value for a symbol
    pub fn get_position_value(&self, symbol: &str) -> Option<f64> {
        self.holdings.get(symbol)
            .and_then(|shares| {
                self.current_weights.get(symbol)
                    .map(|weight| self.total_value * weight)
            })
    }
}
