#!/usr/bin/env python3
"""
CoinDCX Algorithmic Trading Platform
Startup script for the application
"""

import asyncio
import logging
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app, get_settings
import uvicorn

def main():
    """Main entry point for the application"""
    settings = get_settings()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting CoinDCX Algorithmic Trading Platform")
    
    # Check if API keys are configured
    if not settings.COINDCX_API_KEY or not settings.COINDCX_SECRET_KEY:
        logger.warning("CoinDCX API credentials not configured. Some features may not work.")
    
    # Start the application
    try:
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info" if not settings.DEBUG else "debug"
        )
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
