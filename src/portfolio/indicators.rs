 //! Technical indicators for financial analysis


/// Simple Moving Average
/// Returns a vector of SMA values starting from the first index where a full window is available (period - 1).
/// If prices.len() < period or period == 0, returns an empty vector.
pub fn sma(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.is_empty() || period == 0 || prices.len() < period {
        return Vec::new();
    }

    let mut result = Vec::with_capacity(prices.len() - period + 1);

    // Compute initial window sum [0..period)
    let mut window_sum: f64 = prices.iter().take(period).sum();
    result.push(window_sum / period as f64);

    // Slide the window from index (period) to end
    for i in period..prices.len() {
        // safe because i >= period >= 1
        window_sum += prices[i] - prices[i - period];
        result.push(window_sum / period as f64);
    }

    result
}

/// Exponential Moving Average
/// Returns a vector of EMA values starting from the first index where a full window is available.
/// If prices.len() < period or period == 0, returns an empty vector.
pub fn ema(prices: &[f64], period: usize) -> Vec<f64> {
    if prices.is_empty() || period == 0 || prices.len() < period {
        return Vec::new();
    }

    let multiplier = 2.0 / (period as f64 + 1.0);
    let mut result = Vec::with_capacity(prices.len() - period + 1);

    // Seed EMA with SMA of the first 'period' values
    let seed_sma: f64 = prices.iter().take(period).sum::<f64>() / period as f64;
    result.push(seed_sma);

    // Now iterate from the element after the seed window
    // The EMA next uses the next price at index 'period'
    let mut prev_ema = seed_sma;
    for i in period..prices.len() {
        let current_price = prices[i];
        let ema_val = (current_price - prev_ema) * multiplier + prev_ema;
        result.push(ema_val);
        prev_ema = ema_val;
    }

    result
}

/// Relative Strength Index (RSI)
/// Wilder's RSI. Returns values starting from the first index with a full window.
/// If prices.len() <= period or period == 0, returns empty.
pub fn rsi(prices: &[f64], period: usize) -> Vec<f64> {
    if period == 0 || prices.len() <= period {
        return Vec::new();
    }

    // Initial average gain/loss over the first 'period' deltas
    let mut gains = 0.0_f64;
    let mut losses = 0.0_f64;

    for i in 1..=period {
        let change = prices[i] - prices[i - 1];
        if change > 0.0 {
            gains += change;
        } else {
            losses += -change;
        }
    }

    let mut avg_gain = gains / period as f64;
    let mut avg_loss = losses / period as f64;

    let mut result = Vec::with_capacity(prices.len() - period);
    // First RSI value corresponds to the end of the initial window
    let rs_first = if avg_loss == 0.0 { f64::INFINITY } else { avg_gain / avg_loss };
    let mut rsi_val = 100.0 - (100.0 / (1.0 + rs_first));
    result.push(rsi_val);

    // Wilder's smoothing for subsequent values
    for i in period + 1..prices.len() {
        let change = prices[i] - prices[i - 1];
        let gain = if change > 0.0 { change } else { 0.0 };
        let loss = if change < 0.0 { -change } else { 0.0 };

        avg_gain = (avg_gain * (period as f64 - 1.0) + gain) / period as f64;
        avg_loss = (avg_loss * (period as f64 - 1.0) + loss) / period as f64;

        let rs = if avg_loss == 0.0 { f64::INFINITY } else { avg_gain / avg_loss };
        rsi_val = 100.0 - (100.0 / (1.0 + rs));
        result.push(rsi_val);
    }

    result
}

/// MACD (Moving Average Convergence Divergence)
pub struct MacdResult {
    pub macd_line: Vec<f64>,
    pub signal_line: Vec<f64>,
    pub histogram: Vec<f64>,
}

/// Compute MACD and histogram. Returns variable-length series beginning at the first index where both EMAs are available.
/// Note: Output lengths depend on input size and periods; consumers should handle potential leading alignment differences.
pub fn macd(prices: &[f64], fast_period: usize, slow_period: usize, signal_period: usize) -> MacdResult {
    // Guard against invalid periods
    if prices.is_empty() || fast_period == 0 || slow_period == 0 || signal_period == 0 || fast_period >= slow_period {
        return MacdResult {
            macd_line: Vec::new(),
            signal_line: Vec::new(),
            histogram: Vec::new(),
        };
    }

    let fast_ema = ema(prices, fast_period);
    let slow_ema = ema(prices, slow_period);

    // Align EMAs: fast_ema starts at index fast_period-1, slow_ema at slow_period-1
    // So MACD starts at slow_period-1, where both are available.
    let mut macd_line = Vec::new();
    if !fast_ema.is_empty() && !slow_ema.is_empty() && slow_period > fast_period {
        // Offset between the starts of slow_ema and fast_ema series
        let offset = slow_period - fast_period;
        // Pairwise subtract aligned values
        let n = slow_ema.len().min(fast_ema.len().saturating_sub(offset));
        for i in 0..n {
            macd_line.push(fast_ema[i + offset] - slow_ema[i]);
        }
    }

    // Signal line is EMA of MACD line
    let signal_line = ema(&macd_line, signal_period);

    // Histogram starts where both macd_line and signal_line align
    let mut histogram = Vec::new();
    if !signal_line.is_empty() {
        // signal_line starts after signal_period-1 samples of macd_line
        let offset = signal_period.saturating_sub(1);
        let n = signal_line.len().min(macd_line.len().saturating_sub(offset));
        for i in 0..n {
            histogram.push(macd_line[i + offset] - signal_line[i]);
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

/// Compute Bollinger Bands. Returns vectors starting where a full window is available.
/// If inputs are insufficient, returns empty bands.
pub fn bollinger_bands(prices: &[f64], period: usize, std_dev: f64) -> BollingerBands {
    if prices.is_empty() || period == 0 || prices.len() < period {
        return BollingerBands {
            upper_band: Vec::new(),
            middle_band: Vec::new(),
            lower_band: Vec::new(),
        };
    }

    let middle_band = sma(prices, period);
    let mut upper_band = Vec::with_capacity(middle_band.len());
    let mut lower_band = Vec::with_capacity(middle_band.len());

    // For each SMA value, compute std dev over the corresponding window
    // The first SMA corresponds to window [0..period)
    for i in period..=prices.len() {
        let slice = &prices[i - period..i];
        let mean = middle_band[i - period]; // aligned with the window ending at i-1

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
