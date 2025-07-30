#!/usr/bin/env python3
"""
Test script to verify Phase 1 core functionality.
"""

def test_basic_functionality():
    """Test basic portfolio functionality."""
    try:
        # Test imports
        from portfolio_lib.models.portfolio import Portfolio
        from portfolio_lib.services.data.yfinance import YFinanceDataService
        from portfolio_lib.models.market_data import RiskMetrics, PerformanceMetrics
        
        print('✅ All imports successful')
        
        # Test creating a mock portfolio (without real data)
        class MockDataService:
            def fetch_current_prices(self, symbols):
                return {symbol: 100.0 for symbol in symbols}
            def fetch_price_history(self, symbols, start_date, end_date):
                return {}
            def get_data_source_name(self):
                return 'mock'
            def is_market_open(self):
                return True
        
        mock_service = MockDataService()
        portfolio = Portfolio(
            name='Test Portfolio',
            holdings={'AAPL': 100, 'GOOGL': 50},
            data_service=mock_service
        )
        
        print(f'✅ Portfolio created: {portfolio.name}')
        print(f'✅ Total value: ${portfolio.total_value:,.2f}')
        print(f'✅ Current weights: {portfolio.current_weights}')
        
        # Test portfolio operations
        portfolio.add_holding('MSFT', 75)
        print(f'✅ Added holding: {portfolio.symbols}')
        
        portfolio.remove_holding('GOOGL')
        print(f'✅ Removed holding: {portfolio.symbols}')
        
        # Test serialization
        portfolio_dict = portfolio.to_dict()
        print(f'✅ Serialization works: {list(portfolio_dict.keys())}')
        
        print('\n🎉 Phase 1 core functionality working!')
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_basic_functionality()
    exit(0 if success else 1)
