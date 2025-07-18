"""
Advanced Strategy Management and Backtesting Examples
===================================================

This script demonstrates how to use the new strategy management and backtesting APIs
for algorithmic trading with the CoinDCX platform.

Run the FastAPI server first: python -m app.main
Then run this script to see examples of:
1. Creating and managing trading strategies
2. Running backtests
3. Comparing strategies
4. Optimizing parameters
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

class StrategyAPIClient:
    """Client for interacting with strategy and backtesting APIs"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_strategy_types(self) -> Dict:
        """Get available strategy types"""
        async with self.session.get(f"{self.base_url}/api/v1/strategies/types") as resp:
            return await resp.json()
    
    async def create_strategy(self, strategy_data: Dict) -> Dict:
        """Create a new strategy"""
        async with self.session.post(
            f"{self.base_url}/api/v1/strategies/create",
            json=strategy_data
        ) as resp:
            return await resp.json()
    
    async def list_strategies(self) -> Dict:
        """List all strategies"""
        async with self.session.get(f"{self.base_url}/api/v1/strategies/list") as resp:
            return await resp.json()
    
    async def get_strategy(self, strategy_name: str) -> Dict:
        """Get specific strategy"""
        async with self.session.get(f"{self.base_url}/api/v1/strategies/{strategy_name}") as resp:
            return await resp.json()
    
    async def run_backtest(self, backtest_data: Dict) -> Dict:
        """Run a backtest"""
        async with self.session.post(
            f"{self.base_url}/api/v1/backtesting/run-backtest",
            json=backtest_data
        ) as resp:
            return await resp.json()
    
    async def compare_strategies(self, comparison_data: Dict) -> Dict:
        """Compare multiple strategies"""
        async with self.session.post(
            f"{self.base_url}/api/v1/backtesting/compare-strategies",
            json=comparison_data
        ) as resp:
            return await resp.json()
    
    async def optimize_strategy(self, optimization_data: Dict) -> Dict:
        """Optimize strategy parameters"""
        async with self.session.post(
            f"{self.base_url}/api/v1/backtesting/optimize-strategy",
            json=optimization_data
        ) as resp:
            return await resp.json()
    
    async def get_suggested_parameters(self, strategy_name: str) -> Dict:
        """Get suggested parameter ranges for optimization"""
        async with self.session.get(
            f"{self.base_url}/api/v1/backtesting/suggested-parameters/{strategy_name}"
        ) as resp:
            return await resp.json()

async def demonstrate_strategy_types():
    """Demonstrate getting available strategy types"""
    print("\\n" + "="*50)
    print("1. AVAILABLE STRATEGY TYPES")
    print("="*50)
    
    async with StrategyAPIClient() as client:
        try:
            response = await client.get_strategy_types()
            if response.get("success"):
                types = response["data"]["strategy_types"]
                for strategy_type in types:
                    print(f"\\n📊 {strategy_type['display_name']} ({strategy_type['type']})")
                    print(f"   Description: {strategy_type['description']}")
                    print(f"   Default Parameters: {json.dumps(strategy_type['default_parameters'], indent=6)}")
            else:
                print(f"❌ Error: {response.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Failed to get strategy types: {e}")

async def demonstrate_strategy_creation():
    """Demonstrate creating trading strategies"""
    print("\\n" + "="*50)
    print("2. CREATING TRADING STRATEGIES")
    print("="*50)
    
    strategies_to_create = [
        {
            "strategy_type": "rsi",
            "name": "btc_rsi_conservative",
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
        },
        {
            "strategy_type": "bollinger_bands",
            "name": "eth_bollinger_aggressive",
            "symbols": ["ETHINR"],
            "parameters": {
                "bb_period": 20,
                "bb_std_dev": 2.0
            },
            "risk_settings": {
                "max_position_size": 5000,
                "stop_loss_percent": 3.0
            }
        },
        {
            "strategy_type": "macd",
            "name": "multi_symbol_macd",
            "symbols": ["BTCINR", "ETHINR", "ADAINR"],
            "parameters": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9
            }
        }
    ]
    
    async with StrategyAPIClient() as client:
        for strategy_data in strategies_to_create:
            try:
                print(f"\\n🚀 Creating strategy: {strategy_data['name']}")
                response = await client.create_strategy(strategy_data)
                
                if response.get("success"):
                    print(f"   ✅ Success: {response['message']}")
                    print(f"   📋 Strategy Type: {strategy_data['strategy_type']}")
                    print(f"   💰 Symbols: {', '.join(strategy_data['symbols'])}")
                else:
                    print(f"   ❌ Error: {response.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Failed to create {strategy_data['name']}: {e}")

async def demonstrate_backtesting():
    """Demonstrate running backtests"""
    print("\\n" + "="*50)
    print("3. RUNNING BACKTESTS")
    print("="*50)
    
    # Define backtest parameters
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)  # Last 30 days
    
    backtest_requests = [
        {
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
        },
        {
            "strategy_name": "bollinger_bands",
            "symbols": ["ETHINR"],
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": "1h",
            "initial_capital": 50000.0,
            "strategy_parameters": {
                "bb_period": 20,
                "bb_std_dev": 2.0
            }
        }
    ]
    
    async with StrategyAPIClient() as client:
        for request in backtest_requests:
            try:
                print(f"\\n📈 Running backtest for {request['strategy_name']} on {request['symbols'][0]}")
                print(f"   📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                
                response = await client.run_backtest(request)
                
                if response.get("success"):
                    results = response["data"]["backtest_results"]
                    for result in results:
                        if "error" not in result:
                            print(f"   ✅ Backtest completed successfully!")
                            print(f"   📊 Total Return: {result['total_return_percent']:.2f}%")
                            print(f"   💹 Trades: {result['total_trades']} (Win Rate: {result['win_rate']:.1f}%)")
                            print(f"   📉 Max Drawdown: {result['max_drawdown_percent']:.2f}%")
                            print(f"   ⚡ Sharpe Ratio: {result['sharpe_ratio']:.3f}")
                        else:
                            print(f"   ❌ Backtest error: {result['error']}")
                else:
                    print(f"   ❌ Error: {response.get('message', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   ❌ Failed to run backtest: {e}")

async def demonstrate_strategy_comparison():
    """Demonstrate comparing multiple strategies"""
    print("\\n" + "="*50)
    print("4. STRATEGY COMPARISON")
    print("="*50)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)  # Last 2 weeks
    
    comparison_request = {
        "strategy_names": ["rsi", "bollinger_bands", "macd"],
        "symbols": ["BTCINR"],
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "interval": "1h",
        "initial_capital": 100000.0
    }
    
    async with StrategyAPIClient() as client:
        try:
            print(f"\\n🏆 Comparing strategies on BTCINR")
            print(f"   📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            response = await client.compare_strategies(comparison_request)
            
            if response.get("success"):
                report = response["data"]["comparison_report"]
                print(f"   ✅ Comparison completed!")
                
                # Display ranking
                print(f"\\n   🥇 STRATEGY RANKINGS:")
                rankings = report.get("rankings", {})
                for metric, ranking in rankings.items():
                    print(f"   \\n   📊 By {metric.replace('_', ' ').title()}:")
                    for i, strategy in enumerate(ranking[:3], 1):
                        print(f"      {i}. {strategy['strategy']} - {strategy['value']:.3f}")
                
                # Display summary stats
                summary = report.get("summary_stats", {})
                if summary:
                    print(f"\\n   📈 SUMMARY STATISTICS:")
                    for strategy, stats in summary.items():
                        print(f"   \\n   🔹 {strategy}:")
                        print(f"      Return: {stats.get('total_return_percent', 0):.2f}%")
                        print(f"      Sharpe: {stats.get('sharpe_ratio', 0):.3f}")
                        print(f"      Trades: {stats.get('total_trades', 0)}")
                        print(f"      Win Rate: {stats.get('win_rate', 0):.1f}%")
            else:
                print(f"   ❌ Error: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Failed to compare strategies: {e}")

async def demonstrate_parameter_optimization():
    """Demonstrate parameter optimization"""
    print("\\n" + "="*50)
    print("5. PARAMETER OPTIMIZATION")
    print("="*50)
    
    async with StrategyAPIClient() as client:
        # First, get suggested parameters
        try:
            print("\\n🔧 Getting suggested parameters for RSI strategy...")
            suggestions = await client.get_suggested_parameters("rsi")
            
            if suggestions.get("success"):
                param_ranges = suggestions["data"]["parameter_ranges"]
                print("   ✅ Parameter suggestions retrieved!")
                
                for param, config in param_ranges.items():
                    print(f"   📋 {param}: {config['description']}")
                    if config["type"] == "range":
                        print(f"      Range: {config['start']} to {config['end']} (step: {config['step']})")
                    else:
                        print(f"      Choices: {config['values']}")
                
                # Run optimization
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)  # Last week
                
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
                
                print(f"\\n⚡ Running parameter optimization...")
                print(f"   📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                print(f"   🎯 Optimizing: Sharpe Ratio")
                
                opt_response = await client.optimize_strategy(optimization_request)
                
                if opt_response.get("success"):
                    data = opt_response["data"]
                    print(f"   ✅ Optimization completed!")
                    print(f"   🏆 Best Parameters: {json.dumps(data['best_parameters'], indent=6)}")
                    print(f"   📊 Best Score: {data['best_score']:.3f}")
                    print(f"   🧪 Tests Run: {data['successful_tests']}/{data['total_combinations_tested']}")
                    
                    # Show top 3 results
                    print(f"\\n   🏅 TOP 3 PARAMETER COMBINATIONS:")
                    for i, result in enumerate(data['top_10_results'][:3], 1):
                        print(f"   {i}. Score: {result['score']:.3f}")
                        print(f"      Parameters: {json.dumps(result['parameters'], indent=9)}")
                        print(f"      Return: {result['total_return_percent']:.2f}%")
                        print(f"      Trades: {result['total_trades']}")
                else:
                    print(f"   ❌ Optimization failed: {opt_response.get('message', 'Unknown error')}")
            else:
                print(f"   ❌ Failed to get suggestions: {suggestions.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Failed parameter optimization: {e}")

async def demonstrate_strategy_management():
    """Demonstrate strategy management operations"""
    print("\\n" + "="*50)
    print("6. STRATEGY MANAGEMENT")
    print("="*50)
    
    async with StrategyAPIClient() as client:
        try:
            # List current strategies
            print("\\n📋 Current strategies:")
            response = await client.list_strategies()
            
            if response.get("success"):
                data = response["data"]
                print(f"   Total: {data['total_count']}, Active: {data['active_count']}")
                
                for strategy in data["strategies"][:3]:  # Show first 3
                    print(f"   \\n   🔹 {strategy['name']}")
                    print(f"      Type: {strategy['display_name']}")
                    print(f"      Symbols: {', '.join(strategy['symbols'])}")
                    print(f"      Active: {'✅' if strategy['is_active'] else '❌'}")
                    print(f"      Signals: {strategy['signal_count']}")
            else:
                print(f"   ❌ Error: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Failed to list strategies: {e}")

async def main():
    """Run all demonstration examples"""
    print("🚀 COINDCX ALGORITHMIC TRADING PLATFORM")
    print("Advanced Strategy Management & Backtesting Demo")
    print("=" * 60)
    
    # Wait a moment for server startup
    print("\\n⏳ Waiting for server to be ready...")
    await asyncio.sleep(2)
    
    try:
        # Run all demonstrations
        await demonstrate_strategy_types()
        await demonstrate_strategy_creation()
        await demonstrate_backtesting()
        await demonstrate_strategy_comparison()
        await demonstrate_parameter_optimization()
        await demonstrate_strategy_management()
        
        print("\\n" + "="*60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("\\n📚 What you can do next:")
        print("1. 🌐 Visit http://localhost:8000/docs for interactive API documentation")
        print("2. 🔄 Create your own strategies with custom parameters")
        print("3. 📊 Run backtests on different time periods and symbols")
        print("4. ⚡ Optimize parameters for better performance")
        print("5. 🏆 Compare strategies to find the best performers")
        print("6. 🔴 Activate strategies for live trading (when ready)")
        
        print("\\n💡 API Endpoints Available:")
        print("   • GET  /api/v1/strategies/types - Get available strategy types")
        print("   • POST /api/v1/strategies/create - Create new strategy")
        print("   • GET  /api/v1/strategies/list - List all strategies")
        print("   • POST /api/v1/backtesting/run-backtest - Run backtest")
        print("   • POST /api/v1/backtesting/compare-strategies - Compare strategies")
        print("   • POST /api/v1/backtesting/optimize-strategy - Optimize parameters")
        print("   • GET  /api/v1/market/symbols - Get available trading pairs")
        print("   • GET  /api/v1/market/ticker/{symbol} - Get real-time prices")
        
    except Exception as e:
        print(f"\\n❌ Demo failed with error: {e}")
        print("\\n🔧 Troubleshooting:")
        print("1. Make sure the FastAPI server is running: python -m app.main")
        print("2. Check that the server is accessible at http://localhost:8000")
        print("3. Verify your internet connection for market data")

if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
