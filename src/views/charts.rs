//! Price charts component for technical analysis

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;

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
                
                // Render a simple line chart of closing prices
                if !price_history.is_empty() {
                    ui.separator();
                    ui.heading("Price Trend");
                    
                    // Create a simple plot of closing prices
                    let closes: Vec<f64> = price_history.iter()
                        .map(|point| point.close)
                        .collect();
                    
                    if !closes.is_empty() {
                        // Simple line chart using egui_plot functionality
                        use egui_plot::{Line, Plot};
                        
                        let points: Vec<[f64; 2]> = closes.iter()
                            .enumerate()
                            .map(|(i, &value)| [i as f64, value])
                            .collect();
                        
                        let line = Line::new("Close Price", points);
                        
                        Plot::new("price_chart")
                            .view_aspect(2.0)
                            .show(ui, |plot_ui| {
                                plot_ui.line(line);
                            });
                    }
                }
                
                // Placeholder for more advanced chart features
                ui.separator();
                ui.label("📈 Advanced chart features:");
                ui.label("• Candlestick charts");
                ui.label("• Technical indicators (SMA, EMA, RSI, MACD)");
                ui.label("• Volume bars");
                ui.label("• Zoom and pan controls");
                ui.label("• Multiple timeframes");
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
