use egui::{self, Color32, Ui};
use egui_plot::{BoxElem, BoxPlot, BoxSpread, Legend, Plot};
use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::{Portfolio, PricePoint};
use crate::state::Config;

/// CandlesComponent implemented using BoxPlot, following egui demo patterns.
/// Each candle is represented as a BoxElem (min/low, quartiles via open/close, max/high).
pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
}

impl CandlesComponent {
    pub fn new() -> Self {
        Self {
            is_open: true,
            selected_symbol: None,
        }
    }
}

impl PortfolioComponent for CandlesComponent {
    fn render(&mut self, ui: &mut Ui, portfolio: &Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        // Base id scoped to the current Ui path for this component
        let window_id = ui.id().with("component::candles::window");

        egui::Window::new("Candles")
            .id(window_id)
            .open(&mut self.is_open)
            .default_width(900.0)
            .default_height(560.0)
            .show(ui.ctx(), |ui| {
                // Derive a window-local base id
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

                ui.horizontal(|ui| {
                    ui.label("Symbol:");
                    let combo_id = ui.id().with("candles_symbol_combo");
                    egui::ComboBox::from_id_salt(combo_id)
                        .selected_text(
                            self.selected_symbol
                                .as_ref()
                                .map(|s| s.as_str())
                                .unwrap_or("Select symbol"),
                        )
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_label(self.selected_symbol.is_none(), "Select symbol")
                                .clicked()
                            {
                                self.selected_symbol = None;
                            }
                            for sym in &symbols {
                                let selected = self.selected_symbol.as_deref() == Some(sym.as_str());
                                if ui.selectable_label(selected, sym).clicked() {
                                    self.selected_symbol = Some(sym.clone());
                                }
                            }
                        });
                });

                ui.add_space(8.0);

                if let Some(sym) = self.selected_symbol.clone() {
                    if let Some(series) = portfolio.get_price_history(&sym) {
                        render_boxplot_candles(ui, &sym, series, base_id);
                    } else {
                        ui.colored_label(Color32::YELLOW, "No price history for selected symbol.");
                    }
                } else {
                    ui.label("Choose a symbol to display candlesticks.");
                }
            });
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

fn render_boxplot_candles(ui: &mut Ui, symbol: &str, data: &[PricePoint], base_id: egui::Id) {
    if data.is_empty() {
        ui.label("No data points available.");
        return;
    }

    // Limit bars for performance (demo pattern)
    let max_points = 300;
    let slice = if data.len() > max_points {
        &data[data.len() - max_points..]
    } else {
        data
    };

    // Build box elements from OHLC using quartiles representation:
    // whisker_low = low
    // q1 = min(open, close)
    // median = (open + close)/2
    // q3 = max(open, close)
    // whisker_high = high
    let mut boxes = Vec::with_capacity(slice.len());
    for (i, p) in slice.iter().enumerate() {
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
        let fill = if up {
            Color32::from_rgb(0, 180, 0)
        } else {
            Color32::from_rgb(200, 40, 40)
        };
        be = be.fill(fill).stroke(egui::Stroke::new(1.0, Color32::WHITE));

        boxes.push(be);
    }

    // Plot id scoped to this window content to avoid collisions
    let plot_id = base_id.with(("candles_boxplot_plot", symbol));
    Plot::new(plot_id)
        .legend(Legend::default())
        .allow_scroll(false)
        .allow_boxed_zoom(true)
        .show(ui, |plot_ui| {
            let bp = BoxPlot::new(boxes).name(format!("{symbol} OHLC"));
            plot_ui.box_plot(bp);
        });
}
