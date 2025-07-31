# Portfolio Application Architecture Plan

## Overview

This document outlines the architecture for porting and refactoring the portfolio application into a clean, modular system that eliminates bloat and type mismatches while providing maximum flexibility and reusability.

## Core Design Principles

1. **Single Source of Truth**: Portfolio class as the central data model
2. **Type Safety**: Consistent types across frontend/backend boundary
3. **Component-Based UI**: Reusable UI components that accept `Portfolio` and `Config` parameters
4. **Separation of Concerns**: Clean backend API structure separate from frontend
5. **Dependency Injection**: Pluggable services for data providers, strategies, and other services
6. **Library First**: Core logic as standalone Python library for notebooks and scripts
7. **Lean & Focused**: Remove bloat, keep only essential features

## System Architecture

```
fractal/
├── portfolio_lib/          # Core Python library (standalone package)
├── backend_server/         # FastAPI server using the library
├── src/                    # Rust egui frontend
├── shared/                 # JSON schemas for type synchronization
├── Cargo.toml
└── README.md
```

## 1. Core Python Library: `portfolio_lib`

### Purpose
- Standalone, installable Python package
- Contains all financial logic and computations
- Can be used independently in Jupyter notebooks, scripts, or other applications
- Fully testable in isolation

### Directory Structure
```
portfolio_lib/
├── portfolio_lib/
│   ├── __init__.py
│   ├── config.py                     # Library configuration
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── portfolio.py              # Core Portfolio class
│   │   ├── market_data.py            # Data value objects (PriceData, OHLCV, etc.)
│   │   └── strategy.py               # Strategy, Trade, and Backtest result models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   │
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Abstract DataService Protocol
│   │   │   ├── yfinance.py           # yfinance implementation
│   │   │   └── alphavantage.py       # AlphaVantage implementation
│   │   │
│   │   ├── backtesting/
│   │   │   ├── __init__.py
│   │   │   └── engine.py             # Backtesting engine
│   │   │
│   │   ├── strategy/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Abstract Strategy Protocol
│   │   │   └── engine.py             # Strategy execution engine
│   │   │
│   │   └── charts/
│   │       ├── __init__.py
│   │       ├── base.py               # Abstract Chart Generator Protocol
│   │       └── plotly.py             # Plotly implementation
│   │
│   └── utils/
│       ├── __init__.py
│       ├── calculations.py           # Financial calculations
│       └── validation.py             # Data validation utilities
│
├── pyproject.toml                    # Package configuration
├── tests/                            # Comprehensive test suite
│   ├── test_portfolio.py
│   ├── test_data_services.py
│   └── test_strategies.py
└── README.md
```

### Key Classes and Interfaces

#### Portfolio Class
```python
class Portfolio:
    def __init__(self, 
                 name: str, 
                 holdings: Dict[str, float],
                 data_service: DataService,
                 strategy_engine: StrategyEngine = None):
        
    # Core Properties
    @property
    def total_value(self) -> float
    @property
    def current_weights(self) -> Dict[str, float]
    @property
    def price_history(self) -> pd.DataFrame
    @property
    def risk_metrics(self) -> RiskMetrics
    
    # Methods
    def run_strategy(self, strategy_name: str, config: StrategyConfig) -> StrategyResult
    def run_backtest(self, strategy_name: str, config: BacktestConfig) -> BacktestResult
    def get_performance_metrics(self) -> PerformanceMetrics
    def refresh_data(self) -> None
    def add_holding(self, symbol: str, shares: float) -> None
    def remove_holding(self, symbol: str) -> None
```

#### Data Service Protocol
```python
class DataService(Protocol):
    def fetch_price_history(self, symbols: List[str], period: str) -> pd.DataFrame
    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]
    def fetch_fundamental_data(self, symbol: str) -> FundamentalData
    def is_market_open(self) -> bool
```

#### Strategy Protocol
```python
class Strategy(Protocol):
    def generate_signals(self, portfolio: Portfolio, config: StrategyConfig) -> List[Trade]
    def validate_config(self, config: StrategyConfig) -> bool
    def get_description(self) -> str
```

## 2. API Server: `backend_server`

### Purpose
- Lightweight FastAPI server
- Exposes `portfolio_lib` functionality over REST API
- Handles authentication, validation, and persistence
- No business logic - only orchestration

### Directory Structure
```
backend_server/
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app initialization
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   ├── portfolios.py         # Portfolio CRUD operations
│   │   │   ├── strategies.py         # Strategy operations
│   │   │   ├── backtesting.py        # Backtesting operations
│   │   │   └── market_data.py        # Market data operations
│   │   │
│   │   └── schemas.py                # Pydantic schemas for API validation
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # Server configuration
│   │   ├── dependencies.py           # FastAPI dependency injection
│   │   └── security.py               # Authentication logic
│   │
│   └── db/
│       ├── __init__.py
│       ├── models.py                 # SQLAlchemy models for persistence
│       └── session.py                # Database session management
│
├── requirements.txt
├── Dockerfile
└── README.md
```

### API Endpoints
```
# Portfolio Management
GET    /api/portfolios                    # List all portfolios
POST   /api/portfolios                    # Create portfolio
GET    /api/portfolios/{id}               # Get portfolio details
PUT    /api/portfolios/{id}               # Update portfolio
DELETE /api/portfolios/{id}               # Delete portfolio

# Strategy Operations
POST   /api/portfolios/{id}/strategy      # Run strategy
GET    /api/strategies                    # List available strategies
GET    /api/strategies/{name}/config      # Get strategy configuration schema

# Backtesting
POST   /api/portfolios/{id}/backtest      # Run backtest
GET    /api/portfolios/{id}/backtests     # List backtest history

# Analytics
GET    /api/portfolios/{id}/risk-metrics  # Get risk metrics
GET    /api/portfolios/{id}/performance   # Get performance metrics
POST   /api/portfolios/{id}/refresh       # Refresh market data

# Market Data
GET    /api/market-data/{symbols}         # Get market data
GET    /api/market-data/status            # Get data source status
```

### Dependency Injection Example
```python
# app/core/dependencies.py
def get_data_service() -> DataService:
    if settings.DATA_PROVIDER == "yfinance":
        return YFinanceDataService()
    elif settings.DATA_PROVIDER == "alphavantage":
        return AlphaVantageDataService(api_key=settings.AV_API_KEY)
    raise ValueError("Invalid data provider configured")

def get_strategy_engine() -> StrategyEngine:
    return StrategyEngine(strategies=load_strategies())

# Usage in endpoint
@router.get("/{portfolio_id}")
def get_portfolio_details(
    portfolio_id: str,
    data_service: DataService = Depends(get_data_service)
):
    portfolio = Portfolio.load(portfolio_id, data_service=data_service)
    return portfolio.to_dict()
```

## 3. Frontend: Rust + egui

### Directory Structure
```
src/
├── main.rs                           # Entry point
├── lib.rs                            # Library exports
├── app.rs                            # Main app logic
│
├── models/
│   ├── mod.rs
│   ├── portfolio.rs                  # Portfolio struct (mirrors Python)
│   ├── config.rs                     # Configuration structs
│   ├── market_data.rs                # Market data types
│   └── strategy.rs                   # Strategy result types
│
├── components/
│   ├── mod.rs                        # Component trait and manager
│   ├── portfolio_dashboard.rs        # Main portfolio overview
│   ├── price_charts.rs               # Financial charts component
│   ├── risk_dashboard.rs             # Risk metrics visualization
│   ├── backtest_analyzer.rs          # Backtest results analysis
│   ├── strategy_analyzer.rs          # Strategy results visualization
│   ├── data_status.rs                # Data source status display
│   └── settings.rs                   # Application settings
│
├── services/
│   ├── mod.rs
│   ├── api_client.rs                 # Backend API client
│   └── state_manager.rs              # Application state management
│
├── ui/
│   ├── mod.rs
│   ├── widgets/
│   │   ├── mod.rs
│   │   ├── scrollable_table.rs       # Enhanced table with scroll and selection
│   │   ├── resizable_panel.rs        # Panel with resize handle
│   │   ├── chart_panel.rs            # Chart container with zoom/pan
│   │   └── metric_card.rs            # Elegant metric display cards
│   │
│   └── layouts/
│       ├── mod.rs
│       ├── grid_layout.rs            # Responsive grid system
│       ├── strip_layout.rs           # Strip-based layouts
│       └── panel_system.rs           # Advanced panel management
│
└── utils/
    ├── mod.rs
    ├── formatting.rs                 # Value formatting utilities
    ├── colors.rs                     # Color schemes and themes
    └── ui_helpers.rs                 # UI utility functions
```

### Component Architecture
```rust
pub trait PortfolioComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config);
    fn name(&self) -> &str;
    fn is_open(&self) -> bool;
    fn set_open(&mut self, open: bool);
}

pub struct ComponentManager {
    portfolio_dashboard: PortfolioDashboard,
    price_charts: PriceCharts,
    risk_dashboard: RiskDashboard,
    backtest_analyzer: BacktestAnalyzer,
    strategy_analyzer: StrategyAnalyzer,
    data_status: DataStatus,
}

impl ComponentManager {
    pub fn render_all(&mut self, ctx: &Context, portfolio: &Portfolio, config: &Config) {
        // Render all components with shared portfolio and config
    }
}
```

## 4. Type Synchronization

### Shared Schema Generation
```
shared/
├── schemas/
│   ├── portfolio.schema.json         # Generated from Pydantic models
│   ├── config.schema.json
│   ├── market_data.schema.json
│   └── strategy.schema.json
│
└── generate_types.py                 # Script to generate Rust types from schemas
```

### Type Generation Workflow
1. Define Pydantic models in `backend_server/app/api/schemas.py`
2. Generate JSON schemas from Pydantic models
3. Use code generation to create corresponding Rust structs
4. Ensure type safety across the frontend/backend boundary

## 5. Development Phases

### Phase 1: Core Foundation
- [ ] Set up `portfolio_lib` package structure
- [ ] Implement core Portfolio class with dependency injection
- [ ] Create DataService abstractions and implementations (yfinance, alphavantage)
- [ ] Basic unit tests for core functionality

### Phase 2: Backend Server
- [ ] Set up FastAPI server with dependency injection
- [ ] Implement core API endpoints
- [ ] Add persistence layer
- [ ] API integration tests

### Phase 3: Frontend Foundation (✅ COMPLETED)
- [x] Set up Rust project structure
- [x] Implement type synchronization
- [x] Create basic API client
- [x] Main app shell and state management
- [x] Fix UI layout issues (window constraints, panel sizing)
- [x] Implement proper candlestick rendering with BoxPlot API
- [x] Resolve widget ID conflicts
- [x] Add price history fetching from backend

### Phase 4: Core UI Components (🚧 IN PROGRESS)
- [ ] Enhance portfolio dashboard with egui demo patterns
- [ ] Implement advanced price charts with technical indicators
- [ ] Create elegant tables with proper scrolling and striping
- [ ] Add interactive panels with resize capabilities
- [ ] Implement modals and popups for forms
- [ ] Add tooltips and hover interactions

### Phase 5: Advanced Features
- [ ] Port risk dashboard and backtest analyzer
- [ ] Add strategy execution capabilities
- [ ] Performance optimization
- [ ] Comprehensive error handling

### Phase 6: Polish & Testing
- [ ] End-to-end testing
- [ ] Documentation
- [ ] Performance benchmarks
- [ ] Deployment configuration

## Benefits of This Architecture

### Modularity
- Core logic separated into reusable library
- Pluggable services via dependency injection
- Independent testing and development

### Type Safety
- Shared schemas eliminate type mismatches
- Compile-time checks in Rust frontend
- Runtime validation in Python backend

### Maintainability
- Clear separation of concerns
- Consistent patterns throughout
- Easy to extend and modify

### Performance
- Lean codebase without bloat
- Efficient data structures
- Optimized for both development and runtime

### Developer Experience
- Library can be used in notebooks for experimentation
- Clear interfaces and documentation
- Hot-reloading during development

## Next Steps

1. **Approve this plan** and any modifications needed
2. **Phase 1**: Start with `portfolio_lib` core implementation
3. **Iterative development** with frequent testing and validation
4. **Regular reviews** to ensure architecture goals are met

This architecture provides a solid foundation for a maintainable, extensible, and high-performance portfolio management system.
