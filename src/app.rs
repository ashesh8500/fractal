use crate::::ApiClient;
use crate::components::ComponentManager;
use crate::state::AppState;
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
            api_client::new("http://localhost:8000/api/v1"),
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
            last_selected_portfolio: None,
            last_error_message: None,
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

    // ... (rest of the file unchanged; omitted for brevity)
}
