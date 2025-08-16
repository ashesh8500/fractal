use crate::api::ApiClient;
use crate::components::ComponentManager;
use crate::state::AppState;
use crate::views::backtest::drain_backtest_requests;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

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

    // Login / Users windows
    #[serde(skip)]
    show_login_window: bool,
    #[serde(skip)]
    show_users_window: bool,

    // Authentication / Users state (frontend-only)
    #[serde(skip)]
    login_username: String,
    #[serde(skip)]
    login_password: String,
    #[serde(skip)]
    auth_token: Option<String>,
    #[serde(skip)]
    users: Vec<String>,
    #[serde(skip)]
    new_user_username: String,
    #[serde(skip)]
    new_user_password: String,
    #[serde(skip)]
    new_user_is_admin: bool,

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

    // Tokio runtime handle for background async operations
    #[serde(skip)]
    rt_handle: Option<tokio::runtime::Handle>,

    // New: control automatic reloading that can trigger rate limits in native mode
    constant_reload: bool,

    // New: tracks a one-shot manual backend load intent
    #[serde(skip)]
    backend_manual_load_pending: bool,
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
    // Currently fetching symbols
    pub fetching_symbols: std::collections::HashSet<String>,
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
            show_login_window: false,
            show_users_window: false,

            // Authentication / Users frontend defaults
            login_username: String::new(),
            login_password: String::new(),
            auth_token: None,
            users: Vec::new(),
            new_user_username: String::new(),
            new_user_password: String::new(),
            new_user_is_admin: false,

            fetch_queue: Arc::new(Mutex::new(Vec::new())),
            // keep left panel tame by default (shows first N items and a "show more" toggle)
            panel_render_limit: 30,
            last_selected_portfolio: None,
            last_error_message: None,
            portfolio_to_delete: None,
            rt_handle: None, // Will be set properly in new()
            // New defaults:
            constant_reload: true,
            backend_manual_load_pending: false,
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
    // In web builds, force server mode (native provider is unavailable in WASM)
    #[cfg(target_arch = "wasm32")]
    let use_native = false;
    #[cfg(not(target_arch = "wasm32"))]
    let use_native = app.app_state.config.use_native_provider;
        let key = app.app_state.config.alphavantage_api_key.clone();
        app.api_client =
            ApiClient::new(&app.app_state.config.api_base_url).with_native(use_native, key);
        app.component_manager = ComponentManager::new();
        app.connection_status = ConnectionStatus::Disconnected;
        app.async_state = Arc::new(Mutex::new(AsyncState::default()));
        // fetch_queue is not an Option; it is always present. Ensure it is.
        app.fetch_queue = Arc::new(Mutex::new(Vec::new()));

        // If we have a persisted auth token, set it on the ApiClient immediately
        if let Some(tok) = app.app_state.config.auth_token.clone() {
            app.api_client.set_token(Some(tok.clone()));
            app.auth_token = Some(tok);
            // If token exists, keep login window closed
            app.show_login_window = false;
        } else {
            // No token -> prompt login
            app.show_login_window = true;
        }

        // Create Tokio runtime in a background thread (native only)
        #[cfg(not(target_arch = "wasm32"))]
        {
            // Load .env if present
            let _ = dotenvy::dotenv();
            let rt = tokio::runtime::Runtime::new().unwrap();
            let handle = rt.handle().clone();
            std::thread::spawn(move || {
                rt.block_on(async {
                    futures::future::pending::<()>().await; // Keeps runtime alive indefinitely
                });
            });
            app.rt_handle = Some(handle);
        }
        #[cfg(target_arch = "wasm32")]
        {
            app.rt_handle = None;
        }

        // If no portfolios exist, create a quick demo portfolio to enable charts
        if app.app_state.portfolios.is_none() {
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

        // Queue initial fetches for the selected portfolio's holdings so charts/candles have data.
        if let Some(selected) = app.selected_portfolio.clone() {
            if let Some(portfolios) = &app.app_state.portfolios {
                if let Some(p) = portfolios.get(&selected) {
                    if let Ok(mut q) = app.fetch_queue.try_lock() {
                        for sym in p.holdings.keys() {
                            if !q.contains(sym) {
                                q.push(sym.clone());
                            }
                        }
                    }
                }
            }
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
                                    log::info!(
                                        "Updating portfolio {} with {} price points for {}",
                                        selected_name,
                                        price_points.len(),
                                        symbol
                                    );

                                    // Merge with existing history
                                    let mut history_map =
                                        portfolio.price_history.clone().unwrap_or_default();
                                    history_map.insert(symbol.clone(), price_points);
                                    portfolio.update_price_history(history_map);

                                    // Notify components that data has changed
                                    self.component_manager.notify_data_updated(portfolio);

                                    log::info!(
                                        "Portfolio now has price history for {} symbols",
                                        portfolio
                                            .price_history
                                            .as_ref()
                                            .map(|h| h.len())
                                            .unwrap_or(0)
                                    );
                                }
                                Err(e) => {
                                    self.last_error_message = Some(format!(
                                        "Failed to load price history for {}: {}",
                                        symbol, e
                                    ));
                                }
                            }
                        }
                    }
                }
            }
        }

        // Repaint after handling results so Charts/Candles refresh ASAP
        // Actual repaint happens in update() loop; this ensures the frame doesn't stall.
    }

    fn process_fetch_queue(&mut self, ctx: &egui::Context) {
        if let Ok(mut queue) = self.fetch_queue.try_lock() {
            if !queue.is_empty() {
                let symbols_to_fetch: Vec<String> = queue.drain(..).collect();
                log::info!(
                    "Processing fetch queue with {} items",
                    symbols_to_fetch.len()
                );
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
                            let mut symbols_added = Vec::new();
                            for symbol in portfolio.holdings.keys() {
                                if !queue.contains(symbol) {
                                    queue.push(symbol.clone());
                                    symbols_added.push(symbol.clone());
                                }
                            }
                            if !symbols_added.is_empty() {
                                log::info!("Queued history fetch for symbols: {:?}", symbols_added);
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

        // Mark symbol as being fetched
        if let Ok(mut state) = self.async_state.try_lock() {
            state.fetching_symbols.insert(symbol.clone());
        }

        // Request immediate repaint to show spinner
        ctx.request_repaint();

        log::info!("Spawning fetch for symbol: {}", symbol);

        #[cfg(not(target_arch = "wasm32"))]
        {
            if let Some(handle) = &self.rt_handle {
                let ctx2 = ctx.clone();
                handle.spawn(async move {
                    log::debug!("Starting fetch for symbol: {}", symbol);
                    let start = std::time::Instant::now();

                    let result = api_client
                        .get_historic_prices(&[symbol.clone()], "2023-01-01", "2024-12-31")
                        .await;

                    log::info!("Fetch for {} completed in {:?}", symbol, start.elapsed());

                    let price_points = match result {
                        Ok(mut history_map) => {
                            if let Some(points) = history_map.remove(&symbol) {
                                log::info!("Got {} price points for {}", points.len(), symbol);
                                Ok(points)
                            } else {
                                log::warn!("No price history found for symbol {}", symbol);
                                Err("No price history found for symbol".to_string())
                            }
                        }
                        Err(e) => {
                            log::error!("Error fetching {}: {}", symbol, e);
                            Err(e.to_string())
                        }
                    };

                    if let Ok(mut state) = async_state.lock() {
                        state.fetching_symbols.remove(&symbol);
                        state
                            .price_history_results
                            .push((symbol.clone(), price_points));
                        log::debug!("Updated async state for {}", symbol);
                    }

                    ctx2.request_repaint();
                });
            } else {
                log::warn!("Runtime handle not available, falling back to tokio::spawn");
                let ctx_clone = ctx.clone();
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
                        state.fetching_symbols.remove(&symbol);
                        state
                            .price_history_results
                            .push((symbol.clone(), price_points));
                    }

                    ctx_clone.request_repaint();
                });
            }
        }

        #[cfg(target_arch = "wasm32")]
        {
            let ctx_clone = ctx.clone();
            wasm_bindgen_futures::spawn_local(async move {
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
                    state.fetching_symbols.remove(&symbol);
                    state
                        .price_history_results
                        .push((symbol.clone(), price_points));
                }

                ctx_clone.request_repaint();
            });
        }
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
                    egui::Grid::new(ui.id().with("connection_grid"))  // Salted ID
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

                            ui.label("Provider:");
                            if self.app_state.config.use_native_provider {
                                ui.colored_label(egui::Color32::LIGHT_BLUE, "Native (Alpha Vantage)");
                            } else {
                                ui.colored_label(egui::Color32::LIGHT_GREEN, "Server Backend");
                            }
                            ui.end_row();

                            ui.label("API:");
                            ui.small(&self.app_state.config.api_base_url);
                            ui.end_row();
                        });

                    // Controls to avoid rate limiting and enable manual loads
                    ui.horizontal(|ui| {
                        ui.checkbox(&mut self.constant_reload, "Constant reload");
                        if self.app_state.config.use_native_provider {
                            if ui.button("Fetch Holdings Now").on_hover_text("One-shot fetch for selected portfolio holdings (native provider)").clicked() {
                                // Queue selected portfolio symbols once
                                if let (Some(selected), Some(portfolios)) = (&self.selected_portfolio, &self.app_state.portfolios) {
                                    if let Some(p) = portfolios.get(selected) {
                                        if let Ok(mut q) = self.fetch_queue.try_lock() {
                                            for sym in p.holdings.keys() {
                                                if !q.contains(sym) {
                                                    q.push(sym.clone());
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } else {
                            if ui.button("Load from Backend").on_hover_text("One-shot fetch for selected portfolio holdings (server backend)").clicked() {
                                self.backend_manual_load_pending = true;
                            }
                        }
                    });

                    ui.horizontal(|ui| {
                        if ui.button("Test Connection").clicked() {
                            self.test_connection_async(ctx);
                        }

                        let switch_text = if self.app_state.config.use_native_provider {
                            "Switch to Server"
                        } else {
                            "Switch to Native"
                        };

                        if ui.button(switch_text).on_hover_text("Toggle data provider").clicked() {
                            self.toggle_data_provider();
                        }
                    });

                    if !self.test_message.is_empty() {
                        ui.small(&self.test_message);
                    }
                });

                // Live fetch status section
                if let Ok(state) = self.async_state.try_lock() {
                    if !state.fetching_symbols.is_empty() {
                        ui.separator();
                        ui.collapsing("📡 Live Data Fetching", |ui| {
                            ui.small(format!("Fetching {} symbol(s):", state.fetching_symbols.len()));
                            ui.indent("fetching_list", |ui| {
                                for symbol in &state.fetching_symbols {
                                    ui.horizontal(|ui| {
                                        ui.spinner();
                                        ui.small(symbol);
                                    });
                                }
                            });
                        });
                    }
                }
            });
    }

    fn render_portfolio_item(
        &mut self,
        ui: &mut egui::Ui,
        name: &String,
        portfolio: &crate::portfolio::Portfolio,
    ) {
        let is_selected = Some(name) == self.selected_portfolio.as_ref();

        // Portfolio card with demo-style frame
        let frame = if is_selected {
            egui::Frame::group(ui.style())
                .fill(ui.visuals().selection.bg_fill)
                .stroke(egui::Stroke::new(1.0, ui.visuals().selection.stroke.color))
        } else {
            egui::Frame::group(ui.style()).fill(ui.visuals().faint_bg_color)
        };

        frame.show(ui, |ui| {
            ui.horizontal(|ui| {
                let response = ui.selectable_label(is_selected, name);
                if response.clicked() {
                    let selection_changed = self.selected_portfolio.as_ref() != Some(name);
                    self.selected_portfolio = Some(name.clone());
                    if selection_changed {
                        // proactively queue fetches for this portfolio on click
                        if let Some(portfolios) = &self.app_state.portfolios {
                            if let Some(p) = portfolios.get(name) {
                                if let Ok(mut q) = self.fetch_queue.try_lock() {
                                    for sym in p.holdings.keys() {
                                        if !q.contains(sym) {
                                            q.push(sym.clone());
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui
                        .small_button("🗑")
                        .on_hover_text("Delete Portfolio")
                        .clicked()
                    {
                        // Mark for deletion (will be handled after the loop)
                        self.portfolio_to_delete = Some(name.clone());
                    }
                });
            });

            if is_selected {
                ui.separator();
                egui::Grid::new(ui.id().with(("portfolio_details", name))) // Salted with ui.id() and name
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
            .resizable(true)
            .default_size(egui::Vec2::new(500.0, 400.0))
            .open(&mut self.show_status_window)
            .show(ctx, |ui_win| {
                egui::ScrollArea::vertical().show(ui_win, |ui| {
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
                    ui.label(format!(
                        "Native Mode: {}",
                        self.app_state.config.use_native_provider
                    ));

                    if let Some(portfolios) = &self.app_state.portfolios {
                        ui.separator();
                        ui.heading("Portfolios");
                        ui.label(format!("Loaded: {}", portfolios.len()));
                    }
                });
            });
    }

    fn test_connection_async(&mut self, ctx: &egui::Context) {
        self.connection_status = ConnectionStatus::Connecting;
        self.test_message = "Testing connection...".to_string();

        let api_client = self.api_client.clone();
        let async_state = Arc::clone(&self.async_state);
        let ctx = ctx.clone();

        #[cfg(not(target_arch = "wasm32"))]
        {
            if let Some(handle) = &self.rt_handle {
                handle.spawn(async move {
                    let result = api_client.test_health().await;

                    if let Ok(mut state) = async_state.lock() {
                        state.connection_result = Some(result.map_err(|e| e.to_string()));
                    }

                    ctx.request_repaint();
                });
            } else {
                tokio::spawn(async move {
                    let result = api_client.test_health().await;

                    if let Ok(mut state) = async_state.lock() {
                        state.connection_result = Some(result.map_err(|e| e.to_string()));
                    }

                    ctx.request_repaint();
                });
            }
        }

        #[cfg(target_arch = "wasm32")]
        {
            wasm_bindgen_futures::spawn_local(async move {
                let result = api_client.test_health().await;

                if let Ok(mut state) = async_state.lock() {
                    state.connection_result = Some(result.map_err(|e| e.to_string()));
                }

                ctx.request_repaint();
            });
        }
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

        // Queue fetch for the new portfolio
        if let Some(selected) = &self.selected_portfolio {
            if let Some(portfolios) = &self.app_state.portfolios {
                if let Some(p) = portfolios.get(selected) {
                    if let Ok(mut q) = self.fetch_queue.try_lock() {
                        for sym in p.holdings.keys() {
                            if !q.contains(sym) {
                                q.push(sym.clone());
                            }
                        }
                    }
                }
            }
        }
    }

    fn toggle_data_provider(&mut self) {
        // Toggle the provider mode. In web/WASM, native provider is unavailable, so keep it off.
        #[cfg(not(target_arch = "wasm32"))]
        {
            self.app_state.config.use_native_provider = !self.app_state.config.use_native_provider;
        }
        #[cfg(target_arch = "wasm32")]
        {
            self.app_state.config.use_native_provider = false;
        }

        // Recreate API client with new settings
    #[cfg(target_arch = "wasm32")]
    let use_native = false;
    #[cfg(not(target_arch = "wasm32"))]
    let use_native = self.app_state.config.use_native_provider;
        let key = self.app_state.config.alphavantage_api_key.clone();
        self.api_client =
            ApiClient::new(&self.app_state.config.api_base_url).with_native(use_native, key);

        // Reset connection status
        self.connection_status = ConnectionStatus::Disconnected;

        // Update test message
    if use_native {
            self.test_message = "Switched to Native (Alpha Vantage) provider".to_string();
        } else {
            self.test_message = "Switched to Server Backend provider".to_string();
        }

        log::info!(
            "Data provider switched to: {}",
            if use_native { "Native" } else { "Server" }
        );
    }
}

fn powered_by_egui_and_eframe(ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.spacing_mut().item_spacing.x = 0.0;
        ui.label("Powered by ");
        ui.hyperlink_to("egui", "https://github.com/emilk/egui");
        ui.label(" and ");
        ui.hyperlink_to("eframe", "https://github.com/emilk/eframe");
        ui.label(".");
    });
}

// Implementation of the eframe::App trait separated from helper impl above
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

        // Drain any backtest requests emitted by components and spawn backend calls
        for ev in drain_backtest_requests(ctx) {
            let selected = ev.portfolio_name.clone();
            // Capture current holdings to create backend portfolio if missing
            let holdings: HashMap<String, f64> = self
                .app_state
                .portfolios
                .as_ref()
                .and_then(|m| m.get(&selected))
                .map(|p| p.holdings.clone())
                .unwrap_or_default();

            #[cfg(not(target_arch = "wasm32"))]
            {
                if let Some(handle) = &self.rt_handle {
                    let api_client = self.api_client.clone();
                    let ctx_clone = ctx.clone();
                    let selected_cl = selected.clone();
                    let strategy_name = ev.strategy_name.clone();
                    let start_date = ev.start_date.clone();
                    let end_date = ev.end_date.clone();
                    let benchmark = ev.benchmark.clone();
                    let initial_capital = ev.initial_capital;
                    let commission = ev.commission;
                    let slippage = ev.slippage;
                    let holdings_cl = holdings.clone();

                    handle.spawn(async move {
                        // Ensure portfolio exists on backend
                        let ensure_res = match api_client.get_portfolio(&selected_cl).await {
                            Ok(_) => Ok(()),
                            Err(_) => {
                                // Try to create with current holdings
                                api_client
                                    .create_portfolio(&selected_cl, &holdings_cl)
                                    .await
                                    .map(|_| ())
                            }
                        };

                        let res = match ensure_res {
                            Ok(()) => {
                                api_client
                                    .run_backtest(
                                        &selected_cl,
                                        &strategy_name,
                                        &start_date,
                                        &end_date,
                                        initial_capital,
                                        commission,
                                        slippage,
                                        &benchmark,
                                    )
                                    .await
                            }
                            Err(e) => Err(e),
                        };

                        // Store raw result JSON in memory for UI thread to pick up via ctx memory
                        ctx_clone.memory_mut(|mem| {
                            let id = egui::Id::new("backtest_result_json");
                            let mut list: Vec<(String, Result<serde_json::Value, String>)> =
                                mem.data.get_temp(id).unwrap_or_default();
                            list.push((selected_cl.clone(), res.map_err(|e| e.to_string())));
                            mem.data.insert_temp(id, list);
                        });

                        ctx_clone.request_repaint();
                    });
                }
            }

            #[cfg(target_arch = "wasm32")]
            {
                let api_client = self.api_client.clone();
                let ctx_clone = ctx.clone();
                let selected_cl = selected.clone();
                let strategy_name = ev.strategy_name.clone();
                let start_date = ev.start_date.clone();
                let end_date = ev.end_date.clone();
                let benchmark = ev.benchmark.clone();
                let initial_capital = ev.initial_capital;
                let commission = ev.commission;
                let slippage = ev.slippage;
                let holdings_cl = holdings.clone();

                wasm_bindgen_futures::spawn_local(async move {
                    // Ensure portfolio exists on backend
                    let ensure_res = match api_client.get_portfolio(&selected_cl).await {
                        Ok(_) => Ok(()),
                        Err(_) => {
                            api_client
                                .create_portfolio(&selected_cl, &holdings_cl)
                                .await
                                .map(|_| ())
                        }
                    };

                    let res = match ensure_res {
                        Ok(()) => {
                            api_client
                                .run_backtest(
                                    &selected_cl,
                                    &strategy_name,
                                    &start_date,
                                    &end_date,
                                    initial_capital,
                                    commission,
                                    slippage,
                                    &benchmark,
                                )
                                .await
                        }
                        Err(e) => Err(e),
                    };

                    ctx_clone.memory_mut(|mem| {
                        let id = egui::Id::new("backtest_result_json");
                        let mut list: Vec<(String, Result<serde_json::Value, String>)> =
                            mem.data.get_temp(id).unwrap_or_default();
                        list.push((selected_cl.clone(), res.map_err(|e| e.to_string())));
                        mem.data.insert_temp(id, list);
                    });

                    ctx_clone.request_repaint();
                });
            }
        }

        // Consume any finished backtests and update portfolios
        ctx.memory_mut(|mem| {
            let id = egui::Id::new("backtest_result_json");
            if let Some(list) = mem.data.get_temp::<Vec<(String, Result<serde_json::Value, String>)>>(id) {
                for (pname, item) in list.into_iter() {
                    if let Some(portfolios) = &mut self.app_state.portfolios {
                        if let Some(p) = portfolios.get_mut(&pname) {
                            match item {
                                Ok(v) => {
                                    // Try direct deserialization first
                                    if let Ok(bt) = serde_json::from_value::<crate::portfolio::BacktestResult>(v.clone()) {
                                        p.backtest_results = Some(bt);
                                        // Store status for UI feedback
                                        let status_id = egui::Id::new(format!("backtest_status:{}", pname));
                                        mem.data.insert_temp(status_id, String::from("Backtest completed."));
                                    } else {
                                        // Manual adapter: convert backend schema -> UI BacktestResult
                                        use chrono::{DateTime, NaiveDateTime, Utc};
                                        use crate::portfolio::{BacktestResult as UiBacktestResult, DateRange, EquityPoint, PerformanceMetrics};

                                        fn parse_dt(s: &str) -> Option<DateTime<Utc>> {
                                            if let Ok(dt) = DateTime::parse_from_rfc3339(s) { return Some(dt.with_timezone(&Utc)); }
                                            if let Ok(ndt) = NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S") {
                                                return Some(DateTime::<Utc>::from_naive_utc_and_offset(ndt, Utc));
                                            }
                                            if let Ok(nd) = chrono::NaiveDate::parse_from_str(s, "%Y-%m-%d") {
                                                if let Some(ndt) = nd.and_hms_opt(0,0,0) {
                                                    return Some(DateTime::<Utc>::from_naive_utc_and_offset(ndt, Utc));
                                                }
                                            }
                                            None
                                        }

                                        let strategy_name = v.get("strategy_name").and_then(|x| x.as_str()).unwrap_or("unknown").to_string();
                                        let start_s = v.get("start_date").and_then(|x| x.as_str()).or_else(|| v.get("config").and_then(|c| c.get("start_date")).and_then(|x| x.as_str()));
                                        let end_s = v.get("end_date").and_then(|x| x.as_str()).or_else(|| v.get("config").and_then(|c| c.get("end_date")).and_then(|x| x.as_str()));
                                        let start_dt = start_s.and_then(parse_dt).unwrap_or_else(|| Utc::now());
                                        let end_dt = end_s.and_then(parse_dt).unwrap_or_else(|| Utc::now());

                                        let portfolio_values: Vec<f64> = v.get("portfolio_values").and_then(|x| x.as_array()).map(|arr| arr.iter().filter_map(|n| n.as_f64()).collect()).unwrap_or_default();
                                        let timestamps_raw: Vec<String> = v.get("timestamps").and_then(|x| x.as_array()).map(|arr| arr.iter().filter_map(|s| s.as_str().map(|t| t.to_string())).collect()).unwrap_or_default();
                                        let mut equity_curve: Vec<EquityPoint> = Vec::new();
                                        if !portfolio_values.is_empty() {
                                            for (i, val) in portfolio_values.iter().enumerate() {
                                                let dt = timestamps_raw.get(i).and_then(|s| parse_dt(s)).unwrap_or_else(|| start_dt + chrono::Duration::days(i as i64));
                                                equity_curve.push(EquityPoint { date: dt, value: *val });
                                            }
                                        }

                                        let perf = PerformanceMetrics {
                                            total_return: v.get("total_return").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                            annualized_return: v.get("annualized_return").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                            alpha: v.get("alpha").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                            beta: v.get("beta").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                        };

                                        let bench_perf = v.get("benchmark_return").and_then(|x| x.as_f64()).map(|br| PerformanceMetrics { total_return: br, annualized_return: 0.0, alpha: 0.0, beta: 1.0 });

                                        let final_value = portfolio_values.last().copied().unwrap_or(0.0);
                                        let trades_executed = v.get("total_trades").and_then(|x| x.as_u64()).unwrap_or(0) as u32;

                                        let mut adapted = UiBacktestResult {
                                            strategy_name,
                                            period: DateRange { start_date: start_dt, end_date: end_dt },
                                            performance: perf,
                                            benchmark_performance: bench_perf,
                                            trades_executed,
                                            final_portfolio_value: final_value,
                                            equity_curve,
                                            benchmark_curve: None,
                                            weights_over_time: None,
                                        };

                                        // Optional: parse benchmark curve if present
                                        let status_id = egui::Id::new(format!("backtest_status:{}", pname));
                                        mem.data.insert_temp(status_id, String::from("Backtest completed (adapted)."));
                                        // Supports shapes: { benchmark_curve: [{timestamp, value}] } or
                                        // separate arrays: benchmark_values [+ timestamps]
                                        if let Some(curve_arr) = v.get("benchmark_curve").and_then(|x| x.as_array()) {
                                            let mut bc: Vec<EquityPoint> = Vec::new();
                                            for item in curve_arr {
                                                if let (Some(ts), Some(val)) = (item.get("timestamp").and_then(|x| x.as_str()), item.get("value").and_then(|x| x.as_f64())) {
                                                    if let Some(dt) = parse_dt(ts) {
                                                        bc.push(EquityPoint { date: dt, value: val });
                                                    }
                                                }
                                            }
                                            if !bc.is_empty() { adapted.benchmark_curve = Some(bc); }
                                        } else if let Some(vals) = v.get("benchmark_values").and_then(|x| x.as_array()) {
                                            let ts = v.get("benchmark_timestamps").and_then(|x| x.as_array());
                                            let mut bc: Vec<EquityPoint> = Vec::new();
                                            for (i, valv) in vals.iter().enumerate() {
                                                if let Some(val) = valv.as_f64() {
                                                    let dt = ts.and_then(|arr| arr.get(i)).and_then(|s| s.as_str()).and_then(parse_dt).unwrap_or_else(|| start_dt + chrono::Duration::days(i as i64));
                                                    bc.push(EquityPoint { date: dt, value: val });
                                                }
                                            }
                                            if !bc.is_empty() { adapted.benchmark_curve = Some(bc); }
                                        }

                                        // Optional: parse weights_over_time if present; otherwise derive from executed_trades weight_fraction per timestamp
                                        if let Some(wot) = v.get("weights_over_time").and_then(|x| x.as_array()) {
                                            let mut snaps: Vec<crate::portfolio::WeightsAtTime> = Vec::new();
                                            for item in wot {
                                                // Support both {timestamp} and {date}
                                                let ts_opt = item.get("timestamp").and_then(|x| x.as_str()).and_then(parse_dt)
                                                    .or_else(|| item.get("date").and_then(|x| x.as_str()).and_then(parse_dt));
                                                if let Some(ts) = ts_opt {
                                                    let mut weights: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
                                                    if let Some(wdict) = item.get("weights").and_then(|x| x.as_object()) {
                                                        for (k, v) in wdict.iter() {
                                                            if let Some(f) = v.as_f64() { weights.insert(k.clone(), f); }
                                                        }
                                                    }
                                                    if !weights.is_empty() { snaps.push(crate::portfolio::WeightsAtTime { timestamp: ts, weights }); }
                                                }
                                            }
                                            if !snaps.is_empty() { adapted.weights_over_time = Some(snaps); }
                                        } else if let Some(exec) = v.get("executed_trades").and_then(|x| x.as_array()) {
                                            use std::collections::{BTreeMap, HashMap};
                                            let mut by_ts: BTreeMap<chrono::DateTime<chrono::Utc>, HashMap<String, f64>> = BTreeMap::new();
                                            for t in exec {
                                                // Support both timestamp and date
                                                let ts_dt = t.get("timestamp").and_then(|x| x.as_str()).and_then(parse_dt)
                                                    .or_else(|| t.get("date").and_then(|x| x.as_str()).and_then(parse_dt))
                                                    .unwrap_or(start_dt);
                                                let sym = t.get("symbol").and_then(|x| x.as_str()).unwrap_or("");
                                                // Try multiple keys for target weight
                                                let wf = t.get("weight_fraction").and_then(|x| x.as_f64())
                                                    .or_else(|| t.get("target_weight").and_then(|x| x.as_f64()))
                                                    .or_else(|| t.get("weight").and_then(|x| x.as_f64()))
                                                    .or_else(|| t.get("target_allocation").and_then(|x| x.as_f64()))
                                                    .unwrap_or(f64::NAN);
                                                if sym.is_empty() || !wf.is_finite() { continue; }
                                                let e = by_ts.entry(ts_dt).or_default();
                                                e.insert(sym.to_string(), wf);
                                            }
                                            if !by_ts.is_empty() {
                                                let snaps: Vec<crate::portfolio::WeightsAtTime> = by_ts.into_iter().map(|(ts, weights)| crate::portfolio::WeightsAtTime { timestamp: ts, weights }).collect();
                                                adapted.weights_over_time = Some(snaps);
                                            }
                                        }

                                        p.backtest_results = Some(adapted);

                                        // Executed trades table (optional)
                                        if let Some(exec) = v.get("executed_trades").and_then(|x| x.as_array()) {
                                            let mut trades: Vec<crate::portfolio::TradeExecution> = Vec::new();
                                            for t in exec {
                                                // Support timestamp/date
                                                let ts = t.get("timestamp").and_then(|x| x.as_str())
                                                    .or_else(|| t.get("date").and_then(|x| x.as_str()));
                                                let ts_dt = ts
                                                    .and_then(|s| chrono::DateTime::parse_from_rfc3339(s).ok().map(|d| d.with_timezone(&chrono::Utc)))
                                                    .unwrap_or(start_dt);
                                                trades.push(crate::portfolio::TradeExecution {
                                                    symbol: t.get("symbol").and_then(|x| x.as_str()).unwrap_or("").to_string(),
                                                    action: t.get("action").and_then(|x| x.as_str()).unwrap_or("").to_string(),
                                                    quantity_shares: t.get("quantity_shares").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    // weight field fallbacks
                                                    weight_fraction: t.get("weight_fraction").and_then(|x| x.as_f64())
                                                        .or_else(|| t.get("target_weight").and_then(|x| x.as_f64()))
                                                        .or_else(|| t.get("weight").and_then(|x| x.as_f64()))
                                                        .or_else(|| t.get("target_allocation").and_then(|x| x.as_f64()))
                                                        .unwrap_or(0.0),
                                                    price: t.get("price").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    gross_value: t.get("gross_value").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    commission: t.get("commission").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    slippage: t.get("slippage").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    total_cost: t.get("total_cost").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    net_cash_delta: t.get("net_cash_delta").and_then(|x| x.as_f64()).unwrap_or(0.0),
                                                    timestamp: ts_dt,
                                                    reason: t.get("reason").and_then(|x| x.as_str()).map(|s| s.to_string()),
                                                });
                                            }
                                            p.backtest_trades = Some(trades);
                                        } else {
                                            p.backtest_trades = None;
                                        }
                                    }
                                }
                                Err(err) => {
                                    p.data_status = Some(crate::portfolio::DataStatus {
                                        is_loading: false,
                                        last_error: Some(format!("Backtest failed: {}", err)),
                                        data_freshness: std::collections::HashMap::new(),
                                        provider_status: crate::portfolio::ProviderStatus::Error("backtest".into()),
                                    });
                                }
                            }
                        }
                    }
                }
                mem.data.remove::<Vec<(String, Result<serde_json::Value, String>)>>(id);
            }
        });

        // If selected portfolio exists but no price history present and nothing is fetching,
        // auto-queue all holdings once to populate charts (only when constant_reload is ON).
        if let (Some(selected), Some(portfolios)) =
            (self.selected_portfolio.clone(), &self.app_state.portfolios)
        {
            if let Some(p) = portfolios.get(&selected) {
                let has_any_history = p
                    .price_history
                    .as_ref()
                    .map(|m| !m.is_empty())
                    .unwrap_or(false);
                let fetching_any = self
                    .async_state
                    .try_lock()
                    .ok()
                    .map(|s| !s.fetching_symbols.is_empty())
                    .unwrap_or(false);
                if self.constant_reload && !has_any_history && !fetching_any {
                    if let Ok(mut q) = self.fetch_queue.try_lock() {
                        let mut added = false;
                        for sym in p.holdings.keys() {
                            if !q.contains(sym) {
                                q.push(sym.clone());
                                added = true;
                            }
                        }
                        if added {
                            log::info!(
                                "Auto-queued fetch for holdings of selected portfolio '{}'",
                                selected
                            );
                        }
                    }
                }
            }
        }

        // Handle one-shot manual backend load (queues holdings)
        if self.backend_manual_load_pending {
            self.backend_manual_load_pending = false;
            if !self.app_state.config.use_native_provider {
                if let (Some(selected), Some(portfolios)) =
                    (&self.selected_portfolio, &self.app_state.portfolios)
                {
                    if let Some(p) = portfolios.get(selected) {
                        if let Ok(mut q) = self.fetch_queue.try_lock() {
                            for sym in p.holdings.keys() {
                                if !q.contains(sym) {
                                    q.push(sym.clone());
                                }
                            }
                        }
                    }
                }
            }
        }

        // Process any pending fetch queue items
        self.process_fetch_queue(ctx);

        // Check for portfolio selection change and queue fetches as needed
        self.handle_portfolio_selection_change();

        // Request continuous updates while fetching
        if let Ok(state) = self.async_state.try_lock() {
            if !state.fetching_symbols.is_empty() {
                ctx.request_repaint_after(std::time::Duration::from_millis(100));
            }
        }

        // Handle portfolio deletion
        if let Some(portfolio_to_delete) = self.portfolio_to_delete.take() {
            if let Some(portfolios) = &mut self.app_state.portfolios {
                portfolios.remove(&portfolio_to_delete);

                // If the deleted portfolio was selected, clear selection
                if self.selected_portfolio.as_ref() == Some(&portfolio_to_delete) {
                    self.selected_portfolio = None;
                }
            }
            // Ensure UI updates after deletion
            ctx.request_repaint();
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

                // Account menu: login / users management
                ui.menu_button("Account", |ui| {
                    if ui.button("Login").clicked() {
                        self.show_login_window = true;
                    }
                    if ui.button("Users").clicked() {
                        self.show_users_window = true;
                    }
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

        // Login window (minimal Google OAuth via pasted ID token)
        if self.show_login_window {
            let mut open = true;
            egui::Window::new("Login")
                .open(&mut open)
                .resizable(true)
                .show(ctx, |ui| {
                    ui.label("Paste Google ID token (from your OAuth flow) or use legacy username/password.");
                    ui.add_space(8.0);
                    ui.label("Google ID Token:");
                    ui.text_edit_singleline(&mut self.login_password); // reuse field to avoid new ones
                    ui.horizontal(|ui| {
                        if ui.button("Login with Google").clicked() {
                            let id_token = self.login_password.clone();
                            let api = self.api_client.clone();
                            let ctx2 = ctx.clone();
                            // We need mutable refs after async completes; capture a pointer via egui memory
                            #[cfg(not(target_arch = "wasm32"))]
                            if let Some(handle) = &self.rt_handle {
                                handle.spawn(async move {
                                    let res = api.auth_google(&id_token).await;
                                    ctx2.memory_mut(|mem| {
                                        mem.data.insert_temp(egui::Id::new("login_result"), res.map_err(|e| e.to_string()));
                                    });
                                    ctx2.request_repaint();
                                });
                            }
                            #[cfg(target_arch = "wasm32")]
                            {
                                wasm_bindgen_futures::spawn_local(async move {
                                    let res = api.auth_google(&id_token).await;
                                    ctx2.memory_mut(|mem| {
                                        mem.data.insert_temp(egui::Id::new("login_result"), res.map_err(|e| e.to_string()));
                                    });
                                    ctx2.request_repaint();
                                });
                            }
                        }
                        if ui.button("Clear").clicked() {
                            self.login_password.clear();
                        }
                    });

                    ui.add_space(8.0);
                    ui.horizontal(|ui| {
                        if ui.button("Login with Google (browser)").on_hover_text("Open Google in your browser and wait for login to complete").clicked() {
                            let api = self.api_client.clone();
                            let ctx2 = ctx.clone();
                            #[cfg(not(target_arch = "wasm32"))]
                            if let Some(handle) = &self.rt_handle {
                                handle.spawn(async move {
                                    let start = api.google_oauth_start().await;
                                    let (auth_url, state) = match start {
                                        Ok(v) => v,
                                        Err(e) => {
                                            ctx2.memory_mut(|mem| {
                                                mem.data.insert_temp(egui::Id::new("login_error"), format!("OAuth start failed: {}", e));
                                            });
                                            ctx2.request_repaint();
                                            return;
                                        }
                                    };
                                    // Try to open the browser
                                    let _ = ApiClient::open_in_browser(&auth_url);
                                    // Always expose URL as a fallback in UI
                                    ctx2.memory_mut(|mem| {
                                        mem.data.insert_temp(egui::Id::new("login_auth_url"), auth_url.clone());
                                    });
                                    // Poll until complete (up to ~60s)
                                    let mut attempts = 0;
                                    loop {
                                        tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
                                        attempts += 1;
                                        match api.google_oauth_status(&state).await {
                                            Ok((done, maybe)) => {
                                                if done {
                                                    if let Some((token, username)) = maybe {
                                                        ctx2.memory_mut(|mem| {
                                                            let res: Result<(String, Option<String>), String> = Ok((token, username));
                                                            mem.data.insert_temp(egui::Id::new("login_result"), res);
                                                        });
                                                        ctx2.request_repaint();
                                                        break;
                                                    }
                                                } else {
                                                    // Pending: keep UI responsive
                                                    ctx2.request_repaint();
                                                }
                                            }
                                            Err(_e) => {
                                                // keep polling unless too many attempts
                                            }
                                        }
                                        if attempts > 40 { // ~60s
                                            ctx2.memory_mut(|mem| {
                                                mem.data.insert_temp(egui::Id::new("login_error"), "Login timed out".to_string());
                                            });
                                            ctx2.request_repaint();
                                            break;
                                        }
                                    }
                                });
                            }
                        }
                    });

                    // Show auth URL fallback (clickable) if available and indicate progress
                    ctx.memory(|mem| {
                        if let Some(url) = mem.data.get_temp::<String>(egui::Id::new("login_auth_url")) {
                            ui.separator();
                            ui.label("If your browser didn't open, click:");
                            ui.hyperlink(url);
                            ui.add_space(6.0);
                            ui.horizontal(|ui| {
                                ui.spinner();
                                ui.label("Waiting for browser login to complete...");
                                if ui.button("Cancel").clicked() {
                                    // Clear hint and close window; background task will timeout.
                                    ctx.memory_mut(|mem_mut| {
                                        mem_mut.data.remove::<String>(egui::Id::new("login_auth_url"));
                                    });
                                    self.show_login_window = false;
                                }
                            });
                        }
                        if let Some(err) = mem.data.get_temp::<String>(egui::Id::new("login_error")) {
                            ui.separator();
                            ui.colored_label(egui::Color32::LIGHT_RED, err);
                        }
                    });

                    ui.separator();
                    ui.label("Legacy Username/Password (dev/testing)");
                    ui.horizontal(|ui| {
                        ui.label("Username:");
                        ui.text_edit_singleline(&mut self.login_username);
                    });
                    ui.horizontal(|ui| {
                        ui.label("Password:");
                        ui.add(egui::TextEdit::singleline(&mut self.login_password).password(true));
                    });
                    if ui.button("Login").clicked() {
                        let username = self.login_username.clone();
                        let password = self.login_password.clone();
                        let api = self.api_client.clone();
                        let ctx2 = ctx.clone();
                        #[cfg(not(target_arch = "wasm32"))]
                        if let Some(handle) = &self.rt_handle {
                            handle.spawn(async move {
                                let res = api.auth_login(&username, &password).await;
                                ctx2.memory_mut(|mem| {
                                    mem.data.insert_temp(egui::Id::new("legacy_login_result"), res.map_err(|e| e.to_string()));
                                });
                                ctx2.request_repaint();
                            });
                        }
                        #[cfg(target_arch = "wasm32")]
                        {
                            wasm_bindgen_futures::spawn_local(async move {
                                let res = api.auth_login(&username, &password).await;
                                ctx2.memory_mut(|mem| {
                                    mem.data.insert_temp(egui::Id::new("legacy_login_result"), res.map_err(|e| e.to_string()));
                                });
                                ctx2.request_repaint();
                            });
                        }
                    }

                    // Helper: Login with GOOGLE_ID_TOKEN from environment (.env)
                    #[cfg(not(target_arch = "wasm32"))]
                    if ui.button("Login with Google (.env)").on_hover_text("Reads GOOGLE_ID_TOKEN from environment and logs in").clicked() {
                        if let Ok(id_token) = std::env::var("GOOGLE_ID_TOKEN") {
                            let api = self.api_client.clone();
                            let ctx2 = ctx.clone();
                            if let Some(handle) = &self.rt_handle {
                                handle.spawn(async move {
                                    let res = api.auth_google(&id_token).await;
                                    ctx2.memory_mut(|mem| {
                                        mem.data.insert_temp(egui::Id::new("login_result"), res.map_err(|e| e.to_string()));
                                    });
                                    ctx2.request_repaint();
                                });
                            }
                        } else {
                            self.last_error_message = Some("GOOGLE_ID_TOKEN not set in environment".into());
                        }
                    }

                    // Read any login result and persist token
                    let mut took = false;
                    ctx.memory_mut(|mem| {
                        let id = egui::Id::new("login_result");
                        if let Some(res) = mem.data.get_temp::<Result<(String, Option<String>), String>>(id) {
                            took = true;
                            match res {
                                Ok((token, username)) => {
                                    // Persist
                                    self.api_client.set_token(Some(token.clone()));
                                    self.auth_token = Some(token.clone());
                                    self.app_state.config.auth_token = Some(token);
                                    self.app_state.config.current_user = username;
                                    self.show_login_window = false;
                                    // Clear any auth url hint
                                    ctx.memory_mut(|mem_mut| {
                                        mem_mut.data.remove::<String>(egui::Id::new("login_auth_url"));
                                    });
                                }
                                Err(e) => {
                                    self.last_error_message = Some(format!("Login failed: {}", e));
                                }
                            }
                        }
                        mem.data.remove::<Result<(String, Option<String>), String>>(id);
                    });
                    if !took {
                        ctx.memory_mut(|mem| {
                            let id = egui::Id::new("legacy_login_result");
                            if let Some(res) = mem.data.get_temp::<Result<String, String>>(id) {
                                match res {
                                    Ok(token) => {
                                        self.api_client.set_token(Some(token.clone()));
                                        self.auth_token = Some(token.clone());
                                        self.app_state.config.auth_token = Some(token);
                                        self.app_state.config.current_user = self.login_username.clone().into();
                                        self.show_login_window = false;
                                    }
                                    Err(e) => {
                                        self.last_error_message = Some(format!("Login failed: {}", e));
                                    }
                                }
                            }
                            mem.data.remove::<Result<String, String>>(id);
                        });
                    }
                });
            if !open { self.show_login_window = false; }
        }

        // Central panel with portfolio application content
        egui::CentralPanel::default().show(ctx, |ui| {
            if let (Some(portfolios), Some(selected_name)) =
                (&self.app_state.portfolios, &self.selected_portfolio)
            {
                if let Some(portfolio) = portfolios.get(selected_name) {
                    // Portfolio is selected - render component tabs and main content
                    self.component_manager
                        .render_all(ui, portfolio, &self.app_state.config);
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

                        if self.app_state.portfolios.is_none()
                            || self.app_state.portfolios.as_ref().unwrap().is_empty()
                        {
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

        // No need for duplicate window rendering; handled in render_all
    }
}
