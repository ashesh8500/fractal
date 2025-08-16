#![warn(clippy::all, rust_2018_idioms)]

#[cfg(target_arch = "wasm32")]
compile_error!("WASM builds disabled for main fractal crate. Use refactor_ui crate for web frontend instead.");

#[cfg(not(target_arch = "wasm32"))]
pub mod app;
#[cfg(not(target_arch = "wasm32"))]
pub mod portfolio;
#[cfg(not(target_arch = "wasm32"))]
pub mod api;
#[cfg(not(target_arch = "wasm32"))]
pub mod components;
#[cfg(not(target_arch = "wasm32"))]
pub mod views;
#[cfg(not(target_arch = "wasm32"))]
pub mod state;

// Export the `ui` module so paths like `crate::ui::widgets::window::WindowPanel` resolve.
#[cfg(not(target_arch = "wasm32"))]
pub mod ui;

#[cfg(not(target_arch = "wasm32"))]
pub use app::TemplateApp;
