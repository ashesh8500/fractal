//! Integration tests for the portfolio management system
//! 
//! These tests verify the interaction between frontend components,
//! API client, and backend services.

use fractal::TemplateApp;
use std::collections::HashMap;

#[cfg(test)]
mod tests {
    use super::*;
    
    /// Test portfolio creation and state management
    #[test]
    fn test_portfolio_state_management() {
        let mut app = TemplateApp::default();
        
        // Initially no portfolios
        assert!(app.app_state.portfolios.is_none());
        assert!(!app.app_state.has_portfolios());
        
        // Create a test portfolio
        let mut portfolio = crate::portfolio::Portfolio::new("Test Portfolio".to_string());
        portfolio.holdings.insert("AAPL".to_string(), 10.0);
        portfolio.holdings.insert("MSFT".to_string(), 5.0);
        portfolio.total_value = 1000.0;
        
        // Add portfolio to state
        app.app_state.set_portfolio(portfolio);
        
        // Verify portfolio was added
        assert!(app.app_state.has_portfolios());
        assert_eq!(app.app_state.portfolio_names().len(), 1);
        assert!(app.app_state.portfolio_names().contains(&"Test Portfolio".to_string()));
        
        // Verify portfolio can be retrieved
        let retrieved = app.app_state.get_portfolio("Test Portfolio");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().name, "Test Portfolio");
        assert_eq!(retrieved.unwrap().holdings.len(), 2);
    }
    
    /// Test portfolio component rendering requirements
    #[test]
    fn test_portfolio_component_requirements() {
        use crate::components::PortfolioComponent;
        use crate::views::DashboardComponent;
        
        let mut dashboard = DashboardComponent::new();
        
        // Test component properties
        assert_eq!(dashboard.name(), "Dashboard");
        assert!(dashboard.is_open()); // Dashboard starts open
        assert!(dashboard.requires_data());
        
        // Test state changes
        dashboard.set_open(false);
        assert!(!dashboard.is_open());
        
        dashboard.set_open(true);
        assert!(dashboard.is_open());
    }
    
    /// Test portfolio data validation
    #[test]
    fn test_portfolio_data_validation() {
        let portfolio = crate::portfolio::Portfolio::new("Empty Portfolio".to_string());
        
        // Empty portfolio should not have data
        assert!(!portfolio.has_data());
        assert_eq!(portfolio.symbols().len(), 0);
        assert_eq!(portfolio.total_value, 0.0);
        
        let mut portfolio_with_data = crate::portfolio::Portfolio::new("Valid Portfolio".to_string());
        portfolio_with_data.holdings.insert("AAPL".to_string(), 10.0);
        portfolio_with_data.total_value = 1000.0;
        portfolio_with_data.current_weights.insert("AAPL".to_string(), 1.0);
        
        // Portfolio with data should be valid
        assert!(portfolio_with_data.has_data());
        assert_eq!(portfolio_with_data.symbols().len(), 1);
        assert!(portfolio_with_data.symbols().contains(&"AAPL".to_string()));
        
        // Test position value calculation
        let position_value = portfolio_with_data.get_position_value("AAPL");
        assert!(position_value.is_some());
        assert_eq!(position_value.unwrap(), 1000.0); // total_value * weight
    }
    
    /// Test async state management
    #[test]
    fn test_async_state_management() {
        use std::sync::{Arc, Mutex};
        
        let async_state = Arc::new(Mutex::new(crate::app::AsyncState::default()));
        
        // Test connection result
        {
            let mut state = async_state.lock().unwrap();
            state.connection_result = Some(Ok(()));
        }
        
        {
            let state = async_state.lock().unwrap();
            assert!(state.connection_result.is_some());
            assert!(state.connection_result.as_ref().unwrap().is_ok());
        }
        
        // Test portfolio result
        {
            let mut state = async_state.lock().unwrap();
            state.portfolio_result = Some(Ok("Test Portfolio".to_string()));
        }
        
        {
            let state = async_state.lock().unwrap();
            assert!(state.portfolio_result.is_some());
            let result = state.portfolio_result.as_ref().unwrap();
            assert!(result.is_ok());
            assert_eq!(result.as_ref().unwrap(), "Test Portfolio");
        }
    }
    
    /// Test component manager functionality
    #[test]
    fn test_component_manager() {
        use crate::components::ComponentManager;
        
        let manager = ComponentManager::new();
        
        // Should have registered components
        assert_eq!(manager.components.len(), 4); // Dashboard, Charts, Tables, Candles
        
        // Test component categories
        use crate::components::ComponentCategory;
        let general_components = manager.get_components_by_category(ComponentCategory::General);
        let chart_components = manager.get_components_by_category(ComponentCategory::Charts);
        let table_components = manager.get_components_by_category(ComponentCategory::Tables);
        
        assert!(!general_components.is_empty());
        assert!(!chart_components.is_empty());
        assert!(!table_components.is_empty());
    }
    
    /// Test API client error handling
    #[tokio::test]
    async fn test_api_client_error_handling() {
        use crate::api::{ApiClient, ApiError};
        
        // Test with invalid URL
        let client = ApiClient::new("http://invalid-url:9999/api/v1");
        
        let result = client.test_health().await;
        assert!(result.is_err());
        
        match result.unwrap_err() {
            ApiError::Network(_) => {
                // Expected network error
            }
            _ => panic!("Expected network error"),
        }
    }
    
    /// Test portfolio serialization/deserialization
    #[test]
    fn test_portfolio_serialization() {
        let mut portfolio = crate::portfolio::Portfolio::new("Serialization Test".to_string());
        portfolio.holdings.insert("AAPL".to_string(), 10.0);
        portfolio.holdings.insert("MSFT".to_string(), 5.0);
        portfolio.total_value = 1500.0;
        
        // Test JSON serialization
        let json = serde_json::to_string(&portfolio).unwrap();
        assert!(json.contains("Serialization Test"));
        assert!(json.contains("AAPL"));
        assert!(json.contains("MSFT"));
        
        // Test deserialization
        let deserialized: crate::portfolio::Portfolio = serde_json::from_str(&json).unwrap();
        assert_eq!(deserialized.name, portfolio.name);
        assert_eq!(deserialized.holdings, portfolio.holdings);
        assert_eq!(deserialized.total_value, portfolio.total_value);
    }
    
    /// Test configuration management
    #[test]
    fn test_configuration_management() {
        use crate::state::{Config, ChartTheme};
        
        let config = Config::default();
        
        assert_eq!(config.api_base_url, "http://localhost:8000/api/v1");
        assert_eq!(config.default_data_provider, "yfinance");
        assert_eq!(config.refresh_interval_seconds, 300);
        assert!(matches!(config.chart_theme, ChartTheme::Auto));
    }
    
    /// Test error message formatting
    #[test]
    fn test_error_message_formatting() {
        use crate::api::ApiError;
        
        let network_error = ApiError::Network(reqwest::Error::from(reqwest::ErrorKind::Request));
        let backend_error = ApiError::Backend("Test backend error".to_string());
        
        assert!(network_error.to_string().contains("Network error"));
        assert!(backend_error.to_string().contains("Backend error"));
        assert!(backend_error.to_string().contains("Test backend error"));
    }
}

// Make AsyncState public for testing
pub use crate::app::AsyncState;
