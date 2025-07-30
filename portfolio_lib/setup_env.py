#!/usr/bin/env python3
"""
Environment setup script for portfolio_lib.

This script helps set up the development environment and
checks that all dependencies are properly installed.
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create a sample .env file if it doesn't exist."""
    env_file = Path(".env")
    
    if not env_file.exists():
        print("📝 Creating sample .env file...")
        
        env_content = """# Portfolio Library Configuration
# Copy this file and update with your actual API keys

# Data Provider Settings
PORTFOLIO_LIB_DEFAULT_DATA_PROVIDER=yfinance
PORTFOLIO_LIB_LOG_LEVEL=INFO

# AlphaVantage API Key (optional)
# Get your free API key from: https://www.alphavantage.co/support/#api-key
# PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY=your_api_key_here

# Example usage:
# PORTFOLIO_LIB_ALPHAVANTAGE_API_KEY=ABC123XYZ
"""
        
        with open(env_file, "w") as f:
            f.write(env_content)
        
        print(f"✅ Created {env_file}")
        print("📋 Please edit .env file and add your API keys if needed")
    else:
        print(f"✅ .env file already exists: {env_file}")

def check_imports():
    """Check that all required imports work."""
    print("\n🔍 Checking imports...")
    
    try:
        import pandas as pd
        print("✅ pandas imported successfully")
        
        import numpy as np
        print("✅ numpy imported successfully")
        
        import yfinance as yf
        print("✅ yfinance imported successfully")
        
        # Test our library imports
        from portfolio_lib import Portfolio
        print("✅ portfolio_lib.Portfolio imported successfully")
        
        from portfolio_lib.services.data.yfinance import YFinanceDataService
        print("✅ YFinanceDataService imported successfully")
        
        from portfolio_lib.services.strategy.base import StrategyService
        print("✅ StrategyService imported successfully")
        
        from portfolio_lib.services.backtesting.engine import BacktestEngine
        print("✅ BacktestEngine imported successfully")
        
        print("✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Please run: uv sync")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from portfolio_lib.services.data.yfinance import YFinanceDataService
        from portfolio_lib import Portfolio
        
        # Test data service
        data_service = YFinanceDataService()
        print(f"✅ Data service created: {data_service.get_data_source_name()}")
        
        # Test portfolio creation
        portfolio = Portfolio("Test", {"AAPL": 1}, data_service)
        print(f"✅ Portfolio created: {portfolio.name}")
        
        # Test strategy service
        from portfolio_lib.services.strategy.base import StrategyService
        strategy_service = StrategyService(data_service)
        strategies = strategy_service.get_available_strategies()
        print(f"✅ Available strategies: {strategies}")
        
        print("✅ Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 PORTFOLIO_LIB ENVIRONMENT SETUP")
    print("=" * 50)
    
    # Create .env file
    create_env_file()
    
    # Check imports
    if not check_imports():
        print("\n❌ Setup incomplete - import errors")
        return 1
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Setup incomplete - functionality errors")
        return 1
    
    print("\n🎉 ENVIRONMENT SETUP COMPLETE!")
    print("✅ All dependencies installed and working")
    print("✅ Basic functionality verified")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys (optional)")
    print("2. Run tests: python run_tests.py")
    print("3. Or run individual tests:")
    print("   - python test_dependency_injection.py")
    print("   - python test_complete_implementation.py")
    print("   - pytest tests/ -v")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
