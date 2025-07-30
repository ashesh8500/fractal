#!/usr/bin/env python3
"""
Integration test script to verify backend-frontend communication.
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend_server'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'portfolio_lib'))

async def test_backend_endpoints():
    """Test all backend endpoints to ensure they work before frontend testing."""
    
    try:
        import httpx
        
        base_url = "http://localhost:8000/api/v1"
        
        async with httpx.AsyncClient() as client:
            print("🔍 Testing backend endpoints...")
            
            # Test health endpoint
            print("\n1. Testing health endpoint...")
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            # Test create portfolio
            print("\n2. Testing create portfolio...")
            portfolio_data = {
                "name": "Test Portfolio",
                "holdings": {
                    "AAPL": 10.0,
                    "MSFT": 5.0,
                    "GOOGL": 3.0
                }
            }
            response = await client.post(f"{base_url}/portfolios", json=portfolio_data)
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                portfolio = response.json()
                print(f"   Created portfolio: {portfolio['name']}")
                print(f"   Total value: ${portfolio['total_value']:.2f}")
            else:
                print(f"   Error: {response.text}")
            
            # Test list portfolios
            print("\n3. Testing list portfolios...")
            response = await client.get(f"{base_url}/portfolios")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                portfolios = response.json()
                print(f"   Found {len(portfolios)} portfolios")
                for p in portfolios:
                    print(f"   - {p['name']}: ${p['total_value']:.2f}")
            
            # Test get specific portfolio
            print("\n4. Testing get specific portfolio...")
            response = await client.get(f"{base_url}/portfolios/Test Portfolio")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                portfolio = response.json()
                print(f"   Portfolio: {portfolio['name']}")
                print(f"   Holdings: {len(portfolio['holdings'])} positions")
            
            # Test market data
            print("\n5. Testing market data...")
            response = await client.get(f"{base_url}/market-data?symbols=AAPL,MSFT")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Market data: {data}")
            
            print("\n✅ All backend tests completed!")
            return True
            
    except ImportError:
        print("❌ httpx not installed. Install with: pip install httpx")
        return False
    except Exception as e:
        print(f"❌ Backend test failed: {e}")
        return False

def start_backend_server():
    """Start the backend server for testing."""
    import subprocess
    import time
    
    print("🚀 Starting backend server...")
    
    # Start the server in the background
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join([
        os.path.join(os.getcwd(), 'portfolio_lib'),
        env.get('PYTHONPATH', '')
    ])
    
    process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "backend_server.app.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ], cwd=os.getcwd(), env=env)
    
    # Give it time to start
    time.sleep(3)
    
    return process

async def main():
    """Main test function."""
    print("🧪 Integration Test: Backend-Frontend Communication")
    print("=" * 50)
    
    # Start backend server
    server_process = None
    try:
        server_process = start_backend_server()
        
        # Test backend endpoints
        success = await test_backend_endpoints()
        
        if success:
            print("\n🎉 Backend is ready for frontend testing!")
            print("\nNext steps:")
            print("1. Keep this backend server running")
            print("2. In another terminal, run: cargo run")
            print("3. Test the frontend-backend communication")
            print("\nPress Ctrl+C to stop the backend server...")
            
            # Keep server running
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping backend server...")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    finally:
        if server_process:
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    asyncio.run(main())
