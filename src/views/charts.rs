#![allow(clippy::needless_return)]
//! Price charts component for technical analysis
//! Improvements:
//! - Window/panel is scrollable to avoid clipped content
//! - Time-based X axis with date formatting
//! - Better controls UI and legends
//! - Uses egui demo patterns (ScrollArea, headings, spacing)

use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::Portfolio;
use crate::state::Config;
use crate::portfolio::indicators::{ema, rsi, sma};

use egui::{self};
use egui_plot::{Legend, Line, LineStyle, Plot, PlotPoints, PlotUi};
use std::time::{SystemTime, UNIX_EPOCH};

pub struct ChartsComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    show_sma20: bool,
    show_ema12: bool,
    show_rsi: bool,
}

impl ChartsComponent {
    pub fn new() -> Self {
        Self {
            is_open: false,
            selected_symbol: None,
            show_sma20: true,
            show_ema12: true,
            show_rsi: true,
        }
    }
}

fn to_unix_secs(ts: chrono::DateTime<chrono::Utc>) -> f64 {
    ts.timestamp() as f64
}

fn format_price_chart(
    plot_ui: &mut PlotUi,
    closes: &[(f64, f64)],
    sma20: Option<Vec<(f64, f64)>>,
    ema12: Option<Vec<(f64, f64)>>,
) {
    let price_line = Line::new(PlotPoints::from_iter(closes.iter().map(|(x, y)| [*x, *y])))
        .color(egui::Color32::BLUE)
        .name("Close");
    plot_ui.line(price_line);

    if let Some(s) = sma20 {
        let line = Line::new(PlotPoints::from_iter(s.iter().map(|(x, y)| [*x, *y])))
            .color(egui::Color32::RED)
            .name("SMA 20");
        plot_ui.line(line);
    }
    if let Some(e) = ema12 {
        let line = Line::new(PlotPoints::from_iter(e.iter().map(|(x, y)| [*x, *y])))
            .color(egui::Color32::GREEN)
            .name("EMA 12");
        plot_ui.line(line);
    }
}

fn format_rsi_chart(plot_ui: &mut PlotUi, rsi_series: &[(f64, f64)]) {
    let rsi_line = Line::new(PlotPoints::from_iter(
        rsi_series.iter().map(|(x, y)| [*x, *y]),
    ))
    .color(egui::Color32::YELLOW)
    .name("RSI 14");
    plot_ui.line(rsi_line);

    // dashed guide lines 70/30
    let min_x = rsi_series.first().map(|(x, _)| *x).unwrap_or(0.0);
    let max_x = rsi_series.last().map(|(x, _)| *x).unwrap_or(1.0);

    let overbought = Line::new(PlotPoints::from_iter([[min_x, 70.0], [max_x, 70.0]]))
        .color(egui::Color32::RED)
        .style(LineStyle::Dashed { length: 5.0 })
        .name("Overbought (70)");
    let oversold = Line::new(PlotPoints::from_iter([[min_x, 30.0], [max_x, 30.0]]))
        .color(egui::Color32::GREEN)
        .style(LineStyle::Dashed { length: 5.0 })
        .name("Oversold (30)");

    plot_ui.line(overbought);
    plot_ui.line(oversold);
}

impl PortfolioComponent for ChartsComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        // Scrollable container so content is never clipped
        egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| {
            ui.heading("Price Charts");
            ui.add_space(4.0);

            // Controls
            ui.group(|ui| {
                ui.horizontal_wrapped(|ui| {
                    ui.label("Symbol:");
                    let symbols = portfolio.symbols();
                    if symbols.is_empty() {
                        ui.weak("No symbols available");
                    } else {
                        egui::ComboBox::from_id_salt("charts_symbol_selector")
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
                    }

                    ui.separator();

                    ui.checkbox(&mut self.show_sma20, "SMA 20");
                    ui.checkbox(&mut self.show_ema12, "EMA 12");
                    ui.checkbox(&mut self.show_rsi, "RSI 14");
                });
            });

            ui.add_space(6.0);
            ui.separator();

            if let Some(symbol) = &self.selected_symbol {
                if let Some(price_history) = portfolio.get_price_history(symbol) {
                    if price_history.is_empty() {
                        ui.label("No price history available for this symbol");
                        return;
                    }

                    // Basic stats
                    if let Some(latest) = price_history.last() {
                        ui.horizontal_wrapped(|ui| {
                            ui.strong(format!("{} latest:", symbol));
                            ui.label(format!("Close ${:.2}", latest.close));
                            ui.separator();
                            ui.label(format!("High ${:.2}", latest.high));
                            ui.separator();
                            ui.label(format!("Low ${:.2}", latest.low));
                            ui.separator();
                            ui.label(format!("Vol {}", latest.volume));
                        });
                    }
                    ui.weak(format!("{} data points", price_history.len()));

                    // Build time series
                    let closes: Vec<(f64, f64)> = price_history
                        .iter()
                        .map(|p| (to_unix_secs(p.timestamp), p.close))
                        .collect();

                    let close_vals: Vec<f64> = price_history.iter().map(|p| p.close).collect();

                    // SMA/EMA
                    let sma20_series = if self.show_sma20 && close_vals.len() >= 20 {
                        let s = sma(&close_vals, 20);
                        Some(
                            s.iter()
                                .enumerate()
                                .map(|(i, &v)| (to_unix_secs(price_history[i + 19].timestamp), v))
                                .collect::<Vec<_>>(),
                        )
                    } else {
                        None
                    };

                    let ema12_series = if self.show_ema12 && close_vals.len() >= 12 {
                        let e = ema(&close_vals, 12);
                        Some(
                            e.iter()
                                .enumerate()
                                .map(|(i, &v)| (to_unix_secs(price_history[i + 11].timestamp), v))
                                .collect::<Vec<_>>(),
                        )
                    } else {
                        None
                    };

                    ui.add_space(8.0);
                    ui.heading("Price Trend");

                    // Time-based plot: use seconds since epoch. egui_plot supports auto formatting dates if using custom formatter.
                    Plot::new(format!("price_chart_{}", symbol))
                        .legend(Legend::default())
                        .view_aspect(2.0)
                        .x_axis_formatter(|x, _| {
                            let secs = *x;
                            let ts =
                                UNIX_EPOCH + std::time::Duration::from_secs_f64(secs.max(0.0));
                            let dt: chrono::DateTime<chrono::Utc> =
                                chrono::DateTime::<chrono::Utc>::from(ts);
                            dt.format("%Y-%m-%d").to_string()
                        })
                        .show(ui, |plot_ui| {
                            format_price_chart(plot_ui, &closes, sma20_series, ema12_series);
                        });

                    // Volume chart
                    ui.add_space(8.0);
                    ui.heading("Volume");
                    let volumes: Vec<[f64; 2]> = price_history
                        .iter()
                        .map(|p| [to_unix_secs(p.timestamp), p.volume as f64])
                        .collect();
                    let volume_line = Line::new(PlotPoints::from(volumes))
                        .color(egui::Color32::GRAY)
                        .name("Volume");

                    Plot::new(format!("volume_chart_{}", symbol))
                        .view_aspect(2.0)
                        .x_axis_formatter(|x, _| {
                            let secs = *x;
                            let ts =
                                UNIX_EPOCH + std::time::Duration::from_secs_f64(secs.max(0.0));
                            let dt: chrono::DateTime<chrono::Utc> =
                                chrono::DateTime::<chrono::Utc>::from(ts);
                            dt.format("%Y-%m-%d").to_string()
                        })
                        .show(ui, |plot_ui| {
                            plot_ui.line(volume_line);
                        });

                    // RSI chart
                    if self.show_rsi && close_vals.len() >= 15 {
                        ui.add_space(8.0);
                        ui.heading("RSI (14)");

                        let rsi_vals = rsi(&close_vals, 14);
                        let rsi_series: Vec<(f64, f64)> = rsi_vals
                            .iter()
                            .enumerate()
                            .map(|(i, &v)| (to_unix_secs(price_history[i + 14].timestamp), v))
                            .collect();

                        Plot::new(format!("rsi_chart_{}", symbol))
                            .legend(Legend::default())
                            .view_aspect(2.0)
                            .x_axis_formatter(|x, _| {
                                let secs = *x;
                                let ts = UNIX_EPOCH
                                    + std::time::Duration::from_secs_f64(secs.max(0.0));
                                let dt: chrono::DateTime<chrono::Utc> =
                                    chrono::DateTime::<chrono::Utc>::from(ts);
                                dt.format("%Y-%m-%d").to_string()
                            })
                            .show(ui, |plot_ui| {
                                format_rsi_chart(plot_ui, &rsi_series);
                            });
                    }

                    ui.add_space(8.0);
                    ui.separator();
                    ui.heading("Technical Indicators");
                    ui.label("• Simple Moving Average (SMA)");
                    ui.label("• Exponential Moving Average (EMA)");
                    ui.label("• Relative Strength Index (RSI)");
                    ui.label("• MACD (coming soon)");
                } else {
                    ui.label("No price history available for this symbol");
                    if ui.button("Fetch Price History").clicked() {
                        ui.label("Would fetch price history from backend...");
                    }
                }
            } else {
                ui.label("Select a symbol to view its chart");
                let symbols = portfolio.symbols();
                if !symbols.is_empty() {
                    ui.separator();
                    ui.label("Available symbols:");
                    for symbol in symbols {
                        ui.label(format!("• {}", symbol));
                    }
                }
            }
        });
    }

    fn name(&self) -> &str {
        "Charts"
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
