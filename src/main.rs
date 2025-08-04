use eframe::egui;
use portfolio_tracker::{Portfolio, Config};
use portfolio_tracker::views::{DashboardComponent, ChartsComponent, TablesComponent, CandlesComponent};

fn main() -> eframe::Result {
    let portfolio = Portfolio::new();
    let config = Config::default();
    
    eframe::run_native(
        "Portfolio Tracker",
        eframe::NativeOptions::default(),
        Box::new(|cc| {
            egui_extras::install_image_loaders(&cc.egui_ctx);
            Box::new(App::new(portfolio, config))
        }),
    )
}

struct App {
    portfolio: Portfolio,
    config: Config,
    dashboard: DashboardComponent,
    charts: ChartsComponent,
    tables: TablesComponent,
    candles: CandlesComponent,
}

impl App {
    fn new(portfolio: Portfolio, config: Config) -> Self {
        Self {
            portfolio,
            config,
            dashboard: DashboardComponent::new(),
            charts: ChartsComponent::new(),
            tables: TablesComponent::new(),
            candles: CandlesComponent::new(),
        }
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            // Main layout with tabs
            egui::TopBottomPanel::top("top_bar").show(ui.ctx(), |ui| {
                ui.horizontal(|ui| {
                    ui.label("Portfolio Tracker");
                });
            });

            egui::SidePanel::left("side_panel").show(ui.ctx(), |ui| {
                ui.heading("Components");
                ui.separator();
                
                // Component toggles
                ui.checkbox(&mut self.dashboard.is_open, "Dashboard");
                ui.checkbox(&mut self.charts.is_open, "Charts");
                ui.checkbox(&mut self.tables.is_open, "Tables");
                ui.checkbox(&mut self.candles.is_open, "Candles");
            });

            egui::CentralPanel::default().show(ui.ctx(), |ui| {
                // Show components based on their open state
                if self.dashboard.is_open {
                    self.dashboard.update(ui, &mut self.portfolio, &self.config);
                }
                
                if self.charts.is_open {
                    self.charts.update(ui, &mut self.portfolio, &self.config);
                }
                
                if self.tables.is_open {
                    self.tables.update(ui, &mut self.portfolio, &self.config);
                }
                
                if self.candles.is_open {
                    self.candles.update(ui, &mut self.portfolio, &self.config);
                }
            });
        });
    }
}
