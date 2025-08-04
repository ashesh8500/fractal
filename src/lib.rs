#![warn(clippy::all, rust_2018_idioms)]

pub mod app;
pub mod portfolio;
pub mod api;
pub mod components;
pub mod views;
pub mod state;

// Export the `ui` module so paths like `crate::ui::widgets::window::WindowPanel` resolve.
pub mod ui;

pub use app::TemplateApp;
