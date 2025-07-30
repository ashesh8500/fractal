//! Portfolio overview dashboard component

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;

pub struct DashboardComponent {
    is_open: bool,
}

impl DashboardComponent {
    pub fn new() -> Self {
        Self { is_open: true }
    }
}

impl PortfolioComponent for DashboardComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        ui.heading(&format!("Portfolio: {}", portfolio.name));
        
        // Portfolio overview metrics
        ui.separator();
        
        egui::Grid::new("portfolio_overview")
            .num_columns(2)
            .spacing([40.0, 4.0])
            .show(ui, |ui| {
                ui.label("Total Value:");
                ui.label(format!("${:.2}", portfolio.total_value));
                ui.end_row();
                
                ui.label("Holdings:");
                ui.label(format!("{} positions", portfolio.holdings.len()));
                ui.end_row();
                
                ui.label("Data Provider:");
                ui.label(&portfolio.data_provider);
                ui.end_row();
                
                ui.label("Last Updated:");
                ui.label(portfolio.last_updated.format("%Y-%m-%d %H:%M UTC").to_string());
                ui.end_row();
            });
        
        ui.separator();
        
        // Risk metrics
        ui.heading("Risk Metrics");
        egui::Grid::new("risk_metrics")
            .num_columns(2)
            .spacing([40.0, 4.0])
            .show(ui, |ui| {
                ui.label("Volatility:");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.volatility * 100.0));
                ui.end_row();
                
                ui.label("Sharpe Ratio:");
                ui.label(format!("{:.2}", portfolio.risk_metrics.sharpe_ratio));
                ui.end_row();
                
                ui.label("Max Drawdown:");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.max_drawdown * 100.0));
                ui.end_row();
                
                ui.label("VaR (95%):");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.var_95 * 100.0));
                ui.end_row();
            });
        
        ui.separator();
        
        // Performance metrics
        ui.heading("Performance Metrics");
        egui::Grid::new("performance_metrics")
            .num_columns(2)
            .spacing([40.0, 4.0])
            .show(ui, |ui| {
                ui.label("Total Return:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.total_return * 100.0));
                ui.end_row();
                
                ui.label("Annualized Return:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.annualized_return * 100.0));
                ui.end_row();
                
                ui.label("Alpha:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.alpha * 100.0));
                ui.end_row();
                
                ui.label("Beta:");
                ui.label(format!("{:.2}", portfolio.performance_metrics.beta));
                ui.end_row();
            });
        
        // Holdings breakdown
        if !portfolio.holdings.is_empty() {
            ui.separator();
            ui.heading("Holdings");
            
            for (symbol, shares) in &portfolio.holdings {
                ui.horizontal(|ui| {
                    ui.label(symbol);
                    ui.label(format!("{:.2} shares", shares));
                    
                    if let Some(weight) = portfolio.current_weights.get(symbol) {
                        ui.label(format!("({:.1}%)", weight * 100.0));
                    }
                    
                    if let Some(position_value) = portfolio.get_position_value(symbol) {
                        ui.label(format!("${:.2}", position_value));
                    }
                });
            }
        }
    }
    
    fn name(&self) -> &str {
        "Dashboard"
    }
    
    fn is_open(&self) -> bool {
        self.is_open
    }
    
    fn set_open(&mut self, open: bool) {
        self.is_open = open;
    }
    
    fn category(&self) -> ComponentCategory {
        ComponentCategory::General
    }
}
