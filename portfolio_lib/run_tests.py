#!/usr/bin/env python3
"""
Test runner script for portfolio_lib.

This script runs all tests in the correct order and provides
a comprehensive validation of the Phase 1 implementation.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Running: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
        else:
            print(f"❌ FAILED: {description}")
            if result.stderr:
                print("STDERR:")
                print(result.stderr)
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ ERROR running {description}: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 PORTFOLIO_LIB COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Change to portfolio_lib directory
    os.chdir(Path(__file__).parent)
    
    tests = [
        ("python -m pytest tests/ -v", "Unit Tests (pytest)"),
        ("python test_dependency_injection.py", "Dependency Injection Test"),
        ("python test_complete_implementation.py", "Complete Implementation Test"),
    ]
    
    results = []
    
    for cmd, description in tests:
        success = run_command(cmd, description)
        results.append((description, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {description}")
        if not success:
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ Phase 1 implementation is fully working")
        print("🚀 Ready for Phase 2: Backend Server")
        return 0
    else:
        print(f"\n❌ SOME TESTS FAILED")
        print("🔧 Please check the errors above and fix issues")
        return 1

if __name__ == "__main__":
    sys.exit(main())
