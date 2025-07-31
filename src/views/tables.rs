//! Tables component for detailed data display

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;

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
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        ui.heading("Data Tables");
        
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
            
            egui_extras::TableBuilder::new(ui)
                .striped(true)
                .resizable(true)
                .column(egui_extras::Column::auto())
                .column(egui_extras::Column::auto())
                .column(egui_extras::Column::auto())
                .column(egui_extras::Column::remainder())
                .min_scrolled_height(0.0)
                .body(|mut body| {
                    let text_height = egui::TextStyle::Body.resolve(ui.style()).size.max(ui.spacing().interact_size.y);
                    // Header
                    body.row(22.0, |mut row| {
                        row.col(|ui| ui.strong("Symbol"));
                        row.col(|ui| ui.strong("Shares"));
                        row.col(|ui| ui.strong("Weight"));
                        row.col(|ui| ui.strong("Value"));
                    });
                    // Data
                    for (symbol, shares) in &portfolio.holdings {
                        body.row(text_height, |mut row| {
                            row.col(|ui| ui.monospace(symbol));
                            row.col(|ui| ui.label(format!("{:.2}", shares)));
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
                ui.label(format!("Trades executed: {}", backtest_results.trades_executed));
                ui.weak("Trade history will be displayed here");
            } else {
                ui.label("No trade data available");
            }
            
            ui.separator();
        }
        
        // Metrics table
        if self.show_metrics {
            ui.heading("All Metrics");
            
            egui_extras::TableBuilder::new(ui)
                .striped(true)
                .resizable(true)
                .column(egui_extras::Column::auto())
                .column(egui_extras::Column::remainder())
                .body(|mut body| {
                    let row_height = 22.0;
                    let row = |mut body: egui_extras::TableBody, k: &str, v: String| {
                        body.row(row_height, |mut r| {
                            r.col(|ui| ui.strong(k));
                            r.col(|ui| ui.label(v));
                        });
                    };
                    row(body.borrow_mut(), "Volatility", format!("{:.2}%", portfolio.risk_metrics.volatility * 100.0));
                    row(body.borrow_mut(), "Sharpe Ratio", format!("{:.2}", portfolio.risk_metrics.sharpe_ratio));
                    row(body.borrow_mut(), "Max Drawdown", format!("{:.2}%", portfolio.risk_metrics.max_drawdown * 100.0));
                    row(body.borrow_mut(), "VaR (95%)", format!("{:.2}%", portfolio.risk_metrics.var_95 * 100.0));

                    row(body.borrow_mut(), "Total Return", format!("{:.2}%", portfolio.performance_metrics.total_return * 100.0));
                    row(body.borrow_mut(), "Annualized Return", format!("{:.2}%", portfolio.performance_metrics.annualized_return * 100.0));
                    row(body.borrow_mut(), "Alpha", format!("{:.2}%", portfolio.performance_metrics.alpha * 100.0));
                    row(body.borrow_mut(), "Beta", format!("{:.2}", portfolio.performance_metrics.beta));
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
