# Agent Context

## Current State
**Phase 1: COMPLETED** ✅ - Portfolio_lib implemented with full dependency injection architecture and comprehensive testing.

## Key Snippets

### Architecture Overview
```
fractal/
├── portfolio_lib/          # Standalone Python library (can be used in notebooks)
├── backend_server/         # Lightweight FastAPI server using portfolio_lib
├── src/                    # Rust egui frontend (extends existing TemplateApp)
└── shared/                 # Type synchronization schemas
```

### Core Design Principles (CRITICAL)
1. **Preserve existing egui template structure** - extend TemplateApp, don't replace
2. **Dependency injection** - DataService protocol with yfinance/alphavantage implementations
3. **Portfolio-first design** - Portfolio class as single source of truth
4. **Component-based UI** - Components accept Portfolio + Config parameters
5. **Library-first approach** - Core logic in standalone package for notebooks
6. **Type safety** - Shared schemas between Rust frontend and Python backend

### Portfolio Class Interface
```python
class Portfolio:
    def __init__(self, name: str, holdings: Dict[str, float], data_service: DataService)
    
    @property
    def total_value(self) -> float
    @property 
    def current_weights(self) -> Dict[str, float]
    @property
    def risk_metrics(self) -> RiskMetrics
    
    def run_strategy(self, strategy_name: str, config: StrategyConfig) -> StrategyResult
    def run_backtest(self, strategy_name: str, config: BacktestConfig) -> BacktestResult
```

### DataService Protocol
```python
class DataService(Protocol):
    def fetch_price_history(self, symbols: List[str], period: str) -> pd.DataFrame
    def fetch_current_prices(self, symbols: List[str]) -> Dict[str, float]
```

### Component Architecture (Rust)
```rust
pub trait PortfolioComponent {
    fn render(&mut self, ui: &mut egui::Ui, portfolio: &Portfolio, config: &Config);
    fn name(&self) -> &str;
    fn is_open(&self) -> bool;
    fn set_open(&mut self, open: bool);
}
```

## Test Results
**Phase 1 COMPLETED** ✅ - All core functionality tested and working:
- **Unit Tests**: 11/11 passing (test_portfolio.py)
- **Integration Tests**: YFinance + AlphaVantage data providers working
- **Dependency Injection**: Both providers work seamlessly with Portfolio class
- **Data Consistency**: Standardized OHLCV format across providers
- **Strategy Framework**: Ready for implementation
- **Backtesting Framework**: Ready for implementation
- **Configuration System**: .env file + settings working

### Test Configuration
```bash
# Create .env file in portfolio_lib/
PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY="your_key_here"

# Run tests
pytest tests/test_portfolio.py -v                    # Unit tests
pytest tests/test_data_providers.py -v -m integration # Integration tests
python test_dependency_injection.py                   # Comprehensive test
```

## Next Instructions (Phase 2: Backend Server)
1. **Create backend_server structure** - FastAPI app using portfolio_lib
2. **Implement dependency injection** - Service injection in FastAPI
3. **Create REST API endpoints** - Portfolio CRUD, strategies, market data
4. **Add persistence layer** - SQLAlchemy for portfolio storage
5. **API validation** - Pydantic schemas
6. **Authentication** - Basic security layer

## Environment and tooling

### Current Setup
- **Rust**: egui 0.32, eframe 0.32 (existing template preserved)
- **Python**: FastAPI, pandas, numpy (to be added)
- **Package management**: Cargo (Rust), pyproject.toml (Python)
- **Target platforms**: Native (macOS/Linux/Windows) + WASM

### Dependencies to Add
```toml
# Cargo.toml additions (Phase 3)
[dependencies]
serde_json = "1.0"     # For API communication
reqwest = "0.11"       # HTTP client for API calls
tokio = "1.0"          # Async runtime

# pyproject.toml (Phase 1)
[dependencies]
pandas = "^2.0.0"
numpy = "^1.24.0"
yfinance = "^0.2.0"
alpha-vantage = "^2.3.0"
fastapi = "^0.100.0"   # For Phase 2
```

### Development Commands
```bash
# Test portfolio library (Phase 1)
cd portfolio_lib && python -m pytest tests/

# Run backend server (Phase 2)
cd backend_server && uvicorn app.main:app --reload

# Run Rust frontend (Phase 3+)
cargo run

# Build for web (Phase 3+)
trunk serve
```

## History
- **2025-07-30**: Architecture planning completed
- **Key decision**: Preserve existing egui template, extend rather than replace
- **Architecture choice**: Modular library-first approach with dependency injection
- **Current focus**: Phase 1 - Core portfolio_lib implementation

## Critical Notes for Development
- **DO NOT** overwrite existing src/app.rs or src/lib.rs - extend them
- **MAINTAIN** the TemplateApp structure and patterns
- **ENSURE** portfolio_lib can be used independently in Jupyter notebooks
- **IMPLEMENT** proper dependency injection from the start
- **TEST** each component independently before integration
