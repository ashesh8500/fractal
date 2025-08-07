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
            base_url: base_url.trim_end_matches('/').to_string(),
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
                // Capture status before consuming response by .text()
                let status = response.status();
                let text = response.text().await.unwrap_or_default();
                Err(ApiError::Backend(format!(
                    "Health check failed: status={}, body={}",
                    status,
                    text
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
                let status = response.status();
                let text = response.text().await.unwrap_or_default();
                Err(ApiError::Backend(format!(
                    "get_portfolios failed: status={}, body={}",
                    status,
                    text
                )))
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
            let url = format!("{}/portfolios/{}", self.base_url, urlencoding::encode(name));
            let response = self.client.get(&url).send().await?;
            
            if response.status().is_success() {
                let portfolio: Portfolio = response.json().await?;
                Ok(portfolio)
            } else {
                let status = response.status();
                let text = response.text().await.unwrap_or_default();
                Err(ApiError::Backend(format!(
                    "get_portfolio failed: status={}, body={}",
                    status,
                    text
                )))
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
                let status = response.status();
                let text = response.text().await.unwrap_or_default();
                Err(ApiError::Backend(format!(
                    "create_portfolio failed: status={}, body={}",
                    status,
                    text
                )))
            }
        }
    }
    
    /// Get current market data
    pub async fn get_market_data(&self, symbols: &[String]) -> Result<HashMap<String, f64>, ApiError> {
        if self.use_native_provider {
            self.alpha_vantage_current_prices(symbols).await
        } else {
            let symbols_str = symbols.join(",");
            let url = format!("{}/market-data?symbols={}", self.base_url, urlencoding::encode(&symbols_str));
            let response = self.client.get(&url).send().await?;
            
            if response.status().is_success() {
                let data: HashMap<String, f64> = response.json().await?;
                Ok(data)
            } else {
                let status = response.status();
                let text = response.text().await.unwrap_or_default();
                Err(ApiError::Backend(format!(
                    "get_market_data failed: status={}, body={}",
                    status,
                    text
                )))
            }
        }
    }
    
    /// Get historic price data for symbols from backend or native provider
    pub async fn get_historic_prices(
        &self,
        symbols: &[String],
        start_date: &str,
        end_date: &str,
    ) -> Result<HashMap<String, Vec<PricePoint>>, ApiError> {
        if self.use_native_provider {
            self.alpha_vantage_price_history(symbols, start_date, end_date).await
        } else {
            // Only call the history endpoint; do NOT fall back to /market-data (current-only).
            // Try both start/end variants for compatibility.
            let symbols_str = symbols.join(",");
            let attempts = vec![
                format!(
                    "{}/market-data/history?symbols={}&start={}&end={}",
                    self.base_url,
                    urlencoding::encode(&symbols_str),
                    urlencoding::encode(start_date),
                    urlencoding::encode(end_date)
                ),
                format!(
                    "{}/market-data/history?symbols={}&start_date={}&end_date={}",
                    self.base_url,
                    urlencoding::encode(&symbols_str),
                    urlencoding::encode(start_date),
                    urlencoding::encode(end_date)
                ),
            ];

            let mut last_err: Option<ApiError> = None;
            for url in attempts {
                match self.fetch_and_parse_history(&url).await {
                    Ok(map) => return Ok(map),
                    Err(e) => {
                        last_err = Some(e);
                        continue;
                    }
                }
            }

            // If the backend cannot provide history, optionally fall back to native if key present.
            if self.alphavantage_api_key.is_some() {
                log::warn!("Backend history endpoint failed. Falling back to Alpha Vantage for history.");
                return self.alpha_vantage_price_history(symbols, start_date, end_date).await;
            }

            Err(last_err.unwrap_or_else(|| {
                ApiError::Backend("All history endpoint attempts failed (no fallback native provider configured)".into())
            }))
        }
    }

    async fn fetch_and_parse_history(&self, url: &str) -> Result<HashMap<String, Vec<PricePoint>>, ApiError> {
        let response = self.client.get(url).send().await?;
        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(ApiError::Backend(format!(
                "history request failed: url={}, status={}, body={}",
                url, status, text
            )));
        }

        // Expect proper history shapes only; current-price maps are not supported here.
        // 1) { "AAPL": [ {timestamp, open, high, low, close, volume}, ... ], "MSFT": [...] }
        // 2) { "data": { "AAPL": [ {...} ], ... } }
        // 3) [ { "symbol": "AAPL", "prices": [ {...} ] }, ... ]
        // 4) { "market_data": [ {"symbol": "AAPL", "timestamp": "...", "open":...}, ... ] }  -> flattened
        let v: Value = response.json().await?;
        parse_history_value(v).map_err(|e| {
            ApiError::Parsing(format!("Failed parsing history from {}: {}", url, e))
        })
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
            // Use TIME_SERIES_DAILY (free tier) instead of TIME_SERIES_DAILY_ADJUSTED (premium)
            let url = format!(
                "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={}&outputsize=compact&apikey={}",
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
            
            // Log the full response for debugging
            log::debug!("Alpha Vantage response for {}: {}", symbol, serde_json::to_string_pretty(&v).unwrap_or_default());

            // Response has "Time Series (Daily)": { "YYYY-MM-DD": { "1. open": "...", ... }, ... }
            let Some(ts) = v.get("Time Series (Daily)") else {
                // Check for various error conditions in Alpha Vantage responses
                if let Some(note) = v.get("Note").and_then(|n| n.as_str()) {
                    log::warn!("Alpha Vantage rate limit hit: {}", note);
                    return Err(ApiError::RateLimited(note.into()));
                }
                if let Some(error) = v.get("Error Message").and_then(|e| e.as_str()) {
                    log::error!("Alpha Vantage error: {}", error);
                    return Err(ApiError::Parsing(format!("Alpha Vantage API error: {}", error)));
                }
                if let Some(info) = v.get("Information").and_then(|i| i.as_str()) {
                    log::warn!("Alpha Vantage info message: {}", info);
                    return Err(ApiError::RateLimited(info.into()));
                }
                
                // Log the full response structure to help debug
                let available_keys: Vec<String> = v.as_object()
                    .map(|obj| obj.keys().cloned().collect())
                    .unwrap_or_default();
                    
                return Err(ApiError::Parsing(format!(
                    "Missing time series in Alpha Vantage response for {}. Available keys: {:?}. Response: {}", 
                    symbol, 
                    available_keys,
                    serde_json::to_string(&v).unwrap_or_default()
                )));
            };

            let mut points: Vec<PricePoint> = Vec::new();
            if let Some(map) = ts.as_object() {
                for (date_str, fields) in map {
                    // Parse date as UTC midnight
                    let date = chrono::NaiveDate::parse_from_str(date_str, "%Y-%m-%d")
                        .map_err(|e| ApiError::Parsing(format!("Invalid date: {} - {}", date_str, e)))?;
                    let naive_dt = date.and_hms_opt(0, 0, 0).ok_or_else(|| {
                        ApiError::Parsing(format!("Invalid time for date {}", date_str))
                    })?;
                    // Use from_naive_utc_and_offset to avoid deprecated from_utc
                    let dt = chrono::DateTime::<chrono::Utc>::from_naive_utc_and_offset(naive_dt, chrono::Utc);

                    let open = get_num(fields, "1. open")?;
                    let high = get_num(fields, "2. high")?;
                    let low = get_num(fields, "3. low")?;
                    let close = get_num(fields, "4. close")?;
                    let volume = get_num(fields, "5. volume")? as u64;

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

fn parse_history_value(v: Value) -> Result<HashMap<String, Vec<PricePoint>>, String> {
    // Case 1: Simple symbol->array map
    if let Some(map) = v.as_object() {
        // Check if values are arrays of objs
        let mut out: HashMap<String, Vec<PricePoint>> = HashMap::new();

        // Some servers wrap under "data"
        if let Some(inner) = map.get("data") {
            return parse_history_value(inner.clone());
        }

        // Some servers might put a flat "market_data" array with symbol per row
        if let Some(arr) = map.get("market_data").and_then(|m| m.as_array()) {
            let mut grouped: HashMap<String, Vec<PricePoint>> = HashMap::new();
            for row in arr {
                if let Some(symbol) = row.get("symbol").and_then(|s| s.as_str()) {
                    if let Some(pp) = parse_price_point(row) {
                        grouped.entry(symbol.to_string()).or_default().push(pp);
                    }
                }
            }
            for (_k, v) in grouped.iter_mut() {
                v.sort_by_key(|p| p.timestamp);
            }
            return Ok(grouped);
        }

        // Else, treat each key as symbol => array of points
        let mut any_symbol = false;
        for (symbol, arr_val) in map {
            if let Some(arr) = arr_val.as_array() {
                any_symbol = true;
                let mut points = Vec::new();
                for item in arr {
                    if let Some(pp) = parse_price_point(item) {
                        points.push(pp);
                    }
                }
                points.sort_by_key(|p| p.timestamp);
                out.insert(symbol.clone(), points);
            }
        }
        if any_symbol {
            return Ok(out);
        }
    }

    // Case 3: Array of { symbol, prices: [ ... ] }
    if let Some(arr) = v.as_array() {
        let mut out: HashMap<String, Vec<PricePoint>> = HashMap::new();
        for entry in arr {
            if let Some(symbol) = entry.get("symbol").and_then(|s| s.as_str()) {
                if let Some(prices) = entry.get("prices").and_then(|p| p.as_array()) {
                    let mut pts = Vec::new();
                    for item in prices {
                        if let Some(pp) = parse_price_point(item) {
                            pts.push(pp);
                        }
                    }
                    pts.sort_by_key(|p| p.timestamp);
                    out.insert(symbol.to_string(), pts);
                }
            }
        }
        if !out.is_empty() {
            return Ok(out);
        }
    }

    Err("Unsupported history response shape".into())
}

fn parse_price_point(item: &Value) -> Option<PricePoint> {
    // Accept different field names for timestamp
    let ts = item.get("timestamp")
        .or_else(|| item.get("time"))
        .or_else(|| item.get("date"))?;

    // Parse timestamp which can be iso string or epoch millis/seconds
    let timestamp = if let Some(s) = ts.as_str() {
        // Try RFC3339/ISO8601
        if let Ok(dt) = chrono::DateTime::parse_from_rfc3339(s) {
            dt.with_timezone(&chrono::Utc)
        } else if let Ok(nd) = chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d") {
            let naive = nd.and_hms_opt(0, 0, 0)?;
            chrono::DateTime::<chrono::Utc>::from_naive_utc_and_offset(naive, chrono::Utc)
        } else {
            return None;
        }
    } else if let Some(n) = ts.as_i64() {
        // Treat as epoch seconds using DateTime::from_timestamp (new API)
        let dt = chrono::DateTime::<chrono::Utc>::from_timestamp(n, 0)?;
        dt
    } else {
        return None;
    };

    let open = get_num_flex(item, &["open", "o"])?;
    let high = get_num_flex(item, &["high", "h"])?;
    let low = get_num_flex(item, &["low", "l"])?;
    let close = get_num_flex(item, &["close", "c", "adj_close"]).unwrap_or_else(|| {
        // If close not available, try 'price'
        get_num_flex(item, &["price"]).unwrap_or(0.0)
    });
    let volume = get_num_flex(item, &["volume", "v"])
        .map(|v| v as u64)
        .unwrap_or(0);

    Some(PricePoint {
        timestamp,
        open,
        high,
        low,
        close,
        volume,
    })
}

fn get_num_flex(map: &Value, keys: &[&str]) -> Option<f64> {
    for k in keys {
        if let Some(v) = map.get(*k) {
            if let Some(n) = v.as_f64() {
                return Some(n);
            }
            if let Some(s) = v.as_str() {
                if let Ok(n) = s.parse::<f64>() {
                    return Some(n);
                }
            }
        }
    }
    None
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
