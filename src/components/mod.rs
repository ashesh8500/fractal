#![allow(clippy::needless_pass_by_value)]
//! Component system for modular UI rendering
//! 
//! This module defines the trait lifecycle. Each component receives a `Portfolio` and `Config` as parameters
//! following dependency injection principles.

use crate::portfolio::Portfolio;
use crate::state::Config;
use egui::Ui;

pub mod manager;
pub mod status;

pub use manager::ComponentManager;
pub use status::DataProviderStatusComponent;

/// Trait for UI components that render against a shared Portfolio and Config
pub trait PortfolioComponent {
    /// Render the component
    fn render(&mut self, ui: &mut Ui, portfolio: &Portfolio, config: &Config);
    
    /// Get component name for UI display
    fn name(&self) -> &str;
    
    /// Check if component window/panel is open
    fn is_open(&self) -> bool;
    
    /// Set component window/panel open state
    fn set_open(&mut self, open: bool);
    
    /// Get component category for organization
    fn category(&self) -> ComponentCategory {
        ComponentCategory::General
    }
    
    /// Check if component requires data to be meaningful
    fn requires_data(&self) -> bool {
        true
    }

    /// Optional hook: called when portfolio data (e.g., price history) was updated.
    /// Default is no-op; components can override to validate/reset internal state.
    fn on_data_updated(&mut self, _portfolio: &Portfolio) {}
}

#[derive(Debug, Clone, PartialEq)]
pub enum ComponentCategory {
    General,
    Charts,
    Tables,
    Analytics,
    Trading,
}
