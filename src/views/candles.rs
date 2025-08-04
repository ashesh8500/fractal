use egui::{self, Color32, Ui};
use crate::views::PortfolioComponent;
use crate::portfolio::{Portfolio, Config, Timeframe};
use crate::views::ComponentCategory;
use std::collections::HashMap;
use chrono::{DateTime, Utc, TimeZone, UNIX_EPOCH};

// Helper function to convert timestamp to unix seconds
fn to_unix_secs(timestamp: DateTime<Utc>) -> f64 {
    timestamp.timestamp() as f64
}

// Helper function to draw candles
fn draw_candles(plot_ui: &mut egui::plot::PlotUi, candles: &[(f64, f64, f64, f64, f64)]) {
    for &(timestamp, open, high, low, close) in candles {
        let color = if close >= open {
            Color32::GREEN
        } else {
            Color32::RED
        };

        // Draw wick (high to low)
        plot_ui.line(egui::plot::Line::new(
            egui::plot::PlotPoints::from([timestamp, high], [timestamp, low])
        ).color(Color32::WHITE));

        // Draw body
        let body_height = (close - open).abs();
        let body_y = (open + close) / 2.0;
        
        plot_ui.rect(
            egui::plot::PlotRect::new(
                timestamp - 0.2,
                body_y - body_height / 2.0,
                0.4,
                body_height
            )
        ).color(color)
         .stroke(egui::Stroke::new(1.0, Color32::WHITE));
    }
}

pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    timeframe: Timeframe,
    price_history: Option<HashMap<String, Vec<crate::portfolio::PricePoint>>>,
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
    fn update(&mut self, ui: &mut Ui, portfolio: &mut Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        egui::Window::new("Candles")
            .open(&mut self.is_open)
            .default_width(800.0)
            .show(ui.ctx(), |ui| {
                ui.heading("Candlestick Charts");
                
                // Get symbols from portfolio
                let symbols: Vec<String> = portfolio.positions.keys().cloned().collect();
                
                if symbols.is_empty() {
                    ui.label("No positions available to display candle charts");
                    return;
                }

                // Symbol selection
                ui.horizontal(|ui| {
                    ui.label("Select Symbol:");
                    egui::ComboBox::from_id_source("symbol_selector")
                        .selected_text(self.selected_symbol.as_ref().map_or("Select".to_string(), |s| s.clone()))
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_symbol, None, "Select");
                            for symbol in &symbols {
                                ui.selectable_value(&mut self.selected_symbol, Some(symbol.clone()), symbol);
                            }
                        });
                });

                // Timeframe selection
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

                // Display chart if symbol is selected
                if let Some(ref symbol) = self.selected_symbol {
                    if let Some(price_data) = portfolio.get_price_history(symbol) {
                        if price_data.is_empty() {
                            ui.label("No price history available for this symbol");
                            return;
                        }

                        // Create candles data
                        let mut candles: Vec<(f64, f64, f64, f64, f64)> = Vec::new();
                        for point in price_data.iter() {
                            candles.push((
                                to_unix_secs(point.timestamp),
                                point.open,
                                point.high,
                                point.low,
                                point.close
                            ));
                        }

                        // Limit data points to prevent performance issues
                        if candles.len() > 100 {
                            candles = candles[candles.len() - 100..].to_vec();
                        }

                        // Render candlestick chart
                        egui::plot::Plot::new("candle_chart")
                            .view_aspect(2.0)
                            .show(ui, |plot_ui| {
                                draw_candles(&mut plot_ui, &candles);
                            });

                        // Display summary
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

    fn category(&self) -> ComponentCategory {
        ComponentCategory::Charts
    }
}
