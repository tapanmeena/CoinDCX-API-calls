# Advanced Algorithmic Trading Platform - User Guide

## 🚀 Overview

This platform transforms basic CoinDCX trading scripts into a professional algorithmic trading system with advanced strategies and comprehensive backtesting capabilities.

## 🏗️ Architecture

### Core Components
- **FastAPI Backend**: RESTful API with real-time market data
- **Advanced Strategies**: 5 sophisticated trading algorithms
- **Backtesting Engine**: Historical data analysis and strategy validation
- **Parameter Optimization**: Automated strategy tuning
- **Strategy Comparison**: Multi-strategy performance analysis

### Available Trading Strategies

#### 1. RSI Strategy (`rsi`)
- **Purpose**: Momentum-based trading using Relative Strength Index
- **Signals**: Buy when oversold, sell when overbought
- **Parameters**:
  - `rsi_period`: Calculation period (default: 14)
  - `rsi_overbought`: Overbought threshold (default: 70)
  - `rsi_oversold`: Oversold threshold (default: 30)

#### 2. Bollinger Bands Strategy (`bollinger_bands`)
- **Purpose**: Mean reversion trading using statistical bands
- **Signals**: Buy at lower band, sell at upper band
- **Parameters**:
  - `bb_period`: Moving average period (default: 20)
  - `bb_std_dev`: Standard deviation multiplier (default: 2.0)

#### 3. MACD Strategy (`macd`)
- **Purpose**: Trend-following using Moving Average Convergence Divergence
- **Signals**: Buy/sell on MACD line crossovers
- **Parameters**:
  - `fast_period`: Fast EMA period (default: 12)
  - `slow_period`: Slow EMA period (default: 26)
  - `signal_period`: Signal line EMA period (default: 9)

#### 4. Volume Breakout Strategy (`volume_breakout`)
- **Purpose**: Momentum trading based on volume spikes
- **Signals**: Trade on high-volume price breakouts
- **Parameters**:
  - `volume_threshold`: Volume spike multiplier (default: 2.0)
  - `price_breakout_percent`: Price breakout threshold (default: 2.0)

#### 5. Grid Trading Strategy (`grid_trading`)
- **Purpose**: Range-bound trading with automated grid levels
- **Signals**: Buy low, sell high within price grid
- **Parameters**:
  - `grid_levels`: Number of grid levels (default: 10)
  - `grid_spacing_percent`: Spacing between levels (default: 2.0)

## 🛠️ Setup and Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Server
```bash
python -m app.main
```

### 3. Access the Platform
- **API Documentation**: http://localhost:8000/docs
- **Market Data**: http://localhost:8000/api/v1/market/symbols
- **Strategy Management**: http://localhost:8000/api/v1/strategies

## 📊 Using the Backtesting System

### Running a Simple Backtest

```python
import requests
from datetime import datetime, timedelta

# Define backtest parameters
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

backtest_request = {
    "strategy_name": "rsi",
    "symbols": ["BTCINR"],
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "interval": "1h",
    "initial_capital": 100000.0,
    "strategy_parameters": {
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    }
}

# Run backtest
response = requests.post(
    "http://localhost:8000/api/v1/backtesting/run-backtest",
    json=backtest_request
)

result = response.json()
print(f"Total Return: {result['data']['backtest_results'][0]['total_return_percent']:.2f}%")
```

### Comparing Multiple Strategies

```python
comparison_request = {
    "strategy_names": ["rsi", "bollinger_bands", "macd"],
    "symbols": ["BTCINR"],
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "interval": "1h",
    "initial_capital": 100000.0
}

response = requests.post(
    "http://localhost:8000/api/v1/backtesting/compare-strategies",
    json=comparison_request
)

comparison = response.json()
rankings = comparison['data']['comparison_report']['rankings']
print("Best strategies by Sharpe ratio:", rankings['sharpe_ratio'][:3])
```

### Parameter Optimization

```python
optimization_request = {
    "strategy_name": "rsi",
    "symbol": "BTCINR",
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "parameter_ranges": {
        "rsi_period": {
            "type": "range",
            "start": 10,
            "end": 20,
            "step": 2
        },
        "rsi_overbought": {
            "type": "range",
            "start": 65,
            "end": 80,
            "step": 5
        }
    },
    "optimization_metric": "sharpe_ratio"
}

response = requests.post(
    "http://localhost:8000/api/v1/backtesting/optimize-strategy",
    json=optimization_request
)

optimization = response.json()
best_params = optimization['data']['best_parameters']
best_score = optimization['data']['best_score']
print(f"Best parameters: {best_params}")
print(f"Best Sharpe ratio: {best_score:.3f}")
```

## 🔧 Strategy Management

### Creating a Strategy

```python
strategy_request = {
    "strategy_type": "rsi",
    "name": "my_btc_rsi_strategy",
    "symbols": ["BTCINR"],
    "parameters": {
        "rsi_period": 14,
        "rsi_overbought": 75,
        "rsi_oversold": 25
    },
    "risk_settings": {
        "max_position_size": 10000,
        "stop_loss_percent": 5.0
    }
}

response = requests.post(
    "http://localhost:8000/api/v1/strategies/create",
    json=strategy_request
)
```

### Managing Strategies

```python
# List all strategies
strategies = requests.get("http://localhost:8000/api/v1/strategies/list")

# Get specific strategy
strategy = requests.get("http://localhost:8000/api/v1/strategies/my_btc_rsi_strategy")

# Activate strategy
activate = requests.post("http://localhost:8000/api/v1/strategies/my_btc_rsi_strategy/activate")

# Deactivate strategy
deactivate = requests.post("http://localhost:8000/api/v1/strategies/my_btc_rsi_strategy/deactivate")
```

## 📈 Performance Metrics

### Key Metrics Provided

1. **Total Return**: Absolute and percentage returns
2. **Sharpe Ratio**: Risk-adjusted returns
3. **Sortino Ratio**: Downside risk-adjusted returns
4. **Maximum Drawdown**: Largest peak-to-trough decline
5. **Win Rate**: Percentage of profitable trades
6. **Average Trade Return**: Mean return per trade
7. **Profit Factor**: Ratio of gross profit to gross loss

### Understanding Results

```python
# Example backtest result interpretation
result = {
    "total_return_percent": 15.5,  # 15.5% return over period
    "sharpe_ratio": 1.2,           # Good risk-adjusted performance
    "max_drawdown_percent": -8.3,  # Maximum loss was 8.3%
    "win_rate": 65.0,              # 65% of trades were profitable
    "total_trades": 45,            # 45 trades executed
    "annualized_return": 186.0     # Annualized return rate
}
```

## 🎯 Optimization Strategies

### Best Practices

1. **Start Simple**: Begin with default parameters
2. **Use Sufficient Data**: Minimum 30 days for meaningful results
3. **Avoid Overfitting**: Don't optimize on too small datasets
4. **Cross-Validate**: Test optimized parameters on different periods
5. **Consider Transaction Costs**: Include realistic trading fees

### Parameter Optimization Tips

```python
# Good parameter ranges for RSI
rsi_optimization = {
    "rsi_period": {"type": "range", "start": 10, "end": 20, "step": 2},
    "rsi_overbought": {"type": "range", "start": 65, "end": 80, "step": 5},
    "rsi_oversold": {"type": "range", "start": 20, "end": 35, "step": 5}
}

# Good parameter ranges for Bollinger Bands
bb_optimization = {
    "bb_period": {"type": "range", "start": 15, "end": 25, "step": 5},
    "bb_std_dev": {"type": "choices", "values": [1.5, 2.0, 2.5]}
}
```

## 🚦 Risk Management

### Built-in Risk Controls

1. **Position Sizing**: Maximum position size limits
2. **Stop Loss**: Automatic loss cut-offs
3. **Drawdown Limits**: Maximum allowable drawdown
4. **Exposure Limits**: Total market exposure controls

### Setting Risk Parameters

```python
risk_settings = {
    "max_position_size": 10000,      # Maximum position in INR
    "stop_loss_percent": 5.0,        # 5% stop loss
    "take_profit_percent": 15.0,     # 15% take profit
    "max_daily_trades": 10,          # Max trades per day
    "max_drawdown_percent": 15.0     # Max 15% drawdown
}
```

## 🔄 Live Trading Integration

### Preparation Steps

1. **Backtest Thoroughly**: Validate strategy performance
2. **Optimize Parameters**: Find best parameter combinations
3. **Paper Trade**: Test with virtual money first
4. **Start Small**: Begin with minimal capital
5. **Monitor Closely**: Watch initial live performance

### Activation Process

```python
# 1. Create and validate strategy
strategy = create_strategy(strategy_config)

# 2. Run comprehensive backtests
backtest_results = run_backtest(strategy, historical_data)

# 3. Optimize parameters
optimized_params = optimize_strategy(strategy, parameter_ranges)

# 4. Update strategy with optimized parameters
update_strategy(strategy_name, optimized_params)

# 5. Activate for live trading
activate_strategy(strategy_name)
```

## 📚 API Reference

### Strategy Endpoints
- `GET /api/v1/strategies/types` - Available strategy types
- `POST /api/v1/strategies/create` - Create new strategy
- `GET /api/v1/strategies/list` - List all strategies
- `GET /api/v1/strategies/{name}` - Get strategy details
- `PUT /api/v1/strategies/{name}` - Update strategy
- `DELETE /api/v1/strategies/{name}` - Delete strategy
- `POST /api/v1/strategies/{name}/activate` - Activate strategy
- `POST /api/v1/strategies/{name}/deactivate` - Deactivate strategy

### Backtesting Endpoints
- `POST /api/v1/backtesting/run-backtest` - Run single backtest
- `POST /api/v1/backtesting/compare-strategies` - Compare strategies
- `POST /api/v1/backtesting/optimize-strategy` - Optimize parameters
- `GET /api/v1/backtesting/available-strategies` - Get available strategies
- `GET /api/v1/backtesting/suggested-parameters/{strategy}` - Get parameter suggestions

### Market Data Endpoints
- `GET /api/v1/market/symbols` - Available trading pairs
- `GET /api/v1/market/ticker/{symbol}` - Real-time ticker data
- `GET /api/v1/market/depth/{symbol}` - Order book depth
- `GET /api/v1/market/trades/{symbol}` - Recent trades

## 🐛 Troubleshooting

### Common Issues

1. **Server Not Starting**
   - Check Python dependencies: `pip install -r requirements.txt`
   - Verify port 8000 is available
   - Check server logs for errors

2. **Backtest Failures**
   - Ensure valid date ranges (past dates only)
   - Check symbol names match CoinDCX format
   - Verify sufficient historical data available

3. **Strategy Creation Errors**
   - Validate parameter ranges and types
   - Check symbol format (e.g., "BTCINR", not "BTC/INR")
   - Ensure strategy name is unique

4. **Market Data Issues**
   - Check internet connection
   - Verify CoinDCX API access
   - Wait for market data service initialization

### Getting Help

- Check API documentation: http://localhost:8000/docs
- Review server logs for detailed error messages
- Run the demo script: `python examples/advanced_trading_demo.py`
- Verify market data is updating: http://localhost:8000/api/v1/market/symbols

## 🎯 Next Steps

1. **Explore the Demo**: Run `python examples/advanced_trading_demo.py`
2. **Create Custom Strategies**: Modify existing strategies or create new ones
3. **Optimize Performance**: Use parameter optimization to improve results
4. **Integrate with Trading**: Connect to live trading when ready
5. **Monitor and Adjust**: Continuously monitor and refine strategies

## 📞 Support

For technical support or questions:
- Review the interactive API docs at http://localhost:8000/docs
- Check the example scripts in the `examples/` directory
- Examine the strategy implementations in `app/strategies/`

---

**Happy Trading! 🚀**
