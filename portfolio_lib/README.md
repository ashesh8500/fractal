# Portfolio Library

A standalone Python library for portfolio management and financial analysis with dependency injection architecture.

## Features

- **Portfolio Management**: Create and manage investment portfolios
- **Market Data Integration**: Pluggable data services (yfinance, alphavantage)
- **Risk Analysis**: Calculate volatility, Sharpe ratio, VaR, and drawdown metrics
- **Performance Analytics**: Track returns, benchmark comparisons, and performance metrics
- **Dependency Injection**: Flexible architecture for easy testing and extension
- **Notebook Ready**: Designed for use in Jupyter notebooks and scripts

## Installation

```bash
pip install portfolio-lib
```

For development:
```bash
pip install portfolio-lib[dev]
```

## Quick Start

```python
from portfolio_lib import Portfolio, YFinanceDataService

# Create a data service
data_service = YFinanceDataService()

# Create a portfolio
portfolio = Portfolio(
    name="My Portfolio",
    holdings={"AAPL": 100, "GOOGL": 50, "MSFT": 75},
    data_service=data_service
)

# Get portfolio metrics
print(f"Total Value: ${portfolio.total_value:,.2f}")
print(f"Current Weights: {portfolio.current_weights}")

# Risk analysis
risk_metrics = portfolio.risk_metrics
print(f"Volatility: {risk_metrics.volatility:.2%}")
print(f"Sharpe Ratio: {risk_metrics.sharpe_ratio:.2f}")

# Performance analysis
perf_metrics = portfolio.performance_metrics
print(f"Total Return: {perf_metrics.total_return:.2%}")
```

## Architecture

The library is built with dependency injection principles:

- **DataService Protocol**: Abstract interface for market data providers
- **Portfolio Class**: Core portfolio logic with injected data service
- **Pluggable Services**: Easy to swap data providers or add new ones

## Data Providers

### YFinance (Default)
```python
from portfolio_lib import YFinanceDataService
data_service = YFinanceDataService()
```

### AlphaVantage (Optional)
```python
# pip install portfolio-lib[alphavantage]
from portfolio_lib.services.data.alphavantage import AlphaVantageDataService
data_service = AlphaVantageDataService(api_key="your_key")
```

## Development

```bash
# Install in development mode
cd portfolio_lib
pip install -e .[dev]

# Run tests
pytest

# Format code
black portfolio_lib tests
isort portfolio_lib tests

# Type checking
mypy portfolio_lib
```

## License

MIT License - see LICENSE file for details.
