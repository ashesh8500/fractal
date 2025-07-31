//! Candlestick charts component for detailed price analysis

use crate::components::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;
use egui_plot::{Bar, BarChart, Plot, PlotPoints, Line};

pub struct CandlesComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    timeframe: Timeframe,
}

#[derive(Debug, Clone, PartialEq)]
enum Timeframe {
    Daily,
    Weekly,
    Monthly,
}

impl CandlesComponent {
    pub fn new() -> Self {
        Self { 
            is_open: false,
            selected_symbol: None,
            timeframe: Timeframe::Daily,
        }
    }
}

impl PortfolioComponent for CandlesComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        ui.heading("Candlestick Charts");
        
        // Controls
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
            
            ui.separator();
            
            ui.label("Timeframe:");
            egui::ComboBox::from_label("")
                .selected_text(format!("{:?}", self.timeframe))
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.timeframe, Timeframe::Daily, "Daily");
                    ui.selectable_value(&mut self.timeframe, Timeframe::Weekly, "Weekly");
                    ui.selectable_value(&mut self.timeframe, Timeframe::Monthly, "Monthly");
                });
        });
        
        ui.separator();
        
        if let Some(symbol) = &self.selected_symbol {
            if let Some(price_history) = &portfolio.price_history {
                if let Some(prices) = price_history.get(symbol) {
                    ui.heading(&format!("{} Candlestick Chart ({:?})", symbol, self.timeframe));
                    
                    // Show basic OHLC data
                    if let Some(latest) = prices.last() {
                        ui.horizontal(|ui| {
                            ui.label(format!("Open: ${:.2}", latest.open));
                            ui.separator();
                            ui.label(format!("High: ${:.2}", latest.high));
                            ui.separator();
                            ui.label(format!("Low: ${:.2}", latest.low));
                            ui.separator();
                            ui.label(format!("Close: ${:.2}", latest.close));
                            ui.separator();
                            ui.label(format!("Volume: {}", latest.volume));
                        });
                    }
                    
                    ui.separator();
                    
                    // Render candlestick chart
                    if !prices.is_empty() {
                        let data_points = prices.len().min(100); // Limit for performance
                        let start_idx = if prices.len() > data_points { 
                            prices.len() - data_points 
                        } else { 
                            0 
                        };
                        
                        // Create candlestick visualization using multiple elements
                        let mut high_low_bars = Vec::new();
                        let mut body_bars = Vec::new();
                        
                        for (i, price) in prices[start_idx..].iter().enumerate() {
                            let x = i as f64;
                            
                            // High-Low line (thin bar)
                            let hl_height = price.high - price.low;
                            high_low_bars.push(
                                Bar::new(x, hl_height)
                                    .base(price.low)
                                    .width(0.1)
                                    .vertical()
                                    .fill(egui::Color32::GRAY)
                            );
                            
                            // Body (thick bar)
                            let body_height = (price.close - price.open).abs();
                            let body_base = price.open.min(price.close);
                            let body_color = if price.close >= price.open {
                                egui::Color32::from_rgb(0, 150, 0) // Green for bullish
                            } else {
                                egui::Color32::from_rgb(150, 0, 0) // Red for bearish
                            };
                            
                            body_bars.push(
                                Bar::new(x, body_height)
                                    .base(body_base)
                                    .width(0.6)
                                    .vertical()
                                    .fill(body_color)
                            );
                        }
                        
                        let hl_chart = BarChart::new(high_low_bars).name("High-Low");
                        let body_chart = BarChart::new(body_bars).name("Body");
                        
                        Plot::new("candlestick_chart")
                            .view_aspect(2.0)
                            .legend(egui_plot::Legend::default())
                            .show(ui, |plot_ui| {
                                plot_ui.bar_chart(hl_chart);
                                plot_ui.bar_chart(body_chart);
                            });
                        
                        // Render volume bars below price chart
                        ui.separator();
                        ui.heading("Volume");
                        
                        let volumes: Vec<Bar> = prices.iter()
                            .take(50)
                            .enumerate()
                            .map(|(i, price)| {
                                Bar::new(i as f64, price.volume as f64)
                                    .vertical()
                                    .name(format!("Volume {}", i))
                                    .fill(egui::Color32::BLUE)
                            })
                            .collect();
                        
                        let volume_chart = BarChart::new(volumes)
                            .width(0.8)
                            .name("Volume");
                        
                        Plot::new("volume_chart")
                            .view_aspect(2.0)
                            .show(ui, |plot_ui| {
                                plot_ui.bar_chart(volume_chart);
                            });
                    }
                    
                    // Show data summary
                    ui.separator();
                    ui.label(format!("Data points: {}", prices.len()));
                    
                    if prices.len() > 1 {
                        let first = &prices[0];
                        let last = &prices[prices.len() - 1];
                        let change = ((last.close - first.close) / first.close) * 100.0;
                        let change_color = if change >= 0.0 { 
                            egui::Color32::GREEN 
                        } else { 
                            egui::Color32::RED 
                        };
                        
                        ui.horizontal(|ui| {
                            ui.label("Period change:");
                            ui.colored_label(change_color, format!("{:.2}%", change));
                        });
                    }
                } else {
                    ui.label("No price history available for this symbol");
                }
            } else {
                ui.label("No price history data loaded");
            }
        } else {
            ui.label("Select a symbol to view its candlestick chart");
        }
    }
    
    fn name(&self) -> &str {
        "Candles"
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
