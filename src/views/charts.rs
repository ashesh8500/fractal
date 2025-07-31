//! Price charts component for technical analysis

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;
use egui_plot::{Line, Plot, Points};

pub struct ChartsComponent {
    is_open: bool,
    selected_symbol: Option<String>,
}

impl ChartsComponent {
    pub fn new() -> Self {
        Self { 
            is_open: false,
            selected_symbol: None,
        }
    }
}

impl PortfolioComponent for ChartsComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        ui.heading("Price Charts");
        
        // Symbol selection
        ui.horizontal(|ui| {
            ui.label("Symbol:");
            
            let symbols = portfolio.symbols();
            if !symbols.is_empty() {
                egui::ComboBox::from_label("")
                    .selected_text(
                        self.selected_symbol
                            .as_ref()
                            .unwrap_or(&"Select symbol".to_string())
                    )
                    .show_ui(ui, |ui| {
                        for symbol in &symbols {
                            ui.selectable_value(&mut self.selected_symbol, Some(symbol.clone()), symbol);
                        }
                    });
            }
        });
        
        ui.separator();
        
        if let Some(symbol) = &self.selected_symbol {
            if let Some(price_history) = portfolio.get_price_history(symbol) {
                ui.heading(&format!("{} Price Chart", symbol));
                
                // Display basic price information
                if let Some(latest) = price_history.last() {
                    ui.label(format!("Latest Price: ${:.2}", latest.close));
                    ui.label(format!("High: ${:.2}", latest.high));
                    ui.label(format!("Low: ${:.2}", latest.low));
                    ui.label(format!("Volume: {}", latest.volume));
                }
                
                ui.label(format!("Price history: {} data points", price_history.len()));
                
                // Render a line chart of closing prices
                if !price_history.is_empty() {
                    ui.separator();
                    ui.heading("Price Trend");
                    
                    // Create a line chart of closing prices
                    let closes: Vec<[f64; 2]> = price_history.iter()
                        .enumerate()
                        .map(|(i, point)| [i as f64, point.close])
                        .collect();
                    
                    let line = Line::new(closes);
                    
                    Plot::new("price_chart")
                        .view_aspect(2.0)
                        .show(ui, |plot_ui| {
                            plot_ui.line(line);
                        });
                    
                    // Render volume bars
                    ui.separator();
                    ui.heading("Volume");
                    
                    let volumes: Vec<[f64; 2]> = price_history.iter()
                        .enumerate()
                        .map(|(i, point)| [i as f64, point.volume as f64])
                        .collect();
                    
                    let volume_points = Points::new(volumes);
                    
                    Plot::new("volume_chart")
                        .view_aspect(2.0)
                        .show(ui, |plot_ui| {
                            plot_ui.points(volume_points);
                        });
                }
                
                // Technical indicators section
                ui.separator();
                ui.heading("Technical Indicators");
                ui.label("📈 Available indicators:");
                ui.label("• Simple Moving Average (SMA)");
                ui.label("• Exponential Moving Average (EMA)");
                ui.label("• Relative Strength Index (RSI)");
                ui.label("• Moving Average Convergence Divergence (MACD)");
            } else {
                ui.label("No price history available for this symbol");
                
                // Suggest fetching data
                if ui.button("Fetch Price History").clicked() {
                    ui.label("Would fetch price history from backend...");
                }
            }
        } else {
            ui.label("Select a symbol to view its chart");
            
            // Show available symbols
            let symbols = portfolio.symbols();
            if !symbols.is_empty() {
                ui.separator();
                ui.label("Available symbols:");
                for symbol in symbols {
                    ui.label(format!("• {}", symbol));
                }
            }
        }
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
