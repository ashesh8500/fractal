use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::{Portfolio, PricePoint};
use crate::state::Config;
use chrono::Datelike;
use egui::{self, Color32, Ui};
use egui_plot::{BoxElem, BoxPlot, BoxSpread, Legend, Plot};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum RangePreset {
    OneM,
    ThreeM,
    SixM,
    YTD,
    OneY,
    All,
}

/// CandlesComponent implemented using BoxPlot, following egui demo patterns.
/// Each candle is represented as a BoxElem (min/low, quartiles via open/close, max/high).
pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    range: RangePreset,
}

impl CandlesComponent {
    pub fn new() -> Self {
        Self {
            is_open: true,
            selected_symbol: None,
            range: RangePreset::All,
        }
    }
}

impl PortfolioComponent for CandlesComponent {
    fn render(&mut self, ui: &mut Ui, portfolio: &Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        // Base id scoped to the current Ui path for this component (content-scope)
        let base_id = ui.id().with("component::candles::content");

        ui.heading("Candlestick (BoxPlot Demo)");
        ui.separator();

        // Symbols list from holdings, sorted for stable ordering
        let mut symbols: Vec<String> = portfolio.holdings.keys().cloned().collect();
        symbols.sort();

        if symbols.is_empty() {
            ui.label("No holdings available. Add holdings to view candles.");
            return;
        }

        // Auto-select first symbol if none selected
        if self.selected_symbol.is_none() && !symbols.is_empty() {
            self.selected_symbol = Some(symbols[0].clone());
        }

        ui.horizontal(|ui| {
            ui.label("Symbol:");
            let combo_id = base_id.with(("candles", "symbol_combo"));
            egui::ComboBox::from_id_salt(combo_id)
                .selected_text(
                    self.selected_symbol
                        .as_ref()
                        .map(|s| s.as_str())
                        .unwrap_or("Select symbol"),
                )
                .show_ui(ui, |ui| {
                    for sym in &symbols {
                        let selected = self.selected_symbol.as_deref() == Some(sym.as_str());
                        if ui.selectable_label(selected, sym).clicked() {
                            self.selected_symbol = Some(sym.clone());
                        }
                    }
                });
        });

        ui.add_space(8.0);

        // Range presets for quick filtering
        ui.horizontal(|ui| {
            ui.label("Range:");
            let make_btn = |ui: &mut egui::Ui,
                            label: &str,
                            variant: RangePreset,
                            current: &mut RangePreset| {
                let selected = *current == variant;
                if ui.selectable_label(selected, label).clicked() {
                    *current = variant;
                }
            };
            make_btn(ui, "1M", RangePreset::OneM, &mut self.range);
            make_btn(ui, "3M", RangePreset::ThreeM, &mut self.range);
            make_btn(ui, "6M", RangePreset::SixM, &mut self.range);
            make_btn(ui, "YTD", RangePreset::YTD, &mut self.range);
            make_btn(ui, "1Y", RangePreset::OneY, &mut self.range);
            make_btn(ui, "All", RangePreset::All, &mut self.range);
        });

        if let Some(sym) = self.selected_symbol.clone() {
            if let Some(series) = portfolio.get_price_history(&sym) {
                render_boxplot_candles(ui, &sym, series, base_id, self.range);
            } else {
                ui.colored_label(Color32::YELLOW, "No price history for selected symbol.");
            }
        } else {
            ui.label("Choose a symbol to display candlesticks.");
        }
    }

    fn name(&self) -> &str {
        "Candles"
    }

    fn is_open(&self) -> bool {
        self.is_open
    }

    fn set_open(&mut self, open: bool) {
        self.is_open = open;
    }

    fn category(&self) -> ComponentCategory {
        ComponentCategory::Charts
    }
}

fn render_boxplot_candles(
    ui: &mut Ui,
    symbol: &str,
    data: &[PricePoint],
    base_id: egui::Id,
    preset: RangePreset,
) {
    if data.is_empty() {
        ui.label("No data points available.");
        return;
    }

    // Theme-aware stroke and semi-transparent fills for good contrast on light/dark
    let visuals = ui.visuals().clone();
    let stroke_color = visuals.widgets.noninteractive.fg_stroke.color;
    let up_fill = Color32::from_rgba_premultiplied(0, 180, 0, 200);
    let down_fill = Color32::from_rgba_premultiplied(220, 60, 60, 200);
    let stroke_width = 2.0;

    // Apply range preset by timestamp cutoff, then limit bars for performance
    let cutoff_opt = range_cutoff(
        &ui.ctx().style().visuals,
        data.last().map(|p| p.timestamp),
        preset,
    );

    let filtered: Vec<&PricePoint> = if let Some(cutoff) = cutoff_opt {
        data.iter().filter(|p| p.timestamp >= cutoff).collect()
    } else {
        data.iter().collect()
    };

    let max_points = 500;
    let slice_refs: Vec<&PricePoint> = if filtered.len() > max_points {
        filtered[filtered.len() - max_points..].to_vec()
    } else {
        filtered
    };

    // Build box elements from OHLC using quartiles representation:
    // whisker_low = low
    // q1 = min(open, close)
    // median = (open + close)/2
    // q3 = max(open, close)
    // whisker_high = high
    let mut boxes = Vec::with_capacity(slice_refs.len());
    for (i, p) in slice_refs.iter().enumerate() {
        let low = p.low;
        let high = p.high;
        let (q1, q3) = if p.open <= p.close {
            (p.open, p.close)
        } else {
            (p.close, p.open)
        };
        let median = 0.5 * (p.open + p.close);

        // egui_plot 0.31: construct BoxSpread using `new(lower_whisker, q1, median, q3, upper_whisker)`
        let spread = BoxSpread::new(low, q1, median, q3, high);
        let mut be = BoxElem::new(i as f64, spread);

        // Color depending on up/down day
        let up = p.close >= p.open;
        let fill = if up { up_fill } else { down_fill };
        be = be
            .fill(fill)
            .stroke(egui::Stroke::new(stroke_width, stroke_color));

        boxes.push(be);
    }

    // Plot id scoped under the content base_id to avoid collisions
    let plot_id = base_id.with(("candles", "boxplot_plot", symbol));
    Plot::new(plot_id)
        .legend(Legend::default())
        .allow_scroll(false) // pan/zoom inside plot
        .allow_boxed_zoom(true)
        .show_axes([true, true])
        .show_grid(true)
        .show(ui, |plot_ui| {
            let bp = BoxPlot::new(boxes).name(format!("{symbol} OHLC"));
            plot_ui.box_plot(bp);
        });
}

// Compute the cutoff timestamp for a given range preset.
// If None, no filtering is applied.
fn range_cutoff(
    _visuals: &egui::style::Visuals,
    last_ts: Option<chrono::DateTime<chrono::Utc>>,
    preset: RangePreset,
) -> Option<chrono::DateTime<chrono::Utc>> {
    let last = last_ts?;
    let days = match preset {
        RangePreset::OneM => 30,
        RangePreset::ThreeM => 90,
        RangePreset::SixM => 180,
        RangePreset::YTD => {
            // From Jan 1st of current year in UTC
            let y = last.year();
            let jan1 = chrono::NaiveDate::from_ymd_opt(y, 1, 1)?.and_hms_opt(0, 0, 0)?;
            let dt = chrono::DateTime::<chrono::Utc>::from_naive_utc_and_offset(jan1, chrono::Utc);
            return Some(dt);
        }
        RangePreset::OneY => 365,
        RangePreset::All => return None,
    };
    Some(last - chrono::Duration::days(days))
}
