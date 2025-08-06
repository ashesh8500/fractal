use egui::{Color32, Id, Stroke, Ui};
use egui_plot::{Legend, Line, Plot, PlotPoints};
use crate::components::{ComponentCategory, PortfolioComponent};
use crate::portfolio::{Portfolio, PricePoint};
use crate::state::Config;

/// ChartsComponent renders simple demo-style line charts based on price history.
/// IDs are derived from the current Ui id and namespaced to avoid collisions.
pub struct ChartsComponent {
    is_open: bool,
    selected_symbol: Option<String>,
}

impl ChartsComponent {
    pub fn new() -> Self {
        Self {
            is_open: true,
            selected_symbol: None,
        }
    }
}

impl PortfolioComponent for ChartsComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, _config: &Config) {
        if !self.is_open {
            return;
        }

        // Derive a unique, stable base Id from the current Ui path for this component.
        let base_id: Id = ui.id().with("component::charts");
        let window_id = base_id.with("window");

        egui::Window::new("Charts")
            .id(window_id)
            .open(&mut self.is_open)
            .default_width(900.0)
            .default_height(560.0)
            .show(ui.ctx(), |ui| {
                // Within the window, derive a new base from the inner Ui to avoid clashes
                let _base_id = ui.id().with("component::charts::window");

                ui.heading("Portfolio Charts (Demo Line Plot)");
                ui.separator();

                let mut symbols: Vec<String> = portfolio.holdings.keys().cloned().collect();
                symbols.sort();

                if symbols.is_empty() {
                    ui.label("No holdings found. Add holdings to view charts.");
                    return;
                }

                ui.horizontal(|ui| {
                    ui.label("Symbol:");
                    // Use unique salt for ComboBox derived from the local Ui path
                    let combo_id = ui.id().with("charts_symbol_combo");
                    egui::ComboBox::from_id_salt(combo_id)
                        .selected_text(
                            self.selected_symbol
                                .as_ref()
                                .map(|s| s.as_str())
                                .unwrap_or("Select symbol"),
                        )
                        .show_ui(ui, |ui| {
                            if ui
                                .selectable_label(self.selected_symbol.is_none(), "Select symbol")
                                .clicked()
                            {
                                self.selected_symbol = None;
                            }
                            for sym in &symbols {
                                let selected = self.selected_symbol.as_deref() == Some(sym.as_str());
                                if ui.selectable_label(selected, sym).clicked() {
                                    self.selected_symbol = Some(sym.clone());
                                }
                            }
                        });
                });

                ui.add_space(8.0);

                if let Some(sym) = self.selected_symbol.clone() {
                    if let Some(series) = portfolio.get_price_history(&sym) {
                        render_line_plot(ui, &sym, series);
                    } else {
                        ui.colored_label(Color32::YELLOW, "No price history for selected symbol.");
                    }
                } else {
                    ui.label("Choose a symbol to display its chart.");
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

fn render_line_plot(ui: &mut Ui, symbol: &str, data: &[PricePoint]) {
    if data.is_empty() {
        ui.label("No data points available.");
        return;
    }

    // Convert to PlotPoints using the index as x (demo-style).
    let points: PlotPoints<'_> = PlotPoints::from_iter(
        data.iter()
            .enumerate()
            .map(|(i, p)| [i as f64, p.close]),
    );

    // Show a quick info row with last price and change
    if let (Some(first), Some(last)) = (data.first(), data.last()) {
        let abs = last.close - first.close;
        let pct = (abs / first.close) * 100.0;
        let color = if abs >= 0.0 { Color32::GREEN } else { Color32::RED };
        ui.horizontal(|ui| {
            ui.label(format!("{symbol}"));
            ui.separator();
            ui.label(format!("Last: {:.2}", last.close));
            ui.colored_label(color, format!("{:+.2} ({:+.2}%)", abs, pct));
        });
    }

    // Plot id derived from the local Ui id to avoid collisions with other components/windows
    let plot_id = ui.id().with(("charts_plot", symbol));
    Plot::new(plot_id)
        .legend(Legend::default())
        .view_aspect(2.2)
        .allow_scroll(false)
        .allow_boxed_zoom(true)
        .show(ui, |plot_ui| {
            let color = Color32::from_rgb(80, 160, 255);
            plot_ui.line(
                Line::new(points)
                    .name(format!("{symbol} Close"))
                    .color(color)
                    .stroke(Stroke::new(2.0, color)),
            );
        });
}
