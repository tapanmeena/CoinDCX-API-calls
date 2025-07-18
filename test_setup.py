#!/usr/bin/env python3
"""
Quick test script to validate the CoinDCX trading platform setup
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """Test if all modules can be imported"""
    try:
        # Test core imports
        from app.core.config import get_settings
        from app.models.schemas import OrderRequest, StrategyRequest
        from app.services.coindcx_client import CoinDCXClient
        
        print("✅ Core modules imported successfully")
        
        # Test settings
        settings = get_settings()
        print(f"✅ Settings loaded (HOST: {settings.HOST}, PORT: {settings.PORT})")
        
        # Test API client (without credentials)
        client = CoinDCXClient("test", "test")
        print("✅ CoinDCX client can be instantiated")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_database():
    """Test database connectivity"""
    try:
        from app.core.database import Base, engine
        print("✅ Database modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

async def test_api_endpoints():
    """Test if API endpoints can be loaded"""
    try:
        from app.api.v1.router import router
        from app.main import app
        print("✅ API endpoints loaded successfully")
        return True
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def check_environment():
    """Check environment setup"""
    env_file = Path('.env')
    if env_file.exists():
        print("✅ .env file exists")
        return True
    else:
        print("❌ .env file not found. Please copy .env.example to .env")
        return False

def check_requirements():
    """Check if requirements are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pydantic
        import requests
        print("✅ Core dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

async def main():
    """Main test function"""
    print("🧪 Testing CoinDCX Algorithmic Trading Platform Setup\n")
    
    tests = [
        ("Environment file", check_environment),
        ("Requirements", check_requirements),
        ("Core imports", test_imports),
        ("Database", test_database),
        ("API endpoints", test_api_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
        
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The platform is ready to use.")
        print("To start the application, run: python run.py")
        print("API documentation: http://localhost:8000/docs")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        if not check_environment():
            print("💡 Quick fix: cp .env.example .env")
        if not check_requirements():
            print("💡 Quick fix: pip install -r requirements.txt")

if __name__ == "__main__":
    asyncio.run(main())
