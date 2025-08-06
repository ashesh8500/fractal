use egui::{Color32, Stroke};
use egui_plot::{Line, Plot, PlotPoints};
use crate::components::PortfolioComponent;
use crate::portfolio::Portfolio;
use crate::state::Config;

pub struct ChartsComponent {
    is_open: bool,
    selected_symbol: Option<String>,
    chart_type: ChartType,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum ChartType {
    LineChart,
    CandlestickChart,
}

impl ChartsComponent {
    pub fn new() -> Self {
        Self { 
            is_open: true,
            selected_symbol: None,
            chart_type: ChartType::LineChart,
        }
    }
    
}

impl PortfolioComponent for ChartsComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        // Pre-compute IDs and instance ID outside of closures to avoid borrow conflicts
        let instance_id = self as *const _ as usize;
        let window_id = egui::Id::new(("charts_window", instance_id));
        let symbol_combo_id = egui::Id::new(("charts_symbol_combo", instance_id));
        let chart_type_combo_id = egui::Id::new(("charts_chart_type_combo", instance_id));

        egui::Window::new("Charts")
            .id(window_id)
            .open(&mut self.is_open)
            .default_width(800.0)
            .default_height(500.0)
            .show(ui.ctx(), |ui| {
                ui.heading("Portfolio Charts");
                
                // Get symbols from portfolio holdings
                let symbols: Vec<String> = portfolio.holdings.keys().cloned().collect();
                
                if symbols.is_empty() {
                    ui.label("No holdings available to display charts");
                    return;
                }
                
                // Symbol selector with unique ID
                ui.horizontal(|ui| {
                    ui.label("Select Symbol:");
                    egui::ComboBox::from_id_salt(symbol_combo_id)
                        .selected_text(
                            self.selected_symbol
                                .as_ref()
                                .cloned()
                                .unwrap_or_else(|| "Select Symbol".to_string()),
                        )
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_symbol, None, "Select Symbol");
                            for symbol in &symbols {
                                ui.selectable_value(&mut self.selected_symbol, Some(symbol.clone()), symbol);
                            }
                        });
                });
                
                // Chart type selector
                ui.horizontal(|ui| {
                    ui.label("Chart Type:");
                    egui::ComboBox::from_id_salt(chart_type_combo_id)
                        .selected_text(format!("{:?}", self.chart_type))
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.chart_type, ChartType::LineChart, "Line Chart");
                            ui.selectable_value(&mut self.chart_type, ChartType::CandlestickChart, "Candlestick Chart");
                        });
                });
                
                ui.separator();
                
                // Store symbol clone and chart type to avoid borrow conflicts in render_chart
                let selected_symbol_clone = self.selected_symbol.clone();
                let current_chart_type = self.chart_type;
                
                // Render chart if symbol is selected
                if let Some(ref symbol) = selected_symbol_clone {
                    if let Some(price_data) = portfolio.get_price_history(symbol) {
                        if price_data.is_empty() {
                            ui.label("No price history available for this symbol.");
                            ui.small("Historical data will be loaded automatically when available.");
                            return;
                        }
                        
                        // Render chart inline instead of calling self.render_chart to avoid borrow conflicts
                        match current_chart_type {
                            ChartType::LineChart => {
                                Self::render_line_chart_static(ui, symbol, price_data, instance_id);
                            },
                            ChartType::CandlestickChart => {
                                Self::render_candlestick_chart_static(ui, symbol, price_data, instance_id);
                            },
                        }
                    } else {
                        ui.label("No price history available for this symbol.");
                        ui.small("Historical data will be loaded automatically when available.");
                    }
                } else {
                    ui.label("Select a symbol to view its chart");
                }
            });
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

    fn category(&self) -> crate::components::ComponentCategory {
        crate::components::ComponentCategory::Charts
    }
}

impl ChartsComponent {
    fn render_line_chart_static(ui: &mut egui::Ui, symbol: &str, price_data: &[crate::portfolio::PricePoint], instance_id: usize) {
        // Convert price data to line points using close prices
        let points: Vec<[f64; 2]> = price_data
            .iter()
            .enumerate()
            .map(|(i, point)| [i as f64, point.close])
            .collect();
        
        if points.is_empty() {
            ui.label("No data points to display");
            return;
        }
        
        // Calculate price change
        let price_change = if let (Some(first), Some(last)) = (points.first(), points.last()) {
            let change_pct = ((last[1] - first[1]) / first[1]) * 100.0;
            Some((last[1] - first[1], change_pct))
        } else {
            None
        };
        
        // Show current price and change
        if let Some((abs_change, pct_change)) = price_change {
            ui.horizontal(|ui| {
                ui.label(format!("{}:", symbol));
                ui.label(format!("${:.2}", points.last().unwrap()[1]));
                let color = if abs_change >= 0.0 { Color32::GREEN } else { Color32::RED };
                let sign = if abs_change >= 0.0 { "+" } else { "" };
                ui.colored_label(color, format!("{}{:.2} ({}{:.2}%)", sign, abs_change, sign, pct_change));
            });
        }
        
        // Render the plot with unique ID
        Plot::new(egui::Id::new(("line_chart", symbol, instance_id)))
            .view_aspect(2.0)
            .show(ui, |plot_ui| {
                let color = if price_change.map(|(c, _)| c >= 0.0).unwrap_or(true) {
                    Color32::GREEN
                } else {
                    Color32::RED
                };
                
                plot_ui.line(
                    Line::new(PlotPoints::from(points))
                        .name(format!("{} Close Price", symbol))
                        .color(color)
                        .stroke(Stroke::new(2.0, color)),
                );
            });
    }
    
    fn render_candlestick_chart_static(ui: &mut egui::Ui, symbol: &str, price_data: &[crate::portfolio::PricePoint], instance_id: usize) {
        // For candlestick, we'll use a simplified representation with lines
        // This is a basic implementation - you could enhance with proper candlestick rendering
        
        let mut high_line_points = Vec::new();
        let mut low_line_points = Vec::new();
        let mut close_line_points = Vec::new();
        
        for (i, point) in price_data.iter().enumerate() {
            let x = i as f64;
            high_line_points.push([x, point.high]);
            low_line_points.push([x, point.low]);
            close_line_points.push([x, point.close]);
        }
        
        if close_line_points.is_empty() {
            ui.label("No data points to display");
            return;
        }
        
        // Show current price info
        if let Some(last_point) = price_data.last() {
            ui.horizontal(|ui| {
                ui.label(format!("{}:", symbol));
                ui.label(format!("O: ${:.2}", last_point.open));
                ui.label(format!("H: ${:.2}", last_point.high));
                ui.label(format!("L: ${:.2}", last_point.low));
                ui.label(format!("C: ${:.2}", last_point.close));
                let color = if last_point.close >= last_point.open { Color32::GREEN } else { Color32::RED };
                let change = last_point.close - last_point.open;
                let sign = if change >= 0.0 { "+" } else { "" };
                ui.colored_label(color, format!("({}{:.2})", sign, change));
            });
        }
        
        // Render the plot with unique ID  
        Plot::new(egui::Id::new(("candlestick_chart", symbol, instance_id)))
            .view_aspect(2.0)
            .show(ui, |plot_ui| {
                // High line
                plot_ui.line(
                    Line::new(PlotPoints::from(high_line_points))
                        .name("High")
                        .color(Color32::LIGHT_GREEN)
                        .stroke(Stroke::new(1.0, Color32::LIGHT_GREEN)),
                );
                
                // Low line  
                plot_ui.line(
                    Line::new(PlotPoints::from(low_line_points))
                        .name("Low")
                        .color(Color32::LIGHT_RED)
                        .stroke(Stroke::new(1.0, Color32::LIGHT_RED)),
                );
                
                // Close line (main)
                plot_ui.line(
                    Line::new(PlotPoints::from(close_line_points))
                        .name("Close")
                        .color(Color32::BLUE)
                        .stroke(Stroke::new(2.0, Color32::BLUE)),
                );
            });
    }
}
