from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # Allow extra fields in environment variables
    }
    
    # API Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # CoinDCX API
    COINDCX_API_KEY: str = ""
    COINDCX_SECRET_KEY: str = ""
    COINDCX_BASE_URL: str = "https://api.coindcx.com"
    COINDCX_PUBLIC_URL: str = "https://public.coindcx.com"
    
    # Database
    DATABASE_URL: str = "sqlite:///./trading_bot.db"
    
    # Redis (for caching and real-time data)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    
    # Trading Configuration
    DEFAULT_TRADE_AMOUNT: float = 1000.0  # INR
    MAX_POSITION_SIZE: float = 10000.0    # INR
    STOP_LOSS_PERCENT: float = 3.0        # 3%
    TAKE_PROFIT_PERCENT: float = 2.0      # 2%
    MAX_CONCURRENT_TRADES: int = 5
    
    # Risk Management
    DAILY_LOSS_LIMIT: float = 5000.0      # INR
    MAX_DRAWDOWN_PERCENT: float = 10.0    # 10%
    
    # Market Data
    MARKET_DATA_REFRESH_INTERVAL: int = 5  # seconds
    CANDLE_INTERVALS: List[str] = ["1m", "5m", "15m", "1h", "1d"]
    
    # Strategy Configuration
    STRATEGY_EXECUTION_INTERVAL: int = 10  # seconds

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
