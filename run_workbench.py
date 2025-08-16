#!/usr/bin/env python3
"""
Quick runner for the Strategy Workbench.

Usage:
    python run_workbench.py

Or with streamlit directly:
    streamlit run portfolio_lib/portfolio_lib/ui/strategy_workbench.py
"""

import subprocess
import sys
import os

def main():
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Path to the workbench module
    workbench_path = "portfolio_lib/portfolio_lib/ui/strategy_workbench.py"
    
    if not os.path.exists(workbench_path):
        print(f"Error: Could not find {workbench_path}")
        sys.exit(1)
    
    print("🚀 Starting Strategy Workbench...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🎯 Module path: {workbench_path}")
    print("\n" + "="*50)
    print("🔧 Configuration Tips:")
    print("1. Set Provider to 'OpenAI-compatible'")
    print("2. Set API Base to 'http://127.0.0.1:1234/v1'")
    print("3. Set Model to 'qwen/qwen3-coder-30b'")
    print("4. Configure symbols (default: AAPL,MSFT,NVDA,AMZN,GOOGL,QQQ)")
    print("5. Use 'Discuss' mode for exploration, 'Implement' mode to save")
    print("="*50 + "\n")
    
    try:
        # Run streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", workbench_path,
            "--server.port", "8501",
            "--server.address", "localhost"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Strategy Workbench stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
