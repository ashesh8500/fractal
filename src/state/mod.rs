#![allow(elided_lifetimes_in_paths)]
//! Application state management
//! 
//! Centralized state management with Portfolio as the primary data holder.
//! Follows functional programming principles with immutable updates.

use crate::portfolio::Portfolio;
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppState {
    pub portfolios: Option<HashMap<String, Portfolio>>,
    pub config: Config,
    pub ui_state: UiState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub api_base_url: String,
    pub default_data_provider: String,
    pub refresh_interval_seconds: u64,
    pub chart_theme: ChartTheme,
    // Native provider support
    pub use_native_provider: bool,
    pub alphavantage_api_key: Option<String>,

    // Persisted authentication token (JWT) and current user
    pub auth_token: Option<String>,
    pub current_user: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UiState {
    pub selected_portfolio: Option<String>,
    pub component_states: HashMap<String, bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ChartTheme {
    Light,
    Dark,
    Auto,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            portfolios: None,
            config: Config::default(),
            ui_state: UiState::default(),
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            api_base_url: "http://localhost:8000/api/v1".to_string(),
            default_data_provider: "yfinance".to_string(),
            refresh_interval_seconds: 300, // 5 minutes
            chart_theme: ChartTheme::Auto,
            // Defaults for native mode (enabled for testing)
            use_native_provider: false,
            alphavantage_api_key: std::env::var("ALPHAVANTAGE_API_KEY").ok(),
            // Auth defaults
            auth_token: None,
            current_user: None,
        }
    }
}

impl Default for UiState {
    fn default() -> Self {
        Self {
            selected_portfolio: None,
            component_states: HashMap::new(),
        }
    }
}

impl AppState {
    /// Get a portfolio by name
    pub fn get_portfolio(&self, name: &str) -> Option<&Portfolio> {
        self.portfolios.as_ref()?.get(name)
    }
    
    /// Add or update a portfolio
    pub fn set_portfolio(&mut self, portfolio: Portfolio) {
        if self.portfolios.is_none() {
            self.portfolios = Some(HashMap::new());
        }
        
        if let Some(portfolios) = &mut self.portfolios {
            portfolios.insert(portfolio.name.clone(), portfolio);
        }
    }
    
    /// Remove a portfolio
    pub fn remove_portfolio(&mut self, name: &str) -> Option<Portfolio> {
        self.portfolios.as_mut()?.remove(name)
    }
    
    /// Get all portfolio names
    pub fn portfolio_names(&self) -> Vec<String> {
        self.portfolios
            .as_ref()
            .map(|p| p.keys().cloned().collect())
            .unwrap_or_default()
    }
    
    /// Check if any portfolios are loaded
    pub fn has_portfolios(&self) -> bool {
        self.portfolios
            .as_ref()
            .map(|p| !p.is_empty())
            .unwrap_or(false)
    }

}
