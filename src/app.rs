use crate::api::ApiClient;
use crate::components::ComponentManager;
use crate::state::AppState;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

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
    pub app_state: AppState,

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

    // Shared state for async operations
    #[serde(skip)]
    async_state: Arc<Mutex<AsyncState>>,

    // Small demo toggles inspired by egui demo windows
    show_status_window: bool,

    // Symbols queued to fetch price history for (drives frontend fetching)
    #[serde(skip)]
    fetch_queue: Arc<Mutex<Vec<String>>>,

    // Limit of items rendered in the left portfolio panel for performance/usability
    panel_render_limit: usize,

    // Track last selected portfolio to auto-fetch history on selection change
    #[serde(skip)]
    last_selected_portfolio: Option<String>,

    // Show last error briefly in the side panel
    #[serde(skip)]
    last_error_message: Option<String>,
    
    // Portfolio marked for deletion (handled in update loop)
    #[serde(skip)]
    portfolio_to_delete: Option<String>,
}

#[derive(Debug, Clone)]
enum ConnectionStatus {
    Disconnected,
    Connecting,
    Connected,
    Error(String),
}

#[derive(Debug, Default)]
pub struct AsyncState {
    pub connection_result: Option<Result<(), String>>,
    pub portfolio_result: Option<Result<String, String>>,
    pub portfolios_result: Option<Result<Vec<crate::portfolio::Portfolio>, String>>,
    // symbol -> price history loaded
    pub price_history_results: Vec<(String, Result<Vec<crate::portfolio::PricePoint>, String>)>,
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
            show_portfolio_panel: true, // Enable by default
            selected_portfolio: None,
            connection_status: ConnectionStatus::Disconnected,
            test_message: "Not tested yet".to_string(),
            async_state: Arc::new(Mutex::new(AsyncState::default())),
            show_status_window: false,
            fetch_queue: Arc::new(Mutex::new(Vec::new())),
            // keep left panel tame by default (shows first N items and a "show more" toggle)
            panel_render_limit: 30,
            last_selected_portfolio: None,
            last_error_message: None,
            portfolio_to_delete: None,
        }
    }
}

impl TemplateApp {
    /// Called once before the first frame.
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        // This is also where you can customize the look and feel of egui using
        // `cc.egui_ctx.set_visuals` and `cc.egui_ctx.set_fonts`.

        // Make egui_extras loaders available
        egui_extras::install_image_loaders(&cc.egui_ctx);

        // Load previous app state (if any).
        // Note that you must enable the `persistence` feature for this to work.
        let mut app: Self = if let Some(storage) = cc.storage {
            eframe::get_value(storage, eframe::APP_KEY).unwrap_or_default()
        } else {
            Default::default()
        };

        // Initialize non-serializable components
        let use_native = app.app_state.config.use_native_provider;
        let key = app.app_state.config.alphavantage_api_key.clone();
        app.api_client = ApiClient::new(&app.app_state.config.api_base_url)
            .with_native(use_native, key);
        app.component_manager = ComponentManager::new();
        app.connection_status = ConnectionStatus::Disconnected;
        app.async_state = Arc::new(Mutex::new(AsyncState::default()));
        // fetch_queue is not an Option; it is always present. Ensure it is.
        app.fetch_queue = Arc::new(Mutex::new(Vec::new()));

        // If no portfolios exist and we're in native mode, create a quick demo portfolio to enable charts
        if app.app_state.portfolios.is_none() && app.app_state.config.use_native_provider {
            let mut demo = crate::portfolio::Portfolio::new("Demo".to_string());
            demo.holdings.insert("AAPL".to_string(), 10.0);
            demo.holdings.insert("MSFT".to_string(), 5.0);
            demo.holdings.insert("GOOGL".to_string(), 3.0);
            if app.app_state.portfolios.is_none() {
                app.app_state.portfolios = Some(std::collections::HashMap::new());
            }
            if let Some(pmap) = &mut app.app_state.portfolios {
                pmap.insert(demo.name.clone(), demo);
            }
            app.selected_portfolio = Some("Demo".to_string());
        }

        app
    }

    // Helper methods for UI functionality
    fn handle_async_results(&mut self) {
        // Process async operation results
        if let Ok(mut state) = self.async_state.try_lock() {
            // Handle connection results
            if let Some(result) = state.connection_result.take() {
                match result {
                    Ok(()) => {
                        self.connection_status = ConnectionStatus::Connected;
                        self.test_message = "Connection successful".to_string();
                    }
                    Err(e) => {
                        self.connection_status = ConnectionStatus::Error(e.clone());
                        self.test_message = format!("Connection failed: {}", e);
                        self.last_error_message = Some(e);
                    }
                }
            }

            // Handle portfolio results
            if let Some(result) = state.portfolio_result.take() {
                match result {
                    Ok(message) => {
                        self.test_message = message;
                    }
                    Err(e) => {
                        self.last_error_message = Some(e.clone());
                        self.test_message = format!("Portfolio operation failed: {}", e);
                    }
                }
            }

            // Handle price history results  
            for (symbol, result) in state.price_history_results.drain(..) {
                if let Some(portfolios) = &mut self.app_state.portfolios {
                    if let Some(selected_name) = &self.selected_portfolio {
                        if let Some(portfolio) = portfolios.get_mut(selected_name) {
                            match result {
                                Ok(price_points) => {
                                    let mut history_map = HashMap::new();
                                    history_map.insert(symbol.clone(), price_points);
                                    portfolio.update_price_history(history_map);
                                }
                                Err(e) => {
                                    self.last_error_message = Some(format!("Failed to load price history for {}: {}", symbol, e));
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn process_fetch_queue(&mut self, ctx: &egui::Context) {
        if let Ok(mut queue) = self.fetch_queue.try_lock() {
            if !queue.is_empty() {
                let symbols_to_fetch: Vec<String> = queue.drain(..).collect();
                for symbol in symbols_to_fetch {
                    self.fetch_price_history_async(symbol, ctx);
                }
            }
        }
    }

    fn handle_portfolio_selection_change(&mut self) {
        if self.selected_portfolio != self.last_selected_portfolio {
            self.last_selected_portfolio = self.selected_portfolio.clone();
            
            // Queue price history fetches for new portfolio
            if let Some(portfolio_name) = &self.selected_portfolio {
                if let Some(portfolios) = &self.app_state.portfolios {
                    if let Some(portfolio) = portfolios.get(portfolio_name) {
                        if let Ok(mut queue) = self.fetch_queue.try_lock() {
                            for symbol in portfolio.holdings.keys() {
                                if !queue.contains(symbol) {
                                    queue.push(symbol.clone());
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    fn fetch_price_history_async(&self, symbol: String, ctx: &egui::Context) {
        let api_client = self.api_client.clone();
        let async_state = Arc::clone(&self.async_state);
        let ctx = ctx.clone();
        
        tokio::spawn(async move {
            let result = api_client
                .get_historic_prices(&[symbol.clone()], "2023-01-01", "2024-12-31")
                .await;
            
            let price_points = match result {
                Ok(mut history_map) => {
                    if let Some(points) = history_map.remove(&symbol) {
                        Ok(points)
                    } else {
                        Err("No price history found for symbol".to_string())
                    }
                }
                Err(e) => Err(e.to_string()),
            };
            
            if let Ok(mut state) = async_state.lock() {
                state.price_history_results.push((symbol, price_points));
            }
            
            ctx.request_repaint();
        });
    }

    fn render_portfolio_panel(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("portfolio_panel")
            .default_width(250.0)
            .width_range(200.0..=400.0)
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.heading("📊 Portfolios");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if ui.small_button("➕").on_hover_text("Create New Portfolio").clicked() {
                            self.create_sample_portfolio();
                        }
                    });
                });
                
                ui.separator();
                
                // Error display using Frame for better visibility
                if let Some(ref error) = self.last_error_message {
                    egui::Frame::new()
                        .fill(egui::Color32::from_rgb(60, 20, 20))
                        .stroke(egui::Stroke::new(1.0, egui::Color32::RED))
                        .inner_margin(8.0)
                        .show(ui, |ui| {
                            ui.colored_label(egui::Color32::LIGHT_RED, "⚠ Error");
                            ui.small(error);
                        });
                    ui.add_space(8.0);
                }
                
                // Portfolio list with demo-style organization
                egui::ScrollArea::vertical()
                    .auto_shrink([false, true])
                    .show(ui, |ui| {
                        if let Some(portfolios) = &self.app_state.portfolios {
                            if portfolios.is_empty() {
                                ui.vertical_centered(|ui| {
                                    ui.weak("No portfolios yet");
                                    ui.small("Create one to get started");
                                });
                            } else {
                                // Collect portfolio items to avoid borrowing issues
                                let portfolio_items: Vec<(String, crate::portfolio::Portfolio)> = 
                                    portfolios.iter().map(|(name, portfolio)| (name.clone(), portfolio.clone())).collect();
                                
                                for (name, portfolio) in portfolio_items {
                                    self.render_portfolio_item(ui, &name, &portfolio);
                                }
                            }
                        } else {
                            ui.vertical_centered(|ui| {
                                ui.weak("No portfolios loaded");
                            });
                        }
                    });
                
                ui.separator();
                
                // Connection section with demo-style layout
                ui.collapsing("🔗 Connection", |ui| {
                    egui::Grid::new("connection_grid")
                        .num_columns(2)
                        .spacing([8.0, 4.0])
                        .show(ui, |ui| {
                            ui.label("Status:");
                            match &self.connection_status {
                                ConnectionStatus::Disconnected => {
                                    ui.colored_label(egui::Color32::RED, "● Disconnected");
                                }
                                ConnectionStatus::Connecting => {
                                    ui.colored_label(egui::Color32::YELLOW, "◐ Connecting...");
                                }
                                ConnectionStatus::Connected => {
                                    ui.colored_label(egui::Color32::GREEN, "● Connected");
                                }
                                ConnectionStatus::Error(_) => {
                                    ui.colored_label(egui::Color32::RED, "✗ Error");
                                }
                            }
                            ui.end_row();
                            
                            ui.label("API:");
                            ui.small(&self.app_state.config.api_base_url);
                            ui.end_row();
                        });
                    
                    if ui.button("Test Connection").clicked() {
                        self.test_connection_async(ctx);
                    }
                    
                    if !self.test_message.is_empty() {
                        ui.small(&self.test_message);
                    }
                });
            });
    }
    
    fn render_portfolio_item(&mut self, ui: &mut egui::Ui, name: &String, portfolio: &crate::portfolio::Portfolio) {
        let is_selected = Some(name) == self.selected_portfolio.as_ref();
        
        // Portfolio card with demo-style frame
        let frame = if is_selected {
            egui::Frame::group(ui.style())
                .fill(ui.visuals().selection.bg_fill)
                .stroke(egui::Stroke::new(1.0, ui.visuals().selection.stroke.color))
        } else {
            egui::Frame::group(ui.style())
                .fill(ui.visuals().faint_bg_color)
        };
        
        frame.show(ui, |ui| {
            ui.horizontal(|ui| {
                let response = ui.selectable_label(is_selected, name);
                if response.clicked() {
                    self.selected_portfolio = Some(name.clone());
                }
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.small_button("🗑").on_hover_text("Delete Portfolio").clicked() {
                        // Mark for deletion (will be handled after the loop)
                        self.portfolio_to_delete = Some(name.clone());
                    }
                });
            });
            
            if is_selected {
                ui.separator();
                egui::Grid::new(format!("portfolio_details_{}", name))
                    .num_columns(2)
                    .spacing([8.0, 2.0])
                    .show(ui, |ui| {
                        ui.small("Value:");
                        ui.small(format!("${:.0}", portfolio.total_value));
                        ui.end_row();
                        
                        ui.small("Holdings:");
                        ui.small(format!("{} symbols", portfolio.holdings.len()));
                        ui.end_row();
                        
                        ui.small("Updated:");
                        ui.small(portfolio.last_updated.format("%m/%d %H:%M").to_string());
                        ui.end_row();
                    });
            }
        });
        
        ui.add_space(4.0);
    }

    fn render_status_window(&mut self, ctx: &egui::Context) {
        egui::Window::new("Status")
            .open(&mut self.show_status_window)
            .show(ctx, |ui| {
                ui.heading("Connection Status");
                match &self.connection_status {
                    ConnectionStatus::Disconnected => {
                        ui.colored_label(egui::Color32::RED, "Disconnected");
                    }
                    ConnectionStatus::Connecting => {
                        ui.colored_label(egui::Color32::YELLOW, "Connecting...");
                    }
                    ConnectionStatus::Connected => {
                        ui.colored_label(egui::Color32::GREEN, "Connected");
                    }
                    ConnectionStatus::Error(e) => {
                        ui.colored_label(egui::Color32::RED, format!("Error: {}", e));
                    }
                }
                
                ui.separator();
                ui.heading("Configuration");
                ui.label(format!("API URL: {}", self.app_state.config.api_base_url));
                ui.label(format!("Native Mode: {}", self.app_state.config.use_native_provider));
                
                if let Some(portfolios) = &self.app_state.portfolios {
                    ui.separator();
                    ui.heading("Portfolios");
                    ui.label(format!("Loaded: {}", portfolios.len()));
                }
            });
    }

    fn test_connection_async(&mut self, ctx: &egui::Context) {
        self.connection_status = ConnectionStatus::Connecting;
        self.test_message = "Testing connection...".to_string();
        
        let api_client = self.api_client.clone();
        let async_state = Arc::clone(&self.async_state);
        let ctx = ctx.clone();
        
        tokio::spawn(async move {
            let result = api_client.test_health().await;
            
            if let Ok(mut state) = async_state.lock() {
                state.connection_result = Some(result.map_err(|e| e.to_string()));
            }
            
            ctx.request_repaint();
        });
    }
    
    fn create_sample_portfolio(&mut self) {
        let mut portfolio = crate::portfolio::Portfolio::new("Sample Portfolio".to_string());
        
        // Add some sample holdings
        portfolio.holdings.insert("AAPL".to_string(), 10.0);
        portfolio.holdings.insert("MSFT".to_string(), 5.0);
        portfolio.holdings.insert("GOOGL".to_string(), 3.0);
        portfolio.holdings.insert("TSLA".to_string(), 2.0);
        portfolio.holdings.insert("NVDA".to_string(), 1.0);
        
        // Set some reasonable weights and total value
        portfolio.total_value = 50000.0;
        portfolio.current_weights.insert("AAPL".to_string(), 0.4);
        portfolio.current_weights.insert("MSFT".to_string(), 0.25);
        portfolio.current_weights.insert("GOOGL".to_string(), 0.2);
        portfolio.current_weights.insert("TSLA".to_string(), 0.1);
        portfolio.current_weights.insert("NVDA".to_string(), 0.05);
        
        // Initialize portfolios map if needed
        if self.app_state.portfolios.is_none() {
            self.app_state.portfolios = Some(HashMap::new());
        }
        
        if let Some(portfolios) = &mut self.app_state.portfolios {
            portfolios.insert(portfolio.name.clone(), portfolio.clone());
            self.selected_portfolio = Some(portfolio.name);
        }
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
            "https://github.com/emilk/egui/tree/main/crates/eframe",
        );
        ui.label(".");
    });
}

impl eframe::App for TemplateApp {
    /// Called by the frame work to save state before shutdown.
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(storage, eframe::APP_KEY, self);
    }

    /// Called each time the UI needs repainting, which may be many times per second.
    /// Put your widgets into a `SidePanel`, `TopPanel`, `CentralPanel`, `Window` or `Area`.
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Handle async results
        self.handle_async_results();

        // Process any pending fetch queue items
        self.process_fetch_queue(ctx);

        // Check for portfolio selection change and queue fetches as needed
        self.handle_portfolio_selection_change();
        
        // Handle portfolio deletion
        if let Some(portfolio_to_delete) = self.portfolio_to_delete.take() {
            if let Some(portfolios) = &mut self.app_state.portfolios {
                portfolios.remove(&portfolio_to_delete);
                
                // If the deleted portfolio was selected, clear selection
                if self.selected_portfolio.as_ref() == Some(&portfolio_to_delete) {
                    self.selected_portfolio = None;
                }
            }
        }

        // Top panel with menu bar
        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("Quit").clicked() {
                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                    }
                });
                ui.menu_button("Components", |ui| {
                    for name in self.component_manager.component_names() {
                        let mut is_open = self.component_manager.is_component_open(&name);
                        if ui.checkbox(&mut is_open, &name).changed() {
                            self.component_manager.set_component_open(&name, is_open);
                        }
                    }
                });
                ui.menu_button("View", |ui| {
                    ui.checkbox(&mut self.show_portfolio_panel, "Portfolio Panel");
                    ui.checkbox(&mut self.show_status_window, "Status Window");
                });
            });
        });

        // Left side panel for portfolios
        if self.show_portfolio_panel {
            self.render_portfolio_panel(ctx);
        }

        // Status window
        if self.show_status_window {
            self.render_status_window(ctx);
        }

        // Central panel with portfolio application content
        egui::CentralPanel::default().show(ctx, |ui| {
            if let (Some(portfolios), Some(selected_name)) = (
                &self.app_state.portfolios,
                &self.selected_portfolio,
            ) {
                if let Some(portfolio) = portfolios.get(selected_name) {
                    // Portfolio is selected - render component tabs and main content
                    self.component_manager.render_all(ui, portfolio, &self.app_state.config);
                } else {
                    ui.centered_and_justified(|ui| {
                        ui.heading("Portfolio not found");
                    });
                }
            } else {
                // No portfolio selected - show welcome/setup screen
                ui.centered_and_justified(|ui| {
                    ui.vertical_centered(|ui| {
                        ui.heading("Welcome to Fractal Portfolio Tracker");
                        ui.add_space(20.0);
                        
                        if self.app_state.portfolios.is_none() || self.app_state.portfolios.as_ref().unwrap().is_empty() {
                            ui.label("No portfolios available. Create one to get started.");
                            ui.add_space(10.0);
                            
                            if ui.button("Create Sample Portfolio").clicked() {
                                self.create_sample_portfolio();
                            }
                        } else {
                            ui.label("Select a portfolio from the left panel to begin.");
                        }
                    });
                });
            }
            
            // Footer
            ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
                powered_by_egui_and_eframe(ui);
                ui.label(format!("Connection: {:?}", self.connection_status));
            });
        });

        // Render components using the component manager
        if let (Some(portfolios), Some(selected_name)) = (
            &self.app_state.portfolios,
            &self.selected_portfolio,
        ) {
            if let Some(portfolio) = portfolios.get(selected_name) {
                self.component_manager.render_components_in_context(
                    ctx,
                    portfolio,
                    &self.app_state.config,
                );
            }
        }
    }
}
