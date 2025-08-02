use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::Portfolio;
use crate::state::Config;

/// Displays data provider status and helpful diagnostics.
pub struct DataProviderStatusComponent {
    is_open: bool,
}

impl DataProviderStatusComponent {
    pub fn new() -> Self {
        Self { is_open: true }
    }
}

impl Default for DataProviderStatusComponent {
    fn default() -> Self {
        Self::new()
    }
}

impl PortfolioComponent for DataProviderStatusComponent {
    fn render(&mut self, ui: &mut egui::Ui, _portfolio: &Portfolio, config: &Config) {
        ui.heading("Data Provider Status");

        ui.separator();

        // Provider mode
        let (mode_label, mode_color) = if config.use_native_provider {
            ("Native (Alpha Vantage)", egui::Color32::from_rgb(0, 180, 0))
        } else {
            ("Backend", egui::Color32::from_rgb(160, 120, 0))
        };
        ui.horizontal(|ui| {
            ui.strong("Mode:");
            ui.colored_label(mode_color, mode_label);
        });

        // API key status (only relevant in native mode)
        if config.use_native_provider {
            let has_key = config
                .alphavantage_api_key
                .as_deref()
                .map(|s| !s.is_empty())
                .unwrap_or(false);

            let (key_text, key_color) = if has_key {
                ("API key: Configured", egui::Color32::from_rgb(0, 160, 0))
            } else {
                ("API key: Missing", egui::Color32::from_rgb(200, 0, 0))
            };

            ui.horizontal(|ui| {
                ui.strong("Alpha Vantage:");
                ui.colored_label(key_color, key_text);
            });

            ui.add_space(4.0);
            if !has_key {
                ui.label("Set the environment variable ALPHAVANTAGE_API_KEY before launching.");
                ui.monospace("export ALPHAVANTAGE_API_KEY=your_key_here");
            } else {
                ui.weak("Tip: Use 'Fetch Price History' to load data for the selected portfolio.");
            }
        } else {
            ui.weak("Tip: Switch to Native mode from the Portfolio menu or left panel to fetch directly from Alpha Vantage.");
        }

        ui.separator();
        ui.label("This panel helps verify your current data provider configuration.");
    }

    fn name(&self) -> &str {
        "Provider Status"
    }

    fn is_open(&self) -> bool {
        self.is_open
    }

    fn set_open(&mut self, open: bool) {
        self.is_open = open;
    }

    fn category(&self) -> ComponentCategory {
        ComponentCategory::General
    }

    // This component does not require portfolio data to be useful.
    fn requires_data(&self) -> bool {
        false
    }
}
