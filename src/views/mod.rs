#![allow(clippy::needless_pass_by_value)]
//! Modular view components for different aspects of portfolio visualization
//! 
//! Each component is implemented in a separate file and follows the PortfolioComponent
//! trait. Components receive Portfolio + Config as parameters and render their
//! specific view using pure functions.

pub mod dashboard;
pub mod charts;
pub mod tables;
pub mod candles;

pub use dashboard::DashboardComponent;
pub use charts::ChartsComponent;
pub use tables::TablesComponent;
pub use candles::CandlesComponent;
