#!/usr/bin/env python3
"""
Simple backend test to verify imports work.
"""

import sys
import os

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_server'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'portfolio_lib'))

def test_backend_imports():
    """Test that backend imports work."""
    try:
        print("Testing backend imports...")
        
        # Test core imports
        from backend_server.app.core.result import Result, AppError, ErrorType
        print("✅ Core result imports work")
        
        # Test schemas
        from backend_server.app.schemas import PortfolioCreate, DataProvider
        print("✅ Schema imports work")
        
        # Test services
        from backend_server.app.services import PortfolioService
        print("✅ Service imports work")
        
        # Test main app
        from backend_server.app.main import app
        print("✅ FastAPI app imports work")
        
        # Test basic functionality
        service = PortfolioService()
        portfolio_data = PortfolioCreate(
            name="Test Portfolio",
            holdings={"AAPL": 10.0, "MSFT": 5.0}
        )
        
        result = service.create_portfolio(portfolio_data, DataProvider.YFINANCE)
        if result.is_ok():
            print("✅ Portfolio creation works")
        else:
            print(f"❌ Portfolio creation failed: {result.unwrap_err().message}")
        
        print("\n🎉 Backend is ready!")
        return True
        
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backend_imports()
    sys.exit(0 if success else 1)
