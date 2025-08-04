#![allow(clippy::needless_return)]
//! Candlestick charts component for detailed price analysis
//! Improvements:
//! - Uses standardized WindowPanel wrapper
//! - Scrollable content to avoid overflow/clipping
//! - Proper candlestick rendering (wick + body) instead of baseline bars
//! - Time-based X axis with date tick formatting
//! - Cleaner controls and legends

use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::Portfolio;
use crate::state::Config;

use egui::{self};
use egui_plot::{Legend, Line, Plot, PlotPoints, PlotUi};
use std::time::UNIX_EPOCH;

// New helper window
use crate::ui::widgets::window::WindowPanel;

pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    timeframe: Timeframe,
}

#[derive(Debug, Clone, PartialEq)]
enum Timeframe {
    Daily,
    Weekly,
    Monthly,
}

impl CandlesComponent {
    pub fn new() -> Self {
        Self {
            is_open: false,
            selected_symbol: None,
            timeframe: Timeframe::Daily,
        }
    }
}

fn to_unix_secs(ts: chrono::DateTime<chrono::Utc>) -> f64 {
    ts.timestamp() as f64
}

fn draw_candles(plot_ui: &mut PlotUi<'_>, ohlcv: &[(f64, f64, f64, f64, f64)]) {
    // ohlcv: (x, open, high, low, close)
    // Render using:
    // - wick: vertical line from low to high
    // - body: thicker vertical line from open to close
    // We use NaN breaks to draw per-candle segments in single Line items.

    // Wicks
    let mut wick_segments: Vec<[f64; 2]> = Vec::with_capacity(ohlcv.len() * 3);

    // Bodies separated by direction for color
    let mut up_flat: Vec<[f64; 2]> = Vec::with_capacity(ohlcv.len() * 3);
    let mut down_flat: Vec<[f64; 2]> = Vec::with_capacity(ohlcv.len() * 3);

    for (x, open, high, low, close) in ohlcv.iter().copied() {
        // Wick
        wick_segments.push([x, low]);
        wick_segments.push([x, high]);
        wick_segments.push([f64::NAN, f64::NAN]); // break

        // Body
        let (y0, y1) = (open, close);
        if close >= open {
            up_flat.push([x, y0]);
            up_flat.push([x, y1]);
            up_flat.push([f64::NAN, f64::NAN]);
        } else {
            down_flat.push([x, y0]);
            down_flat.push([x, y1]);
            down_flat.push([f64::NAN, f64::NAN]);
        }
    }

    // Draw wicks
    if !wick_segments.is_empty() {
        let wick_line = Line::new(PlotPoints::from(wick_segments))
            .color(egui::Color32::LIGHT_GRAY)
            .name("Wick")
            .width(1.0);
        plot_ui.line(wick_line);
    }

    // Draw bodies
    if !up_flat.is_empty() {
        let up_line = Line::new(PlotPoints::from(up_flat))
            .color(egui::Color32::from_rgb(0, 180, 0))
            .name("Up Body")
            .width(6.0);
        plot_ui.line(up_line);
    }
    if !down_flat.is_empty() {
        let down_line = Line::new(PlotPoints::from(down_flat))
            .color(egui::Color32::from_rgb(200, 30, 30))
            .name("Down Body")
            .width(6.0);
        plot_ui.line(down_line);
    }
}

impl PortfolioComponent for CandlesComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        // Use a standardized window like in egui demos
        let ctx = ui.ctx().clone();
        let mut open = self.is_open;

        WindowPanel::new("candles_window", "Candlestick Charts", &mut open)
            .default_size([760.0, 560.0])
            .resizable(true)
            .scroll(false, false)
            .show(&ctx, |ui| {
                egui::ScrollArea::vertical()
                    .auto_shrink([false, false])
                    .show(ui, |ui| {
                        ui.heading("Candlestick Charts");

                        // Controls
                        ui.group(|ui| {
                            ui.horizontal_wrapped(|ui| {
                                ui.label("Symbol:");
                                let symbols = portfolio.symbols();
                                if !symbols.is_empty() {
                                    egui::ComboBox::from_id_salt("candles_symbol_selector")
                                        .selected_text(
                                            self.selected_symbol
                                                .as_deref()
                                                .unwrap_or("Select symbol")
                                                .to_string(),
                                        )
                                        .show_ui(ui, |ui| {
                                            for symbol in &symbols {
                                                ui.selectable_value(
                                                    &mut self.selected_symbol,
                                                    Some(symbol.clone()),
                                                    symbol,
                                                );
                                            }
                                        });
                                } else {
                                    ui.weak("No symbols available");
                                }

                                ui.separator();

                                ui.label("Timeframe:");
                                egui::ComboBox::from_id_salt("candles_timeframe_selector")
                                    .selected_text(format!("{:?}", self.timeframe))
                                    .show_ui(ui, |ui| {
                                        ui.selectable_value(
                                            &mut self.timeframe,
                                            Timeframe::Daily,
                                            "Daily",
                                        );
                                        ui.selectable_value(
                                            &mut self.timeframe,
                                            Timeframe::Weekly,
                                            "Weekly",
                                        );
                                        ui.selectable_value(
                                            &mut self.timeframe,
                                            Timeframe::Monthly,
                                            "Monthly",
                                        );
                                    });
                            });
                        });

                        ui.add_space(6.0);
                        ui.separator();

                        if let Some(symbol) = &self.selected_symbol {
                            if let Some(price_history_map) = &portfolio.price_history {
                                if let Some(prices) = price_history_map.get(symbol) {
                                    if prices.is_empty() {
                                        ui.label("No price history available for this symbol");
                                        return;
                                    }

                                    ui.heading(format!(
                                        "{} Candlestick Chart ({:?})",
                                        symbol, self.timeframe
                                    ));

                                    if let Some(latest) = prices.last() {
                                        ui.horizontal_wrapped(|ui| {
                                            ui.label(format!("Open: ${:.2}", latest.open));
                                            ui.separator();
                                            ui.label(format!("High: ${:.2}", latest.high));
                                            ui.separator();
                                            ui.label(format!("Low: ${:.2}", latest.low));
                                            ui.separator();
                                            ui.label(format!("Close: ${:.2}", latest.close));
                                            ui.separator();
                                            ui.label(format!("Volume: {}", latest.volume));
                                        });
                                    }

                                    ui.add_space(8.0);

                                    // Build candle tuples
                                    // Limit to last N for performance
                                    let show_n = prices.len().min(300);
                                    let start = prices.len().saturating_sub(show_n);

                                    let candles: Vec<(f64, f64, f64, f64, f64)> = prices[start..]
                                        .iter()
                                        .map(|p| {
                                            (
                                                to_unix_secs(p.timestamp),
                                                p.open,
                                                p.high,
                                                p.low,
                                                p.close,
                                            )
                                        })
                                        .collect();

                                    // Render candlesticks
                                    Plot::new(format!("candlestick_chart_{}", symbol))
                                        .view_aspect(2.0)
                                        .legend(Legend::default())
                                        .x_axis_formatter(|mark, _| {
                                            let secs = mark.value;
                                            let ts = UNIX_EPOCH
                                                + std::time::Duration::from_secs_f64(secs.max(0.0));
                                            let dt: chrono::DateTime<chrono::Utc> =
                                                chrono::DateTime::<chrono::Utc>::from(ts);
                                            dt.format("%Y-%m-%d").to_string()
                                        })
                                        .show(ui, |plot_ui| {
                                            draw_candles(plot_ui, &candles);
                                        });

                                    // Volume bars below price chart as a line
                                    ui.add_space(8.0);
                                    ui.heading("Volume");
                                    let volumes: Vec<[f64; 2]> = prices[start..]
                                        .iter()
                                        .map(|p| [to_unix_secs(p.timestamp), p.volume as f64])
                                        .collect();

                                    let volume_line = Line::new(PlotPoints::from(volumes))
                                        .color(egui::Color32::LIGHT_BLUE)
                                        .name("Volume");

                                    Plot::new(format!("volume_chart_{}", symbol))
                                        .view_aspect(2.0)
                                        .x_axis_formatter(|mark, _| {
                                            let secs = mark.value;
                                            let ts = UNIX_EPOCH
                                                + std::time::Duration::from_secs_f64(secs.max(0.0));
                                            let dt: chrono::DateTime<chrono::Utc> =
                                                chrono::DateTime::<chrono::Utc>::from(ts);
                                            dt.format("%Y-%m-%d").to_string()
                                        })
                                        .show(ui, |plot_ui| {
                                            plot_ui.line(volume_line);
                                        });

                                    // Summary
                                    ui.add_space(8.0);
                                    ui.separator();
                                    ui.label(format!("Data points: {}", prices.len()));

                                    if prices.len() > 1 {
                                        let first = &prices[0];
                                        let last = &prices[prices.len() - 1];
                                        let change =
                                            ((last.close - first.close) / first.close) * 100.0;
                                        let change_color = if change >= 0.0 {
                                            egui::Color32::GREEN
                                        } else {
                                            egui::Color32::RED
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
                                ui.label("No price history data loaded");
                            }
                        } else {
                            ui.label("Select a symbol to view its candlestick chart");
                        }
                    });
            });

        self.is_open = open;
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
