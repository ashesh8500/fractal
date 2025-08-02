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
            show_portfolio_panel: false,
            selected_portfolio: None,
            connection_status: ConnectionStatus::Disconnected,
            test_message: "Not tested yet".to_string(),
            async_state: Arc::new(Mutex::new(AsyncState::default())),
            show_status_window: false,
            fetch_queue: Arc::new(Mutex::new(Vec::new())),
            // keep left panel tame by default (shows first N items and a "show more" toggle)
            panel_render_limit: 30,
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
        app.api_client = ApiClient::new(&app.app_state.config.api_base_url).with_native(use_native, key);
        app.component_manager = ComponentManager::new();
        app.connection_status = ConnectionStatus::Disconnected;
        app.async_state = Arc::new(Mutex::new(AsyncState::default()));
        // fetch_queue is not an Option; it is always present. Ensure it is initialized.
        app.fetch_queue = Arc::new(Mutex::new(Vec::new()));

        app
    }

    /// Test backend connection
    fn test_backend_connection(&mut self, ctx: &egui::Context) {
        if matches!(self.connection_status, ConnectionStatus::Connecting) {
            return; // Already testing
        }

        self.connection_status = ConnectionStatus::Connecting;
        self.test_message = if self.app_state.config.use_native_provider {
            "Testing native provider...".to_string()
        } else {
            "Testing backend connection...".to_string()
        };

        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        let async_state = self.async_state.clone();

        // Use WASM-compatible async execution
        #[cfg(target_arch = "wasm32")]
        {
            wasm_bindgen_futures::spawn_local(async move {
                let result = match api_client.test_health().await {
                    Ok(_) => {
                        log::info!("Health check successful");
                        Ok(())
                    }
                    Err(e) => {
                        log::error!("Health check failed: {}", e);
                        Err(e.to_string())
                    }
                };

                if let Ok(mut state) = async_state.lock() {
                    state.connection_result = Some(result);
                }

                ctx.request_repaint();
            });
        }

        // Use thread for native
        #[cfg(not(target_arch = "wasm32"))]
        {
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let result = match api_client.test_health().await {
                        Ok(_) => {
                            log::info!("Health check successful");
                            Ok(())
                        }
                        Err(e) => {
                            log::error!("Health check failed: {}", e);
                            Err(e.to_string())
                        }
                    };

                    if let Ok(mut state) = async_state.lock() {
                        state.connection_result = Some(result);
                    }

                    ctx.request_repaint();
                });
            });
        }
    }

    /// Create a test portfolio with unique name
    fn create_test_portfolio(&mut self, ctx: &egui::Context) {
        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        let async_state = self.async_state.clone();

        // WASM
        #[cfg(target_arch = "wasm32")]
        {
            wasm_bindgen_futures::spawn_local(async move {
                let mut holdings: std::collections::HashMap<String, f64> =
                    std::collections::HashMap::new();
                holdings.insert("AAPL".to_string(), 10.0);
                holdings.insert("MSFT".to_string(), 5.0);
                let _ = holdings;
            });
        }

        // Native
        #[cfg(not(target_arch = "wasm32"))]
        {
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let mut holdings: std::collections::HashMap<String, f64> =
                        std::collections::HashMap::new();
                    holdings.insert("AAPL".to_string(), 10.0);
                    holdings.insert("MSFT".to_string(), 5.0);
                    holdings.insert("GOOGL".to_string(), 3.0);

                    let timestamp = chrono::Utc::now().format("%H%M%S");
                    let portfolio_name = format!("Test Portfolio {}", timestamp);

                    let result =
                        match api_client.create_portfolio(&portfolio_name, holdings).await {
                            Ok(portfolio) => {
                                log::info!("Created test portfolio: {}", portfolio.name);
                                Ok(portfolio.name)
                            }
                            Err(e) => {
                                log::error!("Failed to create test portfolio: {}", e);
                                Err(e.to_string())
                            }
                        };

                    if let Ok(mut state) = async_state.lock() {
                        state.portfolio_result = Some(result);
                    }

                    ctx.request_repaint();
                });
            });
        }
    }

    /// Enqueue symbol list to fetch price history for (deduplicated)
    pub fn enqueue_price_history_fetch(&mut self, symbols: &[String]) {
        if symbols.is_empty() {
            return;
        }
        if let Ok(mut queue) = self.fetch_queue.lock() {
            for s in symbols {
                if !queue.iter().any(|q| q == s) {
                    queue.push(s.clone());
                }
            }
        }
    }

    /// Load portfolios from backend or native (currently backend only returns actual list)
    fn load_portfolios(&mut self, ctx: &egui::Context) {
        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        let async_state = self.async_state.clone();

        // WASM
        #[cfg(target_arch = "wasm32")]
        {
            wasm_bindgen_futures::spawn_local(async move {
                let result = match api_client.get_portfolios().await {
                    Ok(portfolios) => {
                        log::info!("Loaded {} portfolios", portfolios.len());
                        Ok(portfolios)
                    }
                    Err(e) => {
                        log::error!("Failed to load portfolios: {}", e);
                        Err(e.to_string())
                    }
                };

                if let Ok(mut state) = async_state.lock() {
                    state.portfolios_result = Some(result);
                }

                ctx.request_repaint();
            });
        }

        // Native
        #[cfg(not(target_arch = "wasm32"))]
        {
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    let result = match api_client.get_portfolios().await {
                        Ok(portfolios) => {
                            log::info!("Loaded {} portfolios", portfolios.len());
                            Ok(portfolios)
                        }
                        Err(e) => {
                            log::error!("Failed to load portfolios: {}", e);
                            Err(e.to_string())
                        }
                    };

                    if let Ok(mut state) = async_state.lock() {
                        state.portfolios_result = Some(result);
                    }

                    ctx.request_repaint();
                });
            });
        }
    }

    /// Start background task to fetch price history for queued symbols, batched
    fn drain_and_fetch_price_history(&mut self, ctx: &egui::Context) {
        let symbols: Vec<String> = {
            let mut out = Vec::new();
            if let Ok(mut queue) = self.fetch_queue.lock() {
                let batch = if self.app_state.config.use_native_provider { 5 } else { 10 };
                let batch = batch.min(queue.len());
                for _ in 0..batch {
                    if let Some(s) = queue.pop() {
                        out.push(s);
                    }
                }
            }
            out
        };

        if symbols.is_empty() {
            return;
        }

        let api_client = self.api_client.clone();
        let ctx = ctx.clone();
        let async_state = self.async_state.clone();

        // Format dates robustly as YYYY-MM-DD
        let end_date = chrono::Utc::now().date_naive();
        let start_date = end_date
            .checked_sub_days(chrono::Days::new(200))
            .unwrap_or(end_date);
        let start_s = start_date.format("%Y-%m-%d").to_string();
        let end_s = end_date.format("%Y-%m-%d").to_string();

        #[cfg(target_arch = "wasm32")]
        {
            let symbols_clone = symbols.clone();
            let start_s2 = start_s.clone();
            let end_s2 = end_s.clone();
            wasm_bindgen_futures::spawn_local(async move {
                match api_client
                    .get_historic_prices(
                        &symbols_clone,
                        &start_s2,
                        &end_s2,
                    )
                    .await
                {
                    Ok(mut data) => {
                        if let Ok(mut state) = async_state.lock() {
                            for (sym, list) in data.drain() {
                                state.price_history_results.push((sym, Ok(list)));
                            }
                        }
                    }
                    Err(e) => {
                        if let Ok(mut state) = async_state.lock() {
                            for sym in symbols_clone {
                                state
                                    .price_history_results
                                    .push((sym, Err(e.to_string())));
                            }
                        }
                    }
                }
                ctx.request_repaint();
            });
        }

        #[cfg(not(target_arch = "wasm32"))]
        {
            let start_s2 = start_s.clone();
            let end_s2 = end_s.clone();
            std::thread::spawn(move || {
                let rt = tokio::runtime::Runtime::new().unwrap();
                rt.block_on(async move {
                    match api_client
                        .get_historic_prices(
                            &symbols,
                            &start_s2,
                            &end_s2,
                        )
                        .await
                    {
                        Ok(mut data) => {
                            if let Ok(mut state) = async_state.lock() {
                                for (sym, list) in data.drain() {
                                    state.price_history_results.push((sym, Ok(list)));
                                }
                            }
                        }
                        Err(e) => {
                            if let Ok(mut state) = async_state.lock() {
                                for sym in symbols {
                                    state
                                        .price_history_results
                                        .push((sym, Err(e.to_string())));
                                }
                            }
                        }
                    }
                    ctx.request_repaint();
                });
            });
        }
    }

    /// Enqueue symbol list to fetch price history for (deduplicated)
    pub fn enqueue_price_history_fetch(&mut self, symbols: &[String]) {
        if symbols.is_empty() {
            return;
        }
        if let Ok(mut queue) = self.fetch_queue.lock() {
            for s in symbols {
                if !queue.iter().any(|q| q == s) {
                    queue.push(s.clone());
                }
            }
        }
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

                // Controls
                ui.horizontal_wrapped(|ui| {
                    if ui.button(if self.app_state.config.use_native_provider { "Test Native" } else { "Test Backend Connection" }).clicked() {
                        self.test_backend_connection(ctx);
                    }
                    if ui.button("Create Test Portfolio").clicked() {
                        self.create_test_portfolio(ctx);
                    }
                    if ui.button("Refresh Portfolios").clicked() {
                        self.load_portfolios(ctx);
                    }
                    if ui.button("Toggle Provider Mode").clicked() {
                        self.app_state.config.use_native_provider = !self.app_state.config.use_native_provider;
                        // Rebuild api client
                        let key = self.app_state.config.alphavantage_api_key.clone();
                        self.api_client = ApiClient::new(&self.app_state.config.api_base_url)
                            .with_native(self.app_state.config.use_native_provider, key);
                        self.connection_status = ConnectionStatus::Disconnected;
                    }
                });

                ui.separator();

                // Portfolio list and selection with virtualization-like limit
                if let Some(portfolios) = &self.app_state.portfolios {
                    let total = portfolios.len();
                    let mut shown = 0usize;

                    egui::ScrollArea::vertical()
                        .max_height(200.0)
                        .show(ui, |ui| {
                            for (i, portfolio_name) in portfolios.keys().enumerate() {
                                if i >= self.panel_render_limit {
                                    break;
                                }
                                let selected =
                                    self.selected_portfolio.as_ref() == Some(portfolio_name);
                                if ui.selectable_label(selected, portfolio_name).clicked() {
                                    self.selected_portfolio = Some(portfolio_name.clone());
                                }
                                shown += 1;
                            }
                        });

                    if shown < total {
                        ui.weak(format!(
                            "Showing {} of {} portfolios",
                            shown, total
                        ));
                        if ui.button("Show more").clicked() {
                            self.panel_render_limit =
                                (self.panel_render_limit + 50).min(total.max(50));
                        }
                    }
                } else {
                    ui.label("No portfolios loaded");
                }

                ui.separator();
                ui.label(&self.test_message);
            });
    }

    /// Check for async operation results and update UI state
    fn check_async_results(&mut self, ctx: &egui::Context) {
        let mut should_load_portfolios = false;

        if let Ok(mut state) = self.async_state.lock() {
            if let Some(result) = state.connection_result.take() {
                match result {
                    Ok(_) => {
                        self.connection_status = ConnectionStatus::Connected;
                        self.test_message = if self.app_state.config.use_native_provider {
                            "Native provider ready!".to_string()
                        } else {
                            "Connection successful!".to_string()
                        };
                    }
                    Err(e) => {
                        self.connection_status = ConnectionStatus::Error(e.clone());
                        self.test_message = format!("Connection failed: {}", e);
                    }
                }
            }

            if let Some(result) = state.portfolio_result.take() {
                match result {
                    Ok(name) => {
                        self.test_message = format!(
                            "Portfolio '{}' created successfully! Loading portfolios...",
                            name
                        );
                        should_load_portfolios = true;
                    }
                    Err(e) => {
                        self.test_message = format!("Portfolio creation failed: {}", e);
                    }
                }
            }

            if let Some(result) = state.portfolios_result.take() {
                match result {
                    Ok(portfolios) => {
                        let mut portfolio_map = std::collections::HashMap::new();
                        for mut portfolio in portfolios {
                            if portfolio.price_history.is_none() {
                                portfolio.price_history = Some(std::collections::HashMap::new());
                            }
                            portfolio_map.insert(portfolio.name.clone(), portfolio);
                        }
                        self.app_state.portfolios = Some(portfolio_map);
                        self.test_message = format!(
                            "Loaded {} portfolios successfully!",
                            self.app_state.portfolios.as_ref().unwrap().len()
                        );
                    }
                    Err(e) => {
                        self.test_message = format!("Failed to load portfolios: {}", e);
                    }
                }
            }

            if !state.price_history_results.is_empty() {
                if let Some(selected_name) = &self.selected_portfolio {
                    if let Some(portfolios) = &mut self.app_state.portfolios {
                        if let Some(portfolio) = portfolios.get_mut(selected_name) {
                            if portfolio.price_history.is_none() {
                                portfolio.price_history = Some(std::collections::HashMap::new());
                            }
                            if let Some(price_map) = portfolio.price_history.as_mut() {
                                for (symbol, res) in state.price_history_results.drain(..) {
                                    match res {
                                        Ok(list) => {
                                            price_map.insert(symbol, list);
                                        }
                                        Err(e) => {
                                            log::warn!("Failed loading price history: {}", e);
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    state.price_history_results.clear();
                }
            }
        }

        if should_load_portfolios {
            self.load_portfolios(ctx);
        }

        self.drain_and_fetch_price_history(ctx);
    }

    /// Render portfolio components in the central panel
    fn render_portfolio_components(&mut self, ui: &mut egui::Ui) {
        if let Some(portfolio_name) = &self.selected_portfolio {
            if let Some(portfolio) = self.app_state.get_portfolio(portfolio_name) {
                self.component_manager
                    .render_all(ui, portfolio, &self.app_state.config);
            } else {
                ui.label("Portfolio not found");
            }
        } else {
            ui.label("Select a portfolio to view details");
        }
    }
}

impl eframe::App for TemplateApp {
    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        eframe::set_value(storage, eframe::APP_KEY, self);
    }

    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.check_async_results(ctx);

        egui::TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                let is_web = cfg!(target_arch = "wasm32");
                if !is_web {
                    ui.menu_button("File", |ui| {
                        if ui.button("Quit").clicked() {
                            ctx.request_repaint();
                        }
                    });
                    ui.add_space(16.0);
                }

                ui.menu_button("Portfolio", |ui| {
                    if ui.button("Toggle Portfolio Panel").clicked() {
                        self.show_portfolio_panel = !self.show_portfolio_panel;
                        ui.close_menu();
                    }
                    if ui.button(if self.app_state.config.use_native_provider { "Test Native" } else { "Test Backend" }).clicked() {
                        self.test_backend_connection(ctx);
                        ui.close_menu();
                    }
                    if ui.button("Load Portfolios").clicked() {
                        self.load_portfolios(ctx);
                        ui.close_menu();
                    }
                    if ui.button("Toggle Provider Mode").clicked() {
                        self.app_state.config.use_native_provider = !self.app_state.config.use_native_provider;
                        let key = self.app_state.config.alphavantage_api_key.clone();
                        self.api_client = ApiClient::new(&self.app_state.config.api_base_url)
                            .with_native(self.app_state.config.use_native_provider, key);
                        self.connection_status = ConnectionStatus::Disconnected;
                        ui.close_menu();
                    }
                });

                ui.separator();

                if ui.button("Fetch Price History").clicked() {
                    if let Some(selected) = &self.selected_portfolio {
                        if let Some(pmap) = self
                            .app_state
                            .portfolios
                            .as_ref()
                            .and_then(|m| m.get(selected))
                        {
                            let symbols = pmap.symbols();
                            self.enqueue_price_history_fetch(&symbols);
                        }
                    }
                }

                ui.add_space(16.0);
                egui::widgets::global_theme_preference_buttons(ui);
            });
        });

        self.render_portfolio_ui(ctx);

        if self.show_status_window {
            egui::Window::new("Status")
                .resizable(false)
                .default_width(280.0)
                .show(ctx, |ui| {
                    let (color, text) = match &self.connection_status {
                        ConnectionStatus::Disconnected => {
                            (egui::Color32::RED, "Backend: Disconnected")
                        }
                        ConnectionStatus::Connecting => {
                            (egui::Color32::YELLOW, "Backend: Connecting...")
                        }
                        ConnectionStatus::Connected => (egui::Color32::GREEN, "Backend: Connected"),
                        ConnectionStatus::Error(e) => (egui::Color32::RED, e.as_str()),
                    };
                    ui.horizontal(|ui| {
                        ui.colored_label(color, "●");
                        ui.label(text);
                    });
                    ui.separator();
                    ui.label(&format!("Test Status: {}", self.test_message));
                });
        }

        egui::CentralPanel::default().show(ctx, |ui| {
            if self.selected_portfolio.is_none() {
                ui.heading("Portfolio Management System");

                ui.horizontal(|ui| {
                    let (color, text) = match &self.connection_status {
                        ConnectionStatus::Disconnected => {
                            (egui::Color32::RED, "Backend: Disconnected")
                        }
                        ConnectionStatus::Connecting => {
                            (egui::Color32::YELLOW, "Backend: Connecting...")
                        }
                        ConnectionStatus::Connected => (egui::Color32::GREEN, "Backend: Connected"),
                        ConnectionStatus::Error(e) => (egui::Color32::RED, e.as_str()),
                    };

                    ui.colored_label(color, "●");
                    ui.label(text);
                });

                ui.separator();

                ui.horizontal(|ui| {
                    if ui.button(if self.app_state.config.use_native_provider { "Test Native" } else { "Test Backend Connection" }).clicked() {
                        self.test_backend_connection(ctx);
                    }
                    if ui.button("Create Test Portfolio").clicked() {
                        self.create_test_portfolio(ctx);
                    }
                });

                ui.separator();

                ui.horizontal(|ui| {
                    ui.label("Write something: ");
                    ui.text_edit_singleline(&mut self.label);
                });

                ui.add(egui::Slider::new(&mut self.value, 0.0..=10.0).text("value"));
                if ui.button("Increment").clicked() {
                    self.value += 1.0;
                }

                ui.separator();

                ui.label("Select 'Portfolio' -> 'Toggle Portfolio Panel' to get started");
                ui.label(&format!("Test Status: {}", self.test_message));

                ui.separator();

                ui.add(egui::github_link_file!(
                    "https://github.com/emilk/eframe_template/blob/main/",
                    "Original template source code."
                ));
            } else {
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
