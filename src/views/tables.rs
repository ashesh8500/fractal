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
            
            egui::ScrollArea::vertical()
                .max_height(200.0)
                .show(ui, |ui| {
                    egui::Grid::new("holdings_table")
                        .striped(true)
                        .num_columns(4)
                        .show(ui, |ui| {
                            // Header
                            ui.strong("Symbol");
                            ui.strong("Shares");
                            ui.strong("Weight");
                            ui.strong("Value");
                            ui.end_row();
                            
                            // Data rows
                            for (symbol, shares) in &portfolio.holdings {
                                ui.label(symbol);
                                ui.label(format!("{:.2}", shares));
                                
                                if let Some(weight) = portfolio.current_weights.get(symbol) {
                                    ui.label(format!("{:.1}%", weight * 100.0));
                                } else {
                                    ui.label("N/A");
                                }
                                
                                if let Some(value) = portfolio.get_position_value(symbol) {
                                    ui.label(format!("${:.2}", value));
                                } else {
                                    ui.label("N/A");
                                }
                                
                                ui.end_row();
                            }
                        });
                });
            
            ui.separator();
        }
        
        // Trades table
        if self.show_trades {
            ui.heading("Recent Trades");
            
            if let Some(backtest_results) = &portfolio.backtest_results {
                ui.label(format!("Trades executed: {}", backtest_results.trades_executed));
                // TODO: Show actual trade details when available
                ui.label("Trade history will be displayed here");
            } else {
                ui.label("No trade data available");
            }
            
            ui.separator();
        }
        
        // Metrics table
        if self.show_metrics {
            ui.heading("All Metrics");
            
            egui::Grid::new("metrics_table")
                .striped(true)
                .num_columns(2)
                .show(ui, |ui| {
                    ui.strong("Metric");
                    ui.strong("Value");
                    ui.end_row();
                    
                    // Risk metrics
                    ui.label("Volatility");
                    ui.label(format!("{:.2}%", portfolio.risk_metrics.volatility * 100.0));
                    ui.end_row();
                    
                    ui.label("Sharpe Ratio");
                    ui.label(format!("{:.2}", portfolio.risk_metrics.sharpe_ratio));
                    ui.end_row();
                    
                    ui.label("Max Drawdown");
                    ui.label(format!("{:.2}%", portfolio.risk_metrics.max_drawdown * 100.0));
                    ui.end_row();
                    
                    ui.label("VaR (95%)");
                    ui.label(format!("{:.2}%", portfolio.risk_metrics.var_95 * 100.0));
                    ui.end_row();
                    
                    // Performance metrics
                    ui.label("Total Return");
                    ui.label(format!("{:.2}%", portfolio.performance_metrics.total_return * 100.0));
                    ui.end_row();
                    
                    ui.label("Annualized Return");
                    ui.label(format!("{:.2}%", portfolio.performance_metrics.annualized_return * 100.0));
                    ui.end_row();
                    
                    ui.label("Alpha");
                    ui.label(format!("{:.2}%", portfolio.performance_metrics.alpha * 100.0));
                    ui.end_row();
                    
                    ui.label("Beta");
                    ui.label(format!("{:.2}", portfolio.performance_metrics.beta));
                    ui.end_row();
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
