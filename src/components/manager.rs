//! Component manager for organizing and rendering portfolio components

use super::{PortfolioComponent, ComponentCategory};
use crate::portfolio::Portfolio;
use crate::state::Config;
use crate::views::{DashboardComponent, ChartsComponent, TablesComponent, CandlesComponent};

pub struct ComponentManager {
    components: Vec<Box<dyn PortfolioComponent>>,
}

impl ComponentManager {
    pub fn new() -> Self {
        let mut manager = Self {
            components: Vec::new(),
        };
        
        // Register all available components
        manager.register_component(Box::new(DashboardComponent::new()));
        manager.register_component(Box::new(ChartsComponent::new()));
        manager.register_component(Box::new(TablesComponent::new()));
        manager.register_component(Box::new(CandlesComponent::new()));
        
        manager
    }
    
    pub fn register_component(&mut self, component: Box<dyn PortfolioComponent>) {
        self.components.push(component);
    }
    
    pub fn render_all(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config) {
        // Create tabs for different component categories
        egui::TopBottomPanel::top("component_tabs").show_inside(ui, |ui| {
            ui.horizontal(|ui| {
                for component in &mut self.components {
                    let name = component.name();
                    let is_open = component.is_open();
                    
                    if ui.selectable_label(is_open, name).clicked() {
                        component.set_open(!is_open);
                    }
                }
            });
        });
        
        // Render open components
        for component in &mut self.components {
            if component.is_open() {
                // Only render if component doesn't require data or portfolio has data
                if !component.requires_data() || portfolio.has_data() {
                    egui::Window::new(component.name())
                        .open(&mut true)
                        .show(ui.ctx(), |ui| {
                            component.render(ui, portfolio, config);
                        });
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
