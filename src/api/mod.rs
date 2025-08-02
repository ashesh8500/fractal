 //! API client for communicating with the portfolio backend
 //! and/or directly with external data providers (native mode).

use crate::portfolio::{Portfolio, PricePoint};
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;
use thiserror::Error;

#[derive(Clone)]
pub struct ApiClient {
    client: Client,
    base_url: String,
    // Local/native mode:
    use_native_provider: bool,
    alphavantage_api_key: Option<String>,
}

impl ApiClient {
    pub fn new(base_url: &str) -> Self {
        Self {
            client: Client::new(),
            base_url: base_url.to_string(),
            use_native_provider: false,
            alphavantage_api_key: None,
        }
    }

    /// Enable or disable native provider mode and set optional Alpha Vantage API key
    pub fn with_native(mut self, use_native: bool, alphavantage_api_key: Option<String>) -> Self {
        self.use_native_provider = use_native;
        self.alphavantage_api_key = alphavantage_api_key;
        self
    }
    
    /// Test backend health (noop in native mode)
    pub async fn test_health(&self) -> Result<(), ApiError> {
        if self.use_native_provider {
            // Simple local check
            Ok(())
        } else {
            let url = format!("{}/health", self.base_url);
            let response = self.client.get(&url).send().await?;
            if response.status().is_success() {
                Ok(())
            } else {
                Err(ApiError::Backend(format!(
                    "Health check failed with status: {}",
                    response.status()
                )))
            }
        }
    }
    
    /// Get all portfolios from the backend (native mode returns empty list placeholder)
    pub async fn get_portfolios(&self) -> Result<Vec<Portfolio>, ApiError> {
        if self.use_native_provider {
            Ok(Vec::new())
        } else {
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
    }
    
    /// Get a specific portfolio
    pub async fn get_portfolio(&self, name: &str) -> Result<Portfolio, ApiError> {
        if self.use_native_provider {
            Err(ApiError::Unsupported(
                "Fetching portfolio by name is backend-only in this prototype".into(),
            ))
        } else {
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
    }
    
    /// Create a new portfolio
    pub async fn create_portfolio(&self, name: &str, holdings: HashMap<String, f64>) -> Result<Portfolio, ApiError> {
        if self.use_native_provider {
            // Create a minimal local portfolio
            let mut p = Portfolio::new(name.to_string());
            p.holdings = holdings;
            p.total_value = 0.0;
            Ok(p)
        } else {
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
    }
    
    /// Get current market data
    pub async fn get_market_data(&self, symbols: &[String]) -> Result<HashMap<String, f64>, ApiError> {
        if self.use_native_provider {
            self.alpha_vantage_current_prices(symbols).await
        } else {
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
    
    /// Get historic price data for symbols
    pub async fn get_historic_prices(&self, symbols: &[String], start_date: &str, end_date: &str) -> Result<HashMap<String, Vec<PricePoint>>, ApiError> {
        if self.use_native_provider {
            self.alpha_vantage_price_history(symbols, start_date, end_date).await
        } else {
            let symbols_str = symbols.join(",");
            let url = format!("{}/market-data/history?symbols={}&start_date={}&end_date={}", self.base_url, symbols_str, start_date, end_date);
            let response = self.client.get(&url).send().await?;
            
            if response.status().is_success() {
                let data: HashMap<String, Vec<PricePoint>> = response.json().await?;
                Ok(data)
            } else {
                let error: Value = response.json().await?;
                Err(ApiError::Backend(error.to_string()))
            }
        }
    }

    // ------------ Native provider (Alpha Vantage) ------------
    async fn alpha_vantage_current_prices(&self, symbols: &[String]) -> Result<HashMap<String, f64>, ApiError> {
        let key = self
            .alphavantage_api_key
            .as_ref()
            .ok_or_else(|| ApiError::Config("Alpha Vantage API key not set".into()))?;
        if symbols.is_empty() {
            return Ok(HashMap::new());
        }

        let mut out = HashMap::new();
        for symbol in symbols {
            let url = format!(
                "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={}&apikey={}",
                urlencoding::encode(symbol),
                key
            );
            let resp = self.client.get(&url).send().await?;
            if !resp.status().is_success() {
                return Err(ApiError::Backend(format!(
                    "Alpha Vantage price request failed: {}",
                    resp.status()
                )));
            }
            let v: Value = resp.json().await?;
            // Parse: { "Global Quote": { "05. price": "123.45", ... } }
            let price = v
                .get("Global Quote")
                .and_then(|g| g.get("05. price"))
                .and_then(|p| p.as_str())
                .and_then(|s| s.parse::<f64>().ok())
                .ok_or_else(|| ApiError::Parsing("Missing price in Alpha Vantage response".into()))?;
            out.insert(symbol.clone(), price);
        }
        Ok(out)
    }

    async fn alpha_vantage_price_history(
        &self,
        symbols: &[String],
        _start_date: &str,
        _end_date: &str,
    ) -> Result<HashMap<String, Vec<PricePoint>>, ApiError> {
        let key = self
            .alphavantage_api_key
            .as_ref()
            .ok_or_else(|| ApiError::Config("Alpha Vantage API key not set".into()))?;
        let mut result = HashMap::new();

        for symbol in symbols {
            // Use TIME_SERIES_DAILY_ADJUSTED as a practical default
            let url = format!(
                "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={}&outputsize=compact&apikey={}",
                urlencoding::encode(symbol),
                key
            );
            let resp = self.client.get(&url).send().await?;
            if !resp.status().is_success() {
                return Err(ApiError::Backend(format!(
                    "Alpha Vantage history request failed: {}",
                    resp.status()
                )));
            }
            let v: Value = resp.json().await?;

            // Response has "Time Series (Daily)": { "YYYY-MM-DD": { "1. open": "...", ... }, ... }
            let Some(ts) = v.get("Time Series (Daily)") else {
                // Error messages might be at "Note" or "Error Message"
                if let Some(note) = v.get("Note").and_then(|n| n.as_str()) {
                    return Err(ApiError::RateLimited(note.into()));
                }
                return Err(ApiError::Parsing("Missing time series in Alpha Vantage response".into()));
            };

            let mut points: Vec<PricePoint> = Vec::new();
            if let Some(map) = ts.as_object() {
                for (date_str, fields) in map {
                    // Parse date as UTC midnight
                    let date = chrono::NaiveDate::parse_from_str(date_str, "%Y-%m-%d")
                        .map_err(|e| ApiError::Parsing(format!("Invalid date: {} - {}", date_str, e)))?;
                    let dt = chrono::DateTime::<chrono::Utc>::from_utc(date.and_hms_opt(0, 0, 0).unwrap(), chrono::Utc);

                    let open = get_num(fields, "1. open")?;
                    let high = get_num(fields, "2. high")?;
                    let low = get_num(fields, "3. low")?;
                    let close = get_num(fields, "4. close")?;
                    let volume = get_num(fields, "6. volume")? as u64;

                    points.push(PricePoint {
                        timestamp: dt,
                        open,
                        high,
                        low,
                        close,
                        volume,
                    });
                }
            }

            // Sort ascending by time
            points.sort_by_key(|p| p.timestamp);
            result.insert(symbol.clone(), points);
        }

        Ok(result)
    }
}

fn get_num(map: &serde_json::Value, key: &str) -> Result<f64, ApiError> {
    map.get(key)
        .and_then(|v| v.as_str())
        .and_then(|s| s.parse::<f64>().ok())
        .ok_or_else(|| ApiError::Parsing(format!("Missing or invalid '{}'", key)))
}

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("Network error: {0}")]
    Network(#[from] reqwest::Error),
    #[error("Backend error: {0}")]
    Backend(String),
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("Parsing error: {0}")]
    Parsing(String),
    #[error("Configuration error: {0}")]
    Config(String),
    #[error("Unsupported: {0}")]
    Unsupported(String),
    #[error("Rate limited: {0}")]
    RateLimited(String),
}
