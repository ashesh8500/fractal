#![allow(elided_lifetimes_in_paths)]
//! Tables component for detailed data display

use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::Portfolio;
use crate::state::Config;
use egui_extras::{Column, TableBuilder};

pub struct TablesComponent {
    is_open: bool,
    show_holdings: bool,
    show_trades: bool,
    show_metrics: bool,
}

impl TablesComponent {
    pub fn new() -> Self {
        Self {
            is_open: false,
            show_holdings: true,
            show_trades: false,
            show_metrics: false,
        }
    }
}

impl PortfolioComponent for TablesComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config) {
        let _base_id = ui.id().with("component::tables::content");
        ui.heading("Data Tables");

        // Provider status header
        ui.group(|ui| {
            ui.horizontal(|ui| {
                let mode = if config.use_native_provider {
                    "Native (Alpha Vantage)"
                } else {
                    "Backend"
                };
                ui.strong("Provider Mode:");
                ui.label(mode);

                ui.separator();

                if config.use_native_provider {
                    let key_status = if config
                        .alphavantage_api_key
                        .as_deref()
                        .unwrap_or("")
                        .is_empty()
                    {
                        ("API key: MISSING", egui::Color32::RED)
                    } else {
                        ("API key: OK", egui::Color32::GREEN)
                    };
                    ui.colored_label(key_status.1, key_status.0);
                }
            });
        });

        ui.separator();

        // Table selection
        ui.horizontal(|ui| {
            ui.checkbox(&mut self.show_holdings, "Holdings");
            ui.checkbox(&mut self.show_trades, "Trades");
            ui.checkbox(&mut self.show_metrics, "Metrics");
        });

        ui.separator();

        // Holdings table
        if self.show_holdings {
            ui.heading("Holdings");

            // Pre-compute row height using the outer UI before handing `ui` to the table builder
            let text_height = {
                let style = ui.style();
                egui::TextStyle::Body
                    .resolve(style)
                    .size
                    .max(ui.spacing().interact_size.y)
            };

            TableBuilder::new(ui)
                // .id(...) is not available in egui_extras::TableBuilder for this version
                .striped(true)
                .resizable(true)
                .column(Column::auto()) // Symbol
                .column(Column::auto()) // Shares
                .column(Column::auto()) // Weight
                .column(Column::remainder()) // Value
                .min_scrolled_height(0.0)
                .body(|mut body| {
                    // Header
                    body.row(22.0, |mut row| {
                        row.col(|ui| {
                            ui.strong("Symbol");
                        });
                        row.col(|ui| {
                            ui.strong("Shares");
                        });
                        row.col(|ui| {
                            ui.strong("Weight");
                        });
                        row.col(|ui| {
                            ui.strong("Value");
                        });
                    });
                    // Data
                    for (symbol, shares) in &portfolio.holdings {
                        body.row(text_height, |mut row| {
                            row.col(|ui| {
                                ui.monospace(symbol);
                            });
                            row.col(|ui| {
                                ui.label(format!("{:.2}", shares));
                            });
                            row.col(|ui| {
                                if let Some(weight) = portfolio.current_weights.get(symbol) {
                                    ui.label(format!("{:.1}%", weight * 100.0));
                                } else {
                                    ui.weak("N/A");
                                }
                            });
                            row.col(|ui| {
                                if let Some(value) = portfolio.get_position_value(symbol) {
                                    ui.label(format!("${:.2}", value));
                                } else {
                                    ui.weak("N/A");
                                }
                            });
                        });
                    }
                });

            ui.separator();
        }

        // Trades table
        if self.show_trades {
            ui.heading("Recent Trades");

            if let Some(backtest_results) = &portfolio.backtest_results {
                ui.label(format!(
                    "Trades executed: {}",
                    backtest_results.trades_executed
                ));
                ui.weak("Trade history will be displayed here");
            } else {
                ui.label("No trade data available");
            }

            ui.separator();
        }

        // Metrics table
        if self.show_metrics {
            ui.heading("All Metrics");

            TableBuilder::new(ui)
                // .id(...) is not available in egui_extras::TableBuilder for this version
                .striped(true)
                .resizable(true)
                .column(Column::auto())
                .column(Column::remainder())
                .body(|mut body| {
                    let row_height = 22.0;

                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Volatility");
                        });
                        row.col(|ui| {
                            ui.label(format!("{:.2}%", portfolio.risk_metrics.volatility * 100.0));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Sharpe Ratio");
                        });
                        row.col(|ui| {
                            ui.label(format!("{:.2}", portfolio.risk_metrics.sharpe_ratio));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Max Drawdown");
                        });
                        row.col(|ui| {
                            ui.label(format!(
                                "{:.2}%",
                                portfolio.risk_metrics.max_drawdown * 100.0
                            ));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("VaR (95%)");
                        });
                        row.col(|ui| {
                            ui.label(format!("{:.2}%", portfolio.risk_metrics.var_95 * 100.0));
                        });
                    });

                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Total Return");
                        });
                        row.col(|ui| {
                            ui.label(format!(
                                "{:.2}%",
                                portfolio.performance_metrics.total_return * 100.0
                            ));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Annualized Return");
                        });
                        row.col(|ui| {
                            ui.label(format!(
                                "{:.2}%",
                                portfolio.performance_metrics.annualized_return * 100.0
                            ));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Alpha");
                        });
                        row.col(|ui| {
                            ui.label(format!(
                                "{:.2}%",
                                portfolio.performance_metrics.alpha * 100.0
                            ));
                        });
                    });
                    body.row(row_height, |mut row| {
                        row.col(|ui| {
                            ui.strong("Beta");
                        });
                        row.col(|ui| {
                            ui.label(format!("{:.2}", portfolio.performance_metrics.beta));
                        });
                    });
                });
        }
    }

    fn name(&self) -> &str {
        "Tables"
    }

    fn is_open(&self) -> bool {
        self.is_open
    }

    fn set_open(&mut self, open: bool) {
        self.is_open = open;
    }

    fn category(&self) -> ComponentCategory {
        ComponentCategory::Tables
    }
}
