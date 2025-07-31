# Agent Context

## Current State
**Phase 3: IN PROGRESS** 🚧 - Frontend foundation improved. UI layout and rendering issues fixed: component window sizing, OHLC candlestick rendering, portfolio panel adjustments. Web version updated.

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
**Phase 3 MAJOR FIXES** ✅ - Frontend issues resolved:
- **Price History**: Backend now fetches and returns historical data in portfolio responses
- **Widget IDs**: Fixed ComboBox and Plot ID conflicts using unique identifiers
- **Window Management**: Component windows can now be properly closed
- **API Integration**: Frontend successfully communicates with backend
- **Data Flow**: Price history properly flows from yfinance → backend → frontend
- **UI Components**: Dashboard, Charts, Tables, and Candles components working

### Test Configuration
```bash
# Create .env file in portfolio_lib/
PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY="your_key_here"

# Run tests
pytest tests/test_portfolio.py -v                    # Unit tests
pytest tests/test_data_providers.py -v -m integration # Integration tests
python test_dependency_injection.py                   # Comprehensive test
```

## Next Instructions (Phase 3 Completion → Phase 4)
1. **Complete and Polish Phase 3** - Finalize integration testing, ensure smooth operation
2. **Implement Hover Tooltips** - Add hover functionality to candlestick charts to display OHLC values
3. **Start Phase 4** - Implement UI components and features in the next phase
4. **Portfolio CRUD UI** - Add UI forms for creating and editing portfolios
5. **Advanced Charting** - Implement additional chart visualizations and options
6. **Responsive Layout** - Improve layout responsiveness for various devices

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
- **2025-07-30**: Architecture planning completed, Phase 1 & 2 completed
- **2025-07-31**: Phase 3 major issues fixed - price history, widget IDs, window management
- **Key fixes**: Added price history to backend API, fixed UI component ID conflicts
- **Architecture success**: Clean separation of concerns, data flows properly through all layers
- **Current focus**: Phase 3 completion and transition to Phase 4

## Critical Notes for Development
- **DO NOT** overwrite existing src/app.rs or src/lib.rs - extend them
- **MAINTAIN** the TemplateApp structure and patterns
- **ENSURE** portfolio_lib can be used independently in Jupyter notebooks
- **IMPLEMENT** proper dependency injection from the start
- **TEST** each component independently before integration
