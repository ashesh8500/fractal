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
            if let Some(price_history) = &portfolio.price_history {
                if let Some(prices) = price_history.get(symbol) {
                    ui.heading(&format!("{} Price Chart", symbol));
                    
                    // TODO: Implement actual chart rendering
                    // For now, show basic price information
                    if let Some(latest) = prices.last() {
                        ui.label(format!("Latest Price: ${:.2}", latest.close));
                        ui.label(format!("High: ${:.2}", latest.high));
                        ui.label(format!("Low: ${:.2}", latest.low));
                        ui.label(format!("Volume: {}", latest.volume));
                    }
                    
                    ui.label(format!("Price history: {} data points", prices.len()));
                    
                    // Placeholder for chart
                    ui.separator();
                    ui.label("📈 Chart visualization will be implemented here");
                    ui.label("Features to include:");
                    ui.label("• Candlestick charts");
                    ui.label("• Technical indicators (SMA, EMA, RSI, MACD)");
                    ui.label("• Volume bars");
                    ui.label("• Zoom and pan controls");
                    ui.label("• Multiple timeframes");
                } else {
                    ui.label("No price history available for this symbol");
                }
            } else {
                ui.label("No price history data loaded");
            }
        } else {
            ui.label("Select a symbol to view its chart");
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
