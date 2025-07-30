use crate::portfolio::Portfolio;
use crate::api::ApiClient;
use crate::components::ComponentManager;
use crate::state::AppState;

/// We derive Deserialize/Serialize so we can persist app state on shutdown.
#[derive(serde::Deserialize, serde::Serialize)]
#[serde(default)] // if we add new fields, give them default values when deserializing old state
pub struct TemplateApp {
    // Original template stuff (preserved):
    label: String,

    #[serde(skip)] // This how you opt-out of serialization of a field
    value: f32,

    // Portfolio functionality (extending template):
    #[serde(skip)]
    app_state: AppState,
    
    #[serde(skip)]
    api_client: ApiClient,
    
    #[serde(skip)]
    component_manager: ComponentManager,
    
    // UI state
    show_portfolio_panel: bool,
    selected_portfolio: Option<String>,
    
    // Connection status
    #[serde(skip)]
    connection_status: ConnectionStatus,
    
    #[serde(skip)]
    test_message: String,
}

#[derive(Debug, Clone)]
enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

impl Default for TemplateApp {
    fn default() -> Self {
        Self {
            // Original template stuff (preserved):
            label: "Hello World!".to_owned(),
            value: 2.7,
            
            // Portfolio functionality:
            app_state: AppState::default(),
            api_client: ApiClient::new("http://localhost:8000/api/v1"),
            component_manager: ComponentManager::new(),
            show_portfolio_panel: false,
            selected_portfolio: None,
            connection_status: ConnectionStatus::Disconnected,
            test_message: "Not tested yet".to_string(),
        }
    }
}

impl TemplateApp {
    /// Called once before the first frame.
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        // This is also where you can customize the look and feel of egui using
        // `cc.egui_ctx.set_visuals` and `cc.egui_ctx.set_fonts`.

        // Load previous app state (if any).
        // Note that you must enable the `persistence` feature for this to work.
        let mut app = if let Some(storage) = cc.storage {
            eframe::get_value(storage, eframe::APP_KEY).unwrap_or_default()
        } else {
            Default::default()
        };
        
        // Initialize non-serializable components
        app.api_client = ApiClient::new("http://localhost:8000/api/v1");
        app.component_manager = ComponentManager::new();
        app.connection_status = ConnectionStatus::Disconnected;
        
        app
    }
    
    /// Test backend connection
    fn test_backend_connection(&mut self, ctx: &egui::Context) {
        if matches!(self.connection_status, ConnectionStatus::Connecting) {
            return; // Already testing
        }
        
        self.connection_status = ConnectionStatus::Connecting;
        self.test_message = "Testing connection...".to_string();
        
        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        
        // Spawn async task to test connection
        tokio::spawn(async move {
            // For now, just test the health endpoint
            match api_client.test_health().await {
                Ok(_) => {
                    // Connection successful - request repaint
                    ctx.request_repaint();
                }
                Err(e) => {
                    log::error!("Backend connection failed: {}", e);
                    ctx.request_repaint();
                }
            }
        });
    }
    
    /// Create a test portfolio
    fn create_test_portfolio(&mut self, ctx: &egui::Context) {
        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        
        tokio::spawn(async move {
            let mut holdings = std::collections::HashMap::new();
            holdings.insert("AAPL".to_string(), 10.0);
            holdings.insert("MSFT".to_string(), 5.0);
            holdings.insert("GOOGL".to_string(), 3.0);
            
            match api_client.create_portfolio("Test Portfolio", holdings).await {
                Ok(portfolio) => {
                    log::info!("Created test portfolio: {}", portfolio.name);
                    ctx.request_repaint();
                }
                Err(e) => {
                    log::error!("Failed to create test portfolio: {}", e);
                    ctx.request_repaint();
                }
            }
        });
    }
    
    /// Render portfolio-specific UI panels
    fn render_portfolio_ui(&mut self, ctx: &egui::Context) {
        // Left panel for portfolio selection and management
        egui::SidePanel::left("portfolio_panel")
            .resizable(true)
            .show_animated(ctx, self.show_portfolio_panel, |ui| {
                ui.heading("Portfolios");
                
                // Connection status
                ui.horizontal(|ui| {
                    let (color, text) = match &self.connection_status {
                        ConnectionStatus::Disconnected => (egui::Color32::RED, "Disconnected"),
                        ConnectionStatus::Connecting => (egui::Color32::YELLOW, "Connecting..."),
                        ConnectionStatus::Connected => (egui::Color32::GREEN, "Connected"),
                        ConnectionStatus::Error(e) => (egui::Color32::RED, e.as_str()),
                    };
                    
                    ui.colored_label(color, "●");
                    ui.label(text);
                });
                
                ui.separator();
                
                // Test connection button
                if ui.button("Test Backend Connection").clicked() {
                    self.test_backend_connection(ctx);
                }
                
                // Create test portfolio button
                if ui.button("Create Test Portfolio").clicked() {
                    self.create_test_portfolio(ctx);
                }
                
                ui.separator();
                
                // Portfolio list and selection
                if let Some(portfolios) = &self.app_state.portfolios {
                    for portfolio_name in portfolios.keys() {
                        let selected = self.selected_portfolio.as_ref() == Some(portfolio_name);
                        if ui.selectable_label(selected, portfolio_name).clicked() {
                            self.selected_portfolio = Some(portfolio_name.clone());
                        }
                    }
                } else {
                    ui.label("No portfolios loaded");
                }
                
                ui.separator();
                ui.label(&self.test_message);
            });
    }
    
    /// Render portfolio components in the central panel
    fn render_portfolio_components(&mut self, ui: &mut egui::Ui) {
        if let Some(portfolio_name) = &self.selected_portfolio {
            if let Some(portfolio) = self.app_state.get_portfolio(portfolio_name) {
                // Render all components with the selected portfolio
                self.component_manager.render_all(ui, portfolio, &self.app_state.config);
            } else {
                ui.label("Portfolio not found");
            }
        } else {
            ui.label("Select a portfolio to view details");
        }
    }
}

impl eframe::App for TemplateApp {
    /// Called by the framework to save state before shutdown.
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(storage, eframe::APP_KEY, self);
    }

    /// Called each time the UI needs repainting, which may be many times per second.
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Put your widgets into a `SidePanel`, `TopBottomPanel`, `CentralPanel`, `Window` or `Area`.
        // For inspiration and more examples, go to https://emilk.github.io/egui

        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            // The top panel is often a good place for a menu bar:

            egui::MenuBar::new().ui(ui, |ui| {
                // NOTE: no File->Quit on web pages!
                let is_web = cfg!(target_arch = "wasm32");
                if !is_web {
                    ui.menu_button("File", |ui| {
                        if ui.button("Quit").clicked() {
                            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                        }
                    });
                    ui.add_space(16.0);
                }
                
                // Portfolio menu
                ui.menu_button("Portfolio", |ui| {
                    if ui.button("Show Portfolio Panel").clicked() {
                        self.show_portfolio_panel = !self.show_portfolio_panel;
                    }
                    if ui.button("Test Backend").clicked() {
                        self.test_backend_connection(ctx);
                    }
                    if ui.button("Load Portfolios").clicked() {
                        // TODO: Load portfolios from API
                    }
                });
                
                ui.add_space(16.0);
                egui::widgets::global_theme_preference_buttons(ui);
            });
        });
        
        // Render portfolio UI panels
        self.render_portfolio_ui(ctx);

        egui::CentralPanel::default().show(ctx, |ui| {
            // The central panel the region left after adding TopPanel's and SidePanel's
            
            // Show original template content if no portfolio is selected
            if self.selected_portfolio.is_none() {
                ui.heading("Portfolio Management System");
                
                // Connection status display
                ui.horizontal(|ui| {
                    let (color, text) = match &self.connection_status {
                        ConnectionStatus::Disconnected => (egui::Color32::RED, "Backend: Disconnected"),
                        ConnectionStatus::Connecting => (egui::Color32::YELLOW, "Backend: Connecting..."),
                        ConnectionStatus::Connected => (egui::Color32::GREEN, "Backend: Connected"),
                        ConnectionStatus::Error(e) => (egui::Color32::RED, e.as_str()),
                    };
                    
                    ui.colored_label(color, "●");
                    ui.label(text);
                });
                
                ui.separator();
                
                // Test buttons
                ui.horizontal(|ui| {
                    if ui.button("Test Backend Connection").clicked() {
                        self.test_backend_connection(ctx);
                    }
                    if ui.button("Create Test Portfolio").clicked() {
                        self.create_test_portfolio(ctx);
                    }
                });
                
                ui.separator();
                
                // Original template content
                ui.horizontal(|ui| {
                    ui.label("Write something: ");
                    ui.text_edit_singleline(&mut self.label);
                });

                ui.add(egui::Slider::new(&mut self.value, 0.0..=10.0).text("value"));
                if ui.button("Increment").clicked() {
                    self.value += 1.0;
                }

                ui.separator();
                
                ui.label("Select 'Portfolio' -> 'Show Portfolio Panel' to get started");
                ui.label(&format!("Test Status: {}", self.test_message));
                
                ui.separator();

                ui.add(egui::github_link_file!(
                    "https://github.com/emilk/eframe_template/blob/main/",
                    "Original template source code."
                ));
            } else {
                // Render portfolio components
                self.render_portfolio_components(ui);
            }

            ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
                powered_by_egui_and_eframe(ui);
                egui::warn_if_debug_build(ui);
            });
        });
    }
}

fn powered_by_egui_and_eframe(ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.spacing_mut().item_spacing.x = 0.0;
        ui.label("Powered by ");
        ui.hyperlink_to("egui", "https://github.com/emilk/egui");
        ui.label(" and ");
        ui.hyperlink_to(
            "eframe",
            "https://github.com/emilk/egui/tree/master/crates/eframe",
        );
        ui.label(".");
    });
}
