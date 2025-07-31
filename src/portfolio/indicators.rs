//! Technical indicators for financial analysis

use super::types::PricePoint; // PricePoint is currently unused in this file, but keeping it for potential future use or consistency with other parts of the project that might interpret f64 slices as "PricePoints". OhlcvBar is definitely unused.

/// Simple Moving Average
pub fn sma(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.len() < period {
        return vec![];
    }
    
    let mut result = Vec::new();
    for i in period - 1..prices.len() {
        let sum: f64 = prices[i - period + 1..=i].iter().sum();
        result.push(sum / period as f64);
    }
    result
}

/// Exponential Moving Average
pub fn ema(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.is_empty() || period == 0 {
        return vec![];
    }
    
    let mut result = Vec::new();
    let multiplier = 2.0 / (period as f64 + 1.0);
    
    // Start with SMA for first value
    if prices.len() >= period {
        let first_sma: f64 = prices[0..period].iter().sum::<f64>() / period as f64;
        result.push(first_sma);
        
        // Calculate EMA for remaining values
        for i in period..prices.len() {
            let ema_value = (prices[i] * multiplier) + (result.last().unwrap() * (1.0 - multiplier));
            result.push(ema_value);
        }
    }
    
    result
}

/// Relative Strength Index
pub fn rsi(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.len() < period + 1 {
        return vec![];
    }
    
    let mut gains = Vec::new();
    let mut losses = Vec::new();
    
    // Calculate price changes
    for i in 1..prices.len() {
        let change = prices[i] - prices[i - 1];
        if change > 0.0 {
            gains.push(change);
            losses.push(0.0);
        } else {
            gains.push(0.0);
            losses.push(-change);
        }
    }
    
    let mut result = Vec::new();
    
    // Calculate RSI
    for i in period - 1..gains.len() {
        let avg_gain: f64 = gains[i - period + 1..=i].iter().sum::<f64>() / period as f64;
        let avg_loss: f64 = losses[i - period + 1..=i].iter().sum::<f64>() / period as f64;
        
        let rs = if avg_loss != 0.0 { avg_gain / avg_loss } else { 100.0 };
        let rsi_value = 100.0 - (100.0 / (1.0 + rs));
        result.push(rsi_value);
    }
    
    result
}

/// MACD (Moving Average Convergence Divergence)
pub struct MacdResult {
    pub macd_line: Vec<f64>,
    pub signal_line: Vec<f64>,
    pub histogram: Vec<f64>,
}

pub fn macd(prices: &[f64], fast_period: usize, slow_period: usize, signal_period: usize) -> MacdResult {
    let fast_ema = ema(prices, fast_period);
    let slow_ema = ema(prices, slow_period);
    
    // Calculate MACD line
    let mut macd_line = Vec::new();
    let start_index = slow_period - fast_period;
    
    for i in 0..fast_ema.len().min(slow_ema.len()) {
        if i + start_index < fast_ema.len() {
            macd_line.push(fast_ema[i + start_index] - slow_ema[i]);
        }
    }
    
    // Calculate signal line (EMA of MACD line)
    let signal_line = ema(&macd_line, signal_period);
    
    // Calculate histogram
    let mut histogram = Vec::new();
    let signal_start = signal_period - 1;
    
    for i in 0..signal_line.len() {
        if i + signal_start < macd_line.len() {
            histogram.push(macd_line[i + signal_start] - signal_line[i]);
        }
    }
    
    MacdResult {
        macd_line,
        signal_line,
        histogram,
    }
}

/// Bollinger Bands
pub struct BollingerBands {
    pub upper_band: Vec<f64>,
    pub middle_band: Vec<f64>,  // SMA
    pub lower_band: Vec<f64>,
}

pub fn bollinger_bands(prices: &[f64], period: usize, std_dev: f64) -> BollingerBands {
    let middle_band = sma(prices, period);
    let mut upper_band = Vec::new();
    let mut lower_band = Vec::new();
    
    for i in period - 1..prices.len() {
        let slice = &prices[i - period + 1..=i];
        let mean = slice.iter().sum::<f64>() / period as f64;
        
        // Calculate standard deviation
        let variance: f64 = slice.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / period as f64;
        let std_deviation = variance.sqrt();
        
        let upper = mean + (std_dev * std_deviation);
        let lower = mean - (std_dev * std_deviation);
        
        upper_band.push(upper);
        lower_band.push(lower);
    }
    
    BollingerBands {
        upper_band,
        middle_band,
        lower_band,
    }
}
