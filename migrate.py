#!/usr/bin/env python3
"""
Migration script to move from old structure to new structure
This script helps migrate existing configuration and sets up the new application
"""

import os
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_old_files():
    """Migrate old files to backup directory"""
    old_files = [
        'api.py', 'CryptoOrderer.py', 'GenericCoinTicker.py', 
        'MarginOrderer.py', 'neverUse.py', 'PlaceOrder.py',
        'PnLStrategy.py', 'Strategy1.py', 'TelegramApi.py', 'ticker.py'
    ]
    
    # Create backup directory
    backup_dir = Path('legacy_files')
    backup_dir.mkdir(exist_ok=True)
    
    for file_name in old_files:
        file_path = Path(file_name)
        if file_path.exists():
            backup_path = backup_dir / file_name
            shutil.move(str(file_path), str(backup_path))
            logger.info(f"Moved {file_name} to {backup_path}")

def setup_environment():
    """Setup environment file if it doesn't exist"""
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(str(env_example), str(env_file))
        logger.info("Created .env file from .env.example")
        logger.warning("Please edit .env file with your actual API credentials")
    elif env_file.exists():
        logger.info(".env file already exists")
    else:
        logger.error("No .env.example file found")

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import pydantic
        logger.info("Core dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Please run: pip install -r requirements.txt")
        return False

def main():
    """Main migration function"""
    logger.info("Starting migration to new CoinDCX Algo Trading Platform")
    
    # Migrate old files
    migrate_old_files()
    
    # Setup environment
    setup_environment()
    
    # Check dependencies
    if check_dependencies():
        logger.info("Migration completed successfully!")
        logger.info("To start the application, run: python run.py")
        logger.info("API documentation will be available at: http://localhost:8000/docs")
    else:
        logger.error("Migration completed with errors. Please install dependencies first.")

if __name__ == "__main__":
    main()
