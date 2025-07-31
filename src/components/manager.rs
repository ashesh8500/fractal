//! Component manager for organizing and rendering portfolio components

use super::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;
use crate::views::{DashboardComponent, ChartsComponent, TablesComponent, CandlesComponent};

pub struct ComponentManager {
    pub components: Vec<Box<dyn PortfolioComponent>>,
    // Remember which windows are open without losing the component internal state
    window_open: Vec<bool>,
}

impl ComponentManager {
    pub fn new() -> Self {
        let mut manager = Self {
            components: Vec::new(),
            window_open: Vec::new(),
        };
        
        // Register all available components
        manager.register_component(Box::new(DashboardComponent::new()));
        manager.register_component(Box::new(ChartsComponent::new()));
        manager.register_component(Box::new(TablesComponent::new()));
        manager.register_component(Box::new(CandlesComponent::new()));
        
        manager
    }
    
    pub fn register_component(&mut self, component: Box<dyn PortfolioComponent>) {
        self.window_open.push(component.is_open());
        self.components.push(component);
    }
    
    pub fn render_all(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config) {
        // Create tabs/strip of component toggles (demo-like top bar)
        egui::TopBottomPanel::top("component_tabs").show_inside(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.spacing_mut().item_spacing.x = 6.0;
                for (idx, component) in self.components.iter_mut().enumerate() {
                    let name = component.name();
                    let is_open = self.window_open.get(idx).copied().unwrap_or(component.is_open());
                    let button = ui.selectable_label(is_open, name);
                    if button.clicked() {
                        let new = !is_open;
                        self.window_open[idx] = new;
                        component.set_open(new);
                    }
                }
            });
        });
        
        // Render open components in windows (demo-like detachable)
        for (idx, component) in self.components.iter_mut().enumerate() {
            if self.window_open.get(idx).copied().unwrap_or(component.is_open()) {
                let mut open_state = true;
                egui::Window::new(component.name())
                    .open(&mut open_state)
                    .show(ui.ctx(), |ui_win| {
                        // Only render if component doesn't require data or portfolio has data
                        if !component.requires_data() || portfolio.has_data() {
                            component.render(ui_win, portfolio, config);
                        } else {
                            ui_win.weak("No data available for this component.");
                        }
                    });
                if !open_state {
                    self.window_open[idx] = false;
                    component.set_open(false);
                }
            }
        }
    }
    
    pub fn get_components_by_category(&self, category: ComponentCategory) -> Vec<&str> {
        self.components
            .iter()
            .filter(|c| c.category() == category)
            .map(|c| c.name())
            .collect()
    }
}

impl Default for ComponentManager {
    fn default() -> Self {
        Self::new()
    }
}
