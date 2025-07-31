//! Price charts component for technical analysis

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;
use egui_plot::{Line, Plot, PlotPoints, Legend, LineStyle};
use crate::portfolio::indicators::{sma, ema, rsi};

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
                            .cloned()
                            .unwrap_or_else(|| "Select symbol".to_string())
                    )
                    .show_ui(ui, |ui| {
                        for symbol in &symbols {
                            ui.selectable_value(&mut self.selected_symbol, Some(symbol.clone()), symbol);
                        }
                    });
            } else {
                ui.weak("No symbols available");
            }
        });
        
        ui.separator();
        
        if let Some(symbol) = &self.selected_symbol {
            if let Some(price_history) = portfolio.get_price_history(symbol) {
                ui.heading(&format!("{} Price Chart", symbol));
                
                // Display basic price information
                if let Some(latest) = price_history.last() {
                    ui.horizontal(|ui| {
                        ui.label(format!("Latest: ${:.2}", latest.close));
                        ui.separator();
                        ui.label(format!("High: ${:.2}", latest.high));
                        ui.separator();
                        ui.label(format!("Low: ${:.2}", latest.low));
                        ui.separator();
                        ui.label(format!("Volume: {}", latest.volume));
                    });
                }
                
                ui.weak(format!("Price history: {} data points", price_history.len()));
                
                // Render a line chart of closing prices
                if !price_history.is_empty() {
                    ui.separator();
                    ui.heading("Price Trend");
                    
                    // Create a line chart of closing prices
                    let closes: Vec<[f64; 2]> = price_history.iter()
                        .enumerate()
                        .map(|(i, point)| [i as f64, point.close])
                        .collect();
                    
                    let close_prices: Vec<f64> = price_history.iter().map(|p| p.close).collect();
                    
                    let price_line = Line::new(PlotPoints::from(closes))
                        .color(egui::Color32::BLUE)
                        .name("Price");
                    
                    // SMA 20
                    let mut lines = vec![price_line];
                    if close_prices.len() >= 20 {
                        let sma_20 = sma(&close_prices, 20);
                        let sma_points: Vec<[f64; 2]> = sma_20.iter()
                            .enumerate()
                            .map(|(i, &value)| [(i + 19) as f64, value])
                            .collect();
                        
                        lines.push(Line::new(PlotPoints::from(sma_points))
                            .color(egui::Color32::RED)
                            .name("SMA 20"));
                    }
                    
                    // EMA 12
                    if close_prices.len() >= 12 {
                        let ema_12 = ema(&close_prices, 12);
                        let ema_points: Vec<[f64; 2]> = ema_12.iter()
                            .enumerate()
                            .map(|(i, &value)| [(i + 11) as f64, value])
                            .collect();
                        
                        lines.push(Line::new(PlotPoints::from(ema_points))
                            .color(egui::Color32::GREEN)
                            .name("EMA 12"));
                    }
                    
                    Plot::new("price_chart")
                        .view_aspect(2.0)
                        .legend(Legend::default())
                        .show(ui, |plot_ui| {
                            for line in lines {
                                plot_ui.line(line);
                            }
                        });
                    
                    // Render volume as a line
                    ui.separator();
                    ui.heading("Volume");
                    
                    let volumes: Vec<[f64; 2]> = price_history.iter()
                        .enumerate()
                        .map(|(i, point)| [i as f64, point.volume as f64])
                        .collect();
                    
                    let volume_line = Line::new(PlotPoints::from(volumes))
                        .color(egui::Color32::GRAY)
                        .name("Volume");
                    
                    Plot::new("volume_chart")
                        .view_aspect(2.0)
                        .show(ui, |plot_ui| {
                            plot_ui.line(volume_line);
                        });
                    
                    // RSI Chart
                    if close_prices.len() >= 15 {
                        ui.separator();
                        ui.heading("RSI (14)");
                        
                        let rsi_values = rsi(&close_prices, 14);
                        let rsi_points: Vec<[f64; 2]> = rsi_values.iter()
                            .enumerate()
                            .map(|(i, &value)| [(i + 14) as f64, value])
                            .collect();
                        
                        let rsi_line = Line::new(PlotPoints::from(rsi_points))
                            .color(egui::Color32::YELLOW)
                            .name("RSI");
                        
                        // Overbought/oversold lines, dashed
                        let overbought: Vec<[f64; 2]> = (0..rsi_values.len())
                            .map(|i| [(i + 14) as f64, 70.0])
                            .collect();
                        let oversold: Vec<[f64; 2]> = (0..rsi_values.len())
                            .map(|i| [(i + 14) as f64, 30.0])
                            .collect();
                        
                        let overbought_line = Line::new(PlotPoints::from(overbought))
                            .color(egui::Color32::RED)
                            .style(LineStyle::Dashed { length: 5.0 })
                            .name("Overbought (70)");
                        
                        let oversold_line = Line::new(PlotPoints::from(oversold))
                            .color(egui::Color32::GREEN)
                            .style(LineStyle::Dashed { length: 5.0 })
                            .name("Oversold (30)");
                        
                        Plot::new("rsi_chart")
                            .view_aspect(2.0)
                            .legend(Legend::default())
                            .show(ui, |plot_ui| {
                                plot_ui.line(rsi_line);
                                plot_ui.line(overbought_line);
                                plot_ui.line(oversold_line);
                            });
                    }
                }
                
                ui.separator();
                ui.heading("Technical Indicators");
                ui.label("📈 Available indicators:");
                ui.label("• Simple Moving Average (SMA)");
                ui.label("• Exponential Moving Average (EMA)");
                ui.label("• Relative Strength Index (RSI)");
                ui.label("• Moving Average Convergence Divergence (MACD)");
            } else {
                ui.label("No price history available for this symbol");
                
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
