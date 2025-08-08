#!/usr/bin/env python3
"""
Development server startup script.
"""

import uvicorn
import sys
import os

# Add project paths
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

# Load environment from .env (repo root or local)
try:
    from dotenv import load_dotenv  # type: ignore
    # Try repo root .env first
    root_env = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(root_env):
        load_dotenv(root_env)
    # Then load local .env if present (doesn't override existing)
    load_dotenv()
except Exception:
    pass

if __name__ == "__main__":
    print("🚀 Starting Portfolio Backend Server...")
    print("📊 Functional programming with Result monads")
    print("🏗️  Clean architecture with dependency injection")
    print("💨 Lean and fast API design")
    print()
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
