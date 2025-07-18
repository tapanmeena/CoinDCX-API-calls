# CoinDCX Algorithmic Trading Platform

## Overview

This is a professional algorithmic trading platform built for the CoinDCX exchange. It provides a comprehensive REST API, real-time market data processing, strategy management, risk controls, and automated trading capabilities.

## Features

### 🚀 Core Features
- **REST API**: Full-featured FastAPI-based REST API
- **Real-time Market Data**: Live price feeds and market analysis
- **Strategy Management**: Multiple built-in trading strategies
- **Order Management**: Advanced order handling and execution
- **Risk Management**: Comprehensive risk controls and limits
- **Portfolio Tracking**: Real-time portfolio monitoring
- **Telegram Notifications**: Instant trade and alert notifications
- **Analytics Dashboard**: Performance metrics and reporting

### 📊 Trading Strategies
- **Momentum Strategy**: Trades on price breakouts and trends
- **Mean Reversion Strategy**: Trades on price reversals
- **Custom Strategy Support**: Easy to add new strategies

### 🛡️ Risk Management
- Stop loss and take profit controls
- Daily loss limits
- Maximum drawdown protection
- Position sizing rules
- Real-time risk monitoring

### 📱 Notifications
- Telegram integration for instant alerts
- Trade execution notifications
- Strategy status updates
- Risk alerts and warnings
- Daily performance summaries

## Quick Start

### Prerequisites
- Python 3.8+
- CoinDCX API credentials
- Optional: Telegram bot token for notifications

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd CoinDCX-API-calls
pip install -r requirements.txt
```

2. **Environment Configuration**
Create a `.env` file in the project root:
```env
# CoinDCX API Credentials
COINDCX_API_KEY=your_api_key_here
COINDCX_SECRET_KEY=your_secret_key_here

# Telegram Notifications (Optional)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Configuration
DEFAULT_TRADE_AMOUNT=1000.0
MAX_POSITION_SIZE=10000.0
STOP_LOSS_PERCENT=3.0
TAKE_PROFIT_PERCENT=2.0
DAILY_LOSS_LIMIT=5000.0

# Application Settings
HOST=0.0.0.0
PORT=8000
DEBUG=false
SECRET_KEY=your-secret-key-here
```

3. **Run the Application**
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Market Data
- `GET /api/v1/market/ticker/{symbol}` - Get ticker data
- `GET /api/v1/market/candles/{symbol}` - Get candlestick data
- `GET /api/v1/market/summary` - Get market summary
- `GET /api/v1/market/gainers` - Get top gainers
- `GET /api/v1/market/losers` - Get top losers

### Orders
- `POST /api/v1/orders/create` - Create new order
- `DELETE /api/v1/orders/{order_id}/cancel` - Cancel order
- `GET /api/v1/orders/history` - Get trade history
- `GET /api/v1/orders/active` - Get active orders

### Strategies
- `POST /api/v1/strategies/create` - Create new strategy
- `GET /api/v1/strategies/` - List all strategies
- `POST /api/v1/strategies/{name}/start` - Start strategy
- `POST /api/v1/strategies/{name}/stop` - Stop strategy
- `GET /api/v1/strategies/{name}/performance` - Get performance

### Portfolio
- `GET /api/v1/portfolio/balance` - Get portfolio balance
- `GET /api/v1/portfolio/holdings` - Get current holdings
- `GET /api/v1/portfolio/performance` - Get performance metrics

### Analytics
- `GET /api/v1/analytics/pnl` - Get P&L summary
- `GET /api/v1/analytics/risk-metrics` - Get risk metrics
- `GET /api/v1/analytics/performance` - Get performance analytics

## Usage Examples

### Creating a Momentum Strategy
```python
import requests

strategy_data = {
    "name": "BTC Momentum",
    "strategy_type": "momentum",
    "symbols": ["BTCINR", "ETHINR"],
    "parameters": {
        "momentum_threshold": 3.0,
        "stop_loss_percent": 2.0,
        "take_profit_percent": 1.5,
        "lookback_minutes": 5
    },
    "risk_settings": {
        "max_position_value": 10000,
        "daily_loss_limit": 5000,
        "max_trades_per_day": 10
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/strategies/create",
    json=strategy_data
)
```

### Manual Order Placement
```python
order_data = {
    "symbol": "BTCINR",
    "side": "buy",
    "order_type": "limit_order",
    "quantity": 0.001,
    "price": 3500000
}

response = requests.post(
    "http://localhost:8000/api/v1/orders/create",
    json=order_data
)
```

### Getting Market Data
```python
# Get current ticker
response = requests.get("http://localhost:8000/api/v1/market/ticker/BTCINR")

# Get market summary
response = requests.get("http://localhost:8000/api/v1/market/summary")

# Get top gainers
response = requests.get("http://localhost:8000/api/v1/market/gainers")
```
