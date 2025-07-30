//! Component system for modular UI rendering
//! 
//! This module defines the trait system for portfolio components and manages
//! their lifecycle. Each component receives a Portfolio and Config as parameters
//! following dependency injection principles.

use crate::portfolio::Portfolio;
use crate::state::Config;

pub mod manager;

pub use manager::ComponentManager;

/// Trait for all portfolio UI components
/// 
/// Components are pure render functions that take Portfolio + Config as input
/// and render their specific view. This follows functional programming principles
/// with immutable data flow.
pub trait PortfolioComponent {
    /// Render the component
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config);
    
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
}

#[derive(Debug, Clone, PartialEq)]
pub enum ComponentCategory {
    General,
    Charts,
    Tables,
    Analytics,
    Trading,
}
