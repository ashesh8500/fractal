use egui::{self, Color32, Ui};
use crate::views::PortfolioComponent;
use crate::portfolio::{Portfolio, Config};
use crate::views::ComponentCategory;

pub struct ChartsComponent {
    is_open: bool,
}

impl ChartsComponent {
    pub fn new() -> Self {
        Self { is_open: true }
    }
}

impl PortfolioComponent for ChartsComponent {
    fn update(&mut self, ui: &mut Ui, portfolio: &mut Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        egui::Window::new("Charts")
            .open(&mut self.is_open)
            .default_width(800.0)
            .show(ui.ctx(), |ui| {
                ui.heading("Portfolio Charts");
                
                // Check if we have data to display
                if portfolio.positions.is_empty() {
                    ui.label("No positions available to display charts");
                    return;
                }

                // Create a simple pie chart of portfolio distribution
                let total_value: f64 = portfolio.positions.values().map(|p| p.value).sum();
                
                if total_value > 0.0 {
                    ui.label(format!("Total Portfolio Value: ${:.2}", total_value));
                    
                    // Pie chart data
                    let mut pie_data = Vec::new();
                    for (symbol, position) in &portfolio.positions {
                        let percentage = (position.value / total_value) * 100.0;
                        pie_data.push((symbol.clone(), percentage, position.value));
                    }
                    
                    // Sort by value descending
                    pie_data.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap());
                    
                    // Render pie chart
                    egui::plot::Plot::new("portfolio_pie_chart")
                        .view_aspect(1.0)
                        .show(ui, |plot_ui| {
                            let mut total = 0.0;
                            for (symbol, percentage, value) in &pie_data {
                                let start_angle = total * 2.0 * std::f64::consts::PI / 100.0;
                                total += percentage;
                                let end_angle = total * 2.0 * std::f64::consts::PI / 100.0;
                                
                                let color = Color32::from_rgb(
                                    (rand::random::<f32>() * 255.0) as u8,
                                    (rand::random::<f32>() * 255.0) as u8,
                                    (rand::random::<f32>() * 255.0) as u8,
                                );
                                
                                plot_ui.circle(
                                    egui::plot::PlotPoint::new(0.0, 0.0),
                                    0.5,
                                    color,
                                    egui::Stroke::new(1.0, Color32::BLACK),
                                );
                            }
                        });
                    
                    // Display data table
                    ui.add_space(10.0);
                    ui.heading("Portfolio Distribution");
                    egui::Grid::new("portfolio_grid").num_columns(3).show(ui, |ui| {
                        ui.label("Symbol");
                        ui.label("Value");
                        ui.label("Percentage");
                        ui.end_row();
                        
                        for (symbol, percentage, value) in &pie_data {
                            ui.label(symbol);
                            ui.label(format!("${:.2}", value));
                            ui.label(format!("{:.2}%", percentage));
                            ui.end_row();
                        }
                    });
                } else {
                    ui.label("No portfolio value to display");
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

    fn category(&self) -> ComponentCategory {
        ComponentCategory::Charts
    }
}
