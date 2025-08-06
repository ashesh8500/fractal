#![allow(elided_lifetimes_in_paths)]
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
        let base_id = ui.id().with("component::dashboard::content");
        ui.heading(&format!("Portfolio: {}", portfolio.name));
        
        ui.add_space(4.0);
        ui.separator();
        
        egui::Grid::new(base_id.with(("dashboard", "portfolio_overview")))
            .num_columns(2)
            .spacing([40.0, 6.0])
            .striped(true)
            .show(ui, |ui| {
                ui.strong("Total Value:");
                ui.label(format!("${:.2}", portfolio.total_value))
                    .on_hover_text("Sum of all position values using current weights and total value.");
                ui.end_row();
                
                ui.strong("Holdings:");
                ui.label(format!("{} positions", portfolio.holdings.len()));
                ui.end_row();
                
                ui.strong("Data Provider:");
                ui.label(&portfolio.data_provider);
                ui.end_row();
                
                ui.strong("Last Updated:");
                ui.label(portfolio.last_updated.format("%Y-%m-%d %H:%M UTC").to_string());
                ui.end_row();
            });
        
        ui.separator();
        ui.heading("Risk Metrics");
        egui::Grid::new(base_id.with(("dashboard", "risk_metrics")))
            .num_columns(2)
            .spacing([40.0, 6.0])
            .striped(true)
            .show(ui, |ui| {
                ui.strong("Volatility:");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.volatility * 100.0))
                    .on_hover_text("Standard deviation of returns (annualized).");
                ui.end_row();
                
                ui.strong("Sharpe Ratio:");
                ui.label(format!("{:.2}", portfolio.risk_metrics.sharpe_ratio))
                    .on_hover_text("Risk-adjusted return relative to risk-free rate.");
                ui.end_row();
                
                ui.strong("Max Drawdown:");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.max_drawdown * 100.0));
                ui.end_row();
                
                ui.strong("VaR (95%):");
                ui.label(format!("{:.2}%", portfolio.risk_metrics.var_95 * 100.0));
                ui.end_row();
            });
        
        ui.separator();
        ui.heading("Performance Metrics");
        egui::Grid::new(base_id.with(("dashboard", "performance_metrics")))
            .num_columns(2)
            .spacing([40.0, 6.0])
            .striped(true)
            .show(ui, |ui| {
                ui.strong("Total Return:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.total_return * 100.0));
                ui.end_row();
                
                ui.strong("Annualized Return:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.annualized_return * 100.0));
                ui.end_row();
                
                ui.strong("Alpha:");
                ui.label(format!("{:.2}%", portfolio.performance_metrics.alpha * 100.0));
                ui.end_row();
                
                ui.strong("Beta:");
                ui.label(format!("{:.2}", portfolio.performance_metrics.beta));
                ui.end_row();
            });
        
        if !portfolio.holdings.is_empty() {
            ui.separator();
            ui.heading("Holdings");
            
            egui::ScrollArea::vertical().max_height(220.0).show(ui, |ui| {
                for (symbol, shares) in &portfolio.holdings {
                    ui.horizontal(|ui| {
                        ui.monospace(symbol);
                        ui.label(format!("{:.2} shares", shares));
                        
                        if let Some(weight) = portfolio.current_weights.get(symbol) {
                            ui.weak(format!("({:.1}%)", weight * 100.0));
                        }
                        
                        if let Some(position_value) = portfolio.get_position_value(symbol) {
                            ui.label(format!("${:.2}", position_value));
                        }
                    });
                }
            });
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
