use egui::{self, Color32, Ui};
use egui::plot::{Line, Plot, PlotPoints, PlotUi, Stroke};
use crate::components::PortfolioComponent;
use crate::portfolio::{Portfolio, PricePoint};
use crate::state::Config;
use std::collections::HashMap;
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Timeframe {
    Daily,
    Weekly,
    Monthly,
}

/// Helper function to convert a `DateTime<Utc>` into Unix seconds (as f64)
fn to_unix_secs(timestamp: DateTime<Utc>) -> f64 {
    timestamp.timestamp() as f64
}

/// Helper function that draws candlesticks onto an egui plot.
fn draw_candles(plot_ui: &mut PlotUi, candles: &[(f64, f64, f64, f64, f64)]) {
    for &(timestamp, open, high, low, close) in candles {
        // Choose colour based on price movement
        let color = if close >= open { Color32::GREEN } else { Color32::RED };

        // Draw the wick (high to low)
        plot_ui.line(
            Line::new(PlotPoints::from(vec![[timestamp, high], [timestamp, low]]))
                .color(Color32::WHITE),
        );

        // Draw the body as a rectangle using line thickness to emulate body
        let body_height = (close - open).abs();
        let body_y_top = open.max(close);
        let body_y_bottom = open.min(close);

        plot_ui.line(
            Line::new(PlotPoints::from(vec![[timestamp, body_y_top], [timestamp, body_y_bottom]]))
                .color(color)
                .width((body_height.max(0.5)) as f32),
        );
    }
}

/// UI component that displays a candlestick chart for a selected symbol.
pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    timeframe: Timeframe,
    price_history: Option<HashMap<String, Vec<PricePoint>>>,
}

impl CandlesComponent {
    pub fn new() -> Self {
        Self {
            is_open: true,
            selected_symbol: None,
            timeframe: Timeframe::Daily,
            price_history: None,
        }
    }
}

impl PortfolioComponent for CandlesComponent {
    /// Render the component. Matches the `PortfolioComponent` trait signature.
    fn render(&mut self, ui: &mut Ui, portfolio: &Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        egui::Window::new("Candles")
            .open(&mut self.is_open)
            .default_width(800.0)
            .show(ui.ctx(), |ui| {
                ui.heading("Candlestick Charts");

                // Gather symbols from the portfolio holdings
                let symbols: Vec<String> = portfolio.holdings.keys().cloned().collect();

                if symbols.is_empty() {
                    ui.label("No holdings available to display candle charts");
                    return;
                }

                // Symbol selector
                ui.horizontal(|ui| {
                    ui.label("Select Symbol:");
                    egui::ComboBox::from_id_source("symbol_selector")
                        .selected_text(
                            self.selected_symbol
                                .as_ref()
                                .cloned()
                                .unwrap_or_else(|| "Select".to_string()),
                        )
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_symbol, None, "Select");
                            for symbol in &symbols {
                                ui.selectable_value(&mut self.selected_symbol, Some(symbol.clone()), symbol);
                            }
                        });
                });

                // Timeframe selector (currently unused but kept for future extension)
                ui.horizontal(|ui| {
                    ui.label("Timeframe:");
                    egui::ComboBox::from_id_source("timeframe_selector")
                        .selected_text(format!("{:?}", self.timeframe))
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.timeframe, Timeframe::Daily, "Daily");
                            ui.selectable_value(&mut self.timeframe, Timeframe::Weekly, "Weekly");
                            ui.selectable_value(&mut self.timeframe, Timeframe::Monthly, "Monthly");
                        });
                });

                // Render chart if a symbol is selected
                if let Some(ref symbol) = self.selected_symbol {
                    if let Some(price_data) = portfolio.get_price_history(symbol) {
                        if price_data.is_empty() {
                            ui.label("No price history available for this symbol");
                            return;
                        }

                        // Convert price data into candle tuples
                        let mut candles: Vec<(f64, f64, f64, f64, f64)> = price_data
                            .iter()
                            .map(|pt| {
                                (
                                    to_unix_secs(pt.timestamp),
                                    pt.open,
                                    pt.high,
                                    pt.low,
                                    pt.close,
                                )
                            })
                            .collect();

                        // Limit to the most recent 100 points for performance
                        if candles.len() > 100 {
                            candles = candles[candles.len() - 100..].to_vec();
                        }

                        // Draw the candlestick plot
                        Plot::new("candle_chart")
                            .view_aspect(2.0)
                            .show(ui, |plot_ui| {
                                draw_candles(plot_ui, &candles);
                            });

                        // Summary of price change over the displayed period
                        ui.add_space(10.0);
                        if let (Some(first), Some(last)) = (candles.first(), candles.last()) {
                            let change = ((last.4 - first.1) / first.1) * 100.0;
                            let change_color = if change >= 0.0 {
                                Color32::GREEN
                            } else {
                                Color32::RED
                            };
                            ui.horizontal(|ui| {
                                ui.label("Period change:");
                                ui.colored_label(change_color, format!("{:.2}%", change));
                            });
                        }
                    } else {
                        ui.label("No price history available for this symbol");
                    }
                } else {
                    ui.label("Select a symbol to view its candlestick chart");
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

    fn category(&self) -> crate::components::ComponentCategory {
        crate::components::ComponentCategory::Charts
    }
}
