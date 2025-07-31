#![warn(clippy::all, rust_2018_idioms)]

pub mod app;
pub mod portfolio;
pub mod api;
pub mod components;
pub mod views;
pub mod state;

pub use app::TemplateApp;
