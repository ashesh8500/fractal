#!/usr/bin/env python3
"""
Integration test script to verify backend server functionality.

This script:
- Boots the FastAPI backend with uvicorn
- Waits for readiness
- Exercises core endpoints:
  - /health
  - POST /portfolios
  - GET /portfolios
  - GET /portfolios/{name}
  - GET /market-data
  - GET /market-data/history
- Provides clear logging and exit codes for CI

Usage:
  python test_integration.py                 # Start server, run tests, then keep server alive until Ctrl+C
  python test_integration.py --one-shot      # Start server, run tests, then shut it down and exit with code
  python test_integration.py --base-url http://localhost:8001/api/v1  # Use external running server (no spawn)
"""

import asyncio
import sys
import os
import json
import time
import signal
import subprocess
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, UTC as DATETIME_UTC

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"


def ensure_dependency(pkg: str, import_name: Optional[str] = None) -> bool:
    try:
        __import__(import_name or pkg)
        return True
    except ImportError:
        print(f"❌ Required dependency '{pkg}' is not installed.")
        print(f"   Install with: pip install {pkg}")
        return False


async def wait_for_ready(base_url: str, timeout: float = 20.0, interval: float = 0.5) -> bool:
    import httpx
    start = time.time()
    while time.time() - start < timeout:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/health")
                if resp.status_code == 200:
                    return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    return False


async def test_backend_endpoints(base_url: str) -> bool:
    """Test all backend endpoints to ensure they work before frontend testing."""
    import httpx

    ok = True
    print("🔍 Testing backend endpoints...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Health
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            ok = ok and (response.status_code == 200)
        except Exception as e:
            print(f"   ❌ Health request failed: {e}")
            return False

        # 2. Create portfolio
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
            try:
                portfolio = response.json()
                print(f"   Created portfolio: {portfolio.get('name')}")
                total_value = portfolio.get('total_value', 0.0) or 0.0
                print(f"   Total value: ${float(total_value):.2f}")
            except Exception:
                print(f"   Response: {response.text}")
        else:
            print(f"   Error: {response.text}")
            ok = False

        # 3. List portfolios
        print("\n3. Testing list portfolios...")
        response = await client.get(f"{base_url}/portfolios")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                portfolios = response.json()
                print(f"   Found {len(portfolios)} portfolios")
                for p in portfolios:
                    tv = p.get('total_value', 0.0) or 0.0
                    print(f"   - {p.get('name')}: ${float(tv):.2f}")
            except Exception:
                print(f"   Response parsing failed: {response.text}")
                ok = False
        else:
            print(f"   Error: {response.text}")
            ok = False

        # 4. Get specific portfolio
        print("\n4. Testing get specific portfolio...")
        response = await client.get(f"{base_url}/portfolios/Test Portfolio")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                portfolio = response.json()
                holdings = portfolio.get('holdings', {})
                print(f"   Portfolio: {portfolio.get('name')}")
                print(f"   Holdings: {len(holdings)} positions")
            except Exception:
                print(f"   Response parsing failed: {response.text}")
                ok = False
        else:
            print(f"   Error: {response.text}")
            ok = False

        # 5. Market data (current prices)
        print("\n5. Testing market data (current prices)...")
        response = await client.get(f"{base_url}/market-data?symbols=AAPL,MSFT")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   Market data: {json.dumps(data)[:300]}...")
            except Exception:
                print(f"   Response parsing failed: {response.text}")
                ok = False
        else:
            print(f"   Error: {response.text}")
            ok = False

        # 6. Market data history (hardened endpoint)
        print("\n6. Testing market data history...")
        # Choose a tight date range to minimize data size and rate limits
        end_dt = datetime.now(DATETIME_UTC).date()
        start_dt = end_dt - timedelta(days=10)
        params = {
            "symbols": "AAPL,MSFT",
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
        }
        response = await client.get(f"{base_url}/market-data/history", params=params)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                # Validate shape: dict of symbol -> list
                if not isinstance(data, dict):
                    print("   ❌ Invalid response shape, expected dict")
                    ok = False
                else:
                    for sym in ["AAPL", "MSFT"]:
                        series = data.get(sym, [])
                        print(f"   {sym}: {len(series)} points")
                        # If empty, still acceptable due to provider limitations; ensure list type
                        if not isinstance(series, list):
                            print(f"   ❌ {sym} series is not a list")
                            ok = False
            except Exception:
                print(f"   Response parsing failed: {response.text}")
                ok = False
        else:
            print(f"   Error: {response.text}")
            ok = False

    if ok:
        print("\n✅ All backend tests completed successfully!")
    else:
        print("\n❌ Some backend tests failed.")
    return ok


def start_backend_server() -> Optional[subprocess.Popen]:
    """Start the backend server for testing."""
    print("🚀 Starting backend server...")

    env = os.environ.copy()
    # Ensure portfolio_lib is importable by backend_server
    project_root = os.getcwd()
    lib_path = os.path.join(project_root, 'portfolio_lib')
    existing = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = os.pathsep.join([lib_path, existing]) if existing else lib_path

    # Start the server in the background
    try:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn",
                "backend_server.app.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000",
            ],
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        print("❌ uvicorn not found. Install with: pip install uvicorn[standard]")
        return None
    except Exception as e:
        print(f"❌ Failed to start backend server: {e}")
        return None

    return process


async def run_with_spawn(one_shot: bool, base_url: str) -> int:
    """Spawn the server, wait for readiness, run tests, and optionally keep alive."""
    process = start_backend_server()
    if process is None:
        return 1

    try:
        ready = await wait_for_ready(base_url)
        if not ready:
            print("❌ Server did not become ready in time.")
            try:
                if process.stderr:
                    err = process.stderr.read().decode(errors="ignore")
                    if err:
                        print("---- Server stderr ----")
                        print(err)
                        print("-----------------------")
            except Exception:
                pass
            return 1

        success = await test_backend_endpoints(base_url)
        if one_shot:
            # Stop after tests
            return 0 if success else 2

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
            return 0 if success else 2
    finally:
        # Terminate server
        try:
            process.terminate()
            try:
                process.wait(timeout=10)
            except Exception:
                process.kill()
        except Exception:
            pass


async def run_against_existing(base_url: str) -> int:
    """Run tests against an already running backend (no spawn)."""
    ready = await wait_for_ready(base_url, timeout=5.0)
    if not ready:
        print(f"❌ Backend at {base_url} is not responding to /health")
        return 1
    success = await test_backend_endpoints(base_url)
    return 0 if success else 2


def parse_args(argv: list) -> Tuple[bool, str, bool]:
    """Parse CLI args. Returns (one_shot, base_url, use_existing)."""
    one_shot = False
    base_url = DEFAULT_BASE_URL
    use_existing = False

    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif a == "--one-shot":
            one_shot = True
        elif a == "--base-url":
            if i + 1 >= len(argv):
                print("Missing value for --base-url")
                sys.exit(1)
            base_url = argv[i + 1].rstrip("/")
            i += 1
            use_existing = True
        elif a == "--use-existing":
            use_existing = True
        i += 1

    return one_shot, base_url, use_existing


async def main():
    """Main test function."""
    # Check dependencies early
    deps_ok = True
    deps_ok &= ensure_dependency("httpx")
    deps_ok &= ensure_dependency("uvicorn")
    if not deps_ok:
        sys.exit(1)

    print("🧪 Integration Test: Backend Server")
    print("=" * 50)

    one_shot, base_url, use_existing = parse_args(sys.argv[1:])

    if use_existing:
        exit_code = await run_against_existing(base_url)
    else:
        exit_code = await run_with_spawn(one_shot, base_url)

    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        sys.exit(130)
