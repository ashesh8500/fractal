#!/usr/bin/env python3
"""
Quick test to verify the backend server setup.
"""

import sys
import os
import asyncio

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../portfolio_lib'))

async def test_imports():
    """Test that all imports work correctly."""
    try:
        # Test core imports
        from backend_server.app.core.result import Result, AppError, ErrorType
        print("✅ Core result monad imported successfully")
        
        # Test schemas
        from backend_server.app.schemas import PortfolioCreate, StrategyExecuteRequest
        print("✅ Pydantic schemas imported successfully")
        
        # Test services
        from backend_server.app.services import portfolio_service
        print("✅ Portfolio service imported successfully")
        
        # Test routes
        from backend_server.app.routes import api_router
        print("✅ API routes imported successfully")
        
        # Test main app
        from backend_server.app.main import app
        print("✅ FastAPI app imported successfully")
        
        # Test Result monad functionality
        success_result = Result.ok("test_value")
        error_result = Result.err(AppError(ErrorType.VALIDATION_ERROR, "test error"))
        
        assert success_result.is_ok()
        assert error_result.is_err()
        assert success_result.unwrap() == "test_value"
        
        # Test functional chaining
        result = (
            Result.ok(5)
            .map(lambda x: x * 2)
            .map(lambda x: x + 1)
        )
        assert result.unwrap() == 11
        print("✅ Result monad functionality working correctly")
        
        # Test schema validation
        portfolio_data = PortfolioCreate(
            name="Test Portfolio",
            holdings={"AAPL": 10, "MSFT": 5}
        )
        assert portfolio_data.name == "Test Portfolio"
        print("✅ Pydantic validation working correctly")
        
        print("\n🎉 All backend server components working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_imports())
    sys.exit(0 if success else 1)
