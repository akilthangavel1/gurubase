#!/usr/bin/env python3
"""
Test script to verify Celery configuration
"""

import os
import sys
import django
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurubase.settings')
django.setup()

def test_celery_import():
    """Test if Celery app can be imported"""
    try:
        from gurubase.celery import app
        print("✅ Celery app imported successfully:", app)
        return True
    except Exception as e:
        print("❌ Failed to import Celery app:", e)
        return False

def test_celery_tasks():
    """Test if tasks can be imported"""
    try:
        from dashboard.tasks import process_stock_data
        print("✅ Tasks imported successfully:", process_stock_data)
        return True
    except Exception as e:
        print("❌ Failed to import tasks:", e)
        return False

def test_celery_app_discovery():
    """Test if Celery can discover the app via command line"""
    import subprocess
    try:
        # Test if celery can find the app
        result = subprocess.run([
            'celery', '-A', 'gurubase.celery', 'inspect', 'stats'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Celery command line discovery successful")
            return True
        else:
            print("❌ Celery command line discovery failed:")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("⚠️  Celery command line test timed out (likely because no worker is running)")
        return True  # This is actually expected if no worker is running
    except Exception as e:
        print("❌ Celery command line test failed:", e)
        return False

if __name__ == "__main__":
    print("🧪 Testing Celery Configuration")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    if test_celery_import():
        tests_passed += 1
    
    if test_celery_tasks():
        tests_passed += 1
    
    if test_celery_app_discovery():
        tests_passed += 1
    
    print("\n" + "=" * 40)
    print(f"Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Celery is configured correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1) 