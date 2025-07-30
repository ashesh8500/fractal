//! API client for communicating with the portfolio backend

use crate::portfolio::Portfolio;
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;

#[derive(Clone)]
pub struct ApiClient {
    client: Client,
    base_url: String,
}

impl ApiClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            client: Client::new(),
            base_url: base_url.to_string(),
        }
    }
    
    /// Test backend health
    pub async fn test_health(&self) -> Result<(), ApiError> {
        let url = format!("{}/health", self.base_url);
        let response = self.client.get(&url).send().await?;
        
        if response.status().is_success() {
            Ok(())
        } else {
            Err(ApiError::Backend(format!("Health check failed with status: {}", response.status())))
        }
    }
    
    /// Get all portfolios from the backend
    pub async fn get_portfolios(&self) -> Result<Vec<Portfolio>, ApiError> {
        let url = format!("{}/portfolios", self.base_url);
        let response = self.client.get(&url).send().await?;
        
        if response.status().is_success() {
            let portfolios: Vec<Portfolio> = response.json().await?;
            Ok(portfolios)
        } else {
            let error: Value = response.json().await?;
            Err(ApiError::Backend(error.to_string()))
        }
    }
    
    /// Get a specific portfolio
    pub async fn get_portfolio(&self, name: &str) -> Result<Portfolio, ApiError> {
        let url = format!("{}/portfolios/{}", self.base_url, name);
        let response = self.client.get(&url).send().await?;
        
        if response.status().is_success() {
            let portfolio: Portfolio = response.json().await?;
            Ok(portfolio)
        } else {
            let error: Value = response.json().await?;
            Err(ApiError::Backend(error.to_string()))
        }
    }
    
    /// Create a new portfolio
    pub async fn create_portfolio(&self, name: &str, holdings: HashMap<String, f64>) -> Result<Portfolio, ApiError> {
        let url = format!("{}/portfolios", self.base_url);
        let payload = serde_json::json!({
            "name": name,
            "holdings": holdings
        });
        
        let response = self.client.post(&url)
            .json(&payload)
            .send()
            .await?;
        
        if response.status().is_success() {
            let portfolio: Portfolio = response.json().await?;
            Ok(portfolio)
        } else {
            let error: Value = response.json().await?;
            Err(ApiError::Backend(error.to_string()))
        }
    }
    
    /// Get current market data
    pub async fn get_market_data(&self, symbols: &[String]) -> Result<HashMap<String, f64>, ApiError> {
        let symbols_str = symbols.join(",");
        let url = format!("{}/market-data?symbols={}", self.base_url, symbols_str);
        let response = self.client.get(&url).send().await?;
        
        if response.status().is_success() {
            let data: HashMap<String, f64> = response.json().await?;
            Ok(data)
        } else {
            let error: Value = response.json().await?;
            Err(ApiError::Backend(error.to_string()))
        }
    }
}

#[derive(Debug)]
pub enum ApiError {
    Network(reqwest::Error),
    Backend(String),
    Serialization(serde_json::Error),
}

impl From<reqwest::Error> for ApiError {
    fn from(err: reqwest::Error) -> Self {
        ApiError::Network(err)
    }
}

impl From<serde_json::Error> for ApiError {
    fn from(err: serde_json::Error) -> Self {
        ApiError::Serialization(err)
    }
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ApiError::Network(e) => write!(f, "Network error: {}", e),
            ApiError::Backend(e) => write!(f, "Backend error: {}", e),
            ApiError::Serialization(e) => write!(f, "Serialization error: {}", e),
        }
    }
}

impl std::error::Error for ApiError {}
