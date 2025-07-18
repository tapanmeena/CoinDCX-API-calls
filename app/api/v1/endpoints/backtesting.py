"""
Backtesting API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import asyncio
import logging

from app.strategies.backtesting import BacktestEngine, StrategyComparison, BacktestReportGenerator
from app.strategies.advanced_strategies import (
    RSIStrategy, BollingerBandsStrategy, MACDStrategy, 
    VolumeBreakoutStrategy, GridTradingStrategy
)
from app.strategies.base_strategy import BaseStrategy
from app.models.schemas import ApiResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class BacktestRequest(BaseModel):
    strategy_name: str = Field(..., description="Strategy name")
    symbols: List[str] = Field(..., description="List of symbols to test")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    interval: str = Field(default="1h", description="Data interval (1m, 5m, 15m, 1h, 1d)")
    initial_capital: float = Field(default=100000.0, description="Initial capital for backtest")
    strategy_parameters: Optional[Dict[str, Any]] = Field(default=None, description="Strategy parameters")
    risk_settings: Optional[Dict[str, Any]] = Field(default=None, description="Risk management settings")

class StrategyComparisonRequest(BaseModel):
    strategy_names: List[str] = Field(..., description="List of strategy names to compare")
    symbols: List[str] = Field(..., description="List of symbols to test")
    start_date: datetime = Field(..., description="Backtest start date")
    end_date: datetime = Field(..., description="Backtest end date")
    interval: str = Field(default="1h", description="Data interval")
    initial_capital: float = Field(default=100000.0, description="Initial capital")

class OptimizationRequest(BaseModel):
    strategy_name: str = Field(..., description="Strategy to optimize")
    symbol: str = Field(..., description="Symbol to optimize on")
    start_date: datetime = Field(..., description="Optimization start date")
    end_date: datetime = Field(..., description="Optimization end date")
    parameter_ranges: Dict[str, Dict[str, Any]] = Field(..., description="Parameter ranges for optimization")
    optimization_metric: str = Field(default="sharpe_ratio", description="Metric to optimize")

# Available strategies registry
STRATEGY_REGISTRY = {
    "rsi": RSIStrategy,
    "bollinger_bands": BollingerBandsStrategy, 
    "macd": MACDStrategy,
    "volume_breakout": VolumeBreakoutStrategy,
    "grid_trading": GridTradingStrategy
}

def create_strategy(strategy_name: str, symbols: List[str], parameters: Dict = None, risk_settings: Dict = None) -> BaseStrategy:
    """Create strategy instance from name"""
    if strategy_name.lower() not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    strategy_class = STRATEGY_REGISTRY[strategy_name.lower()]
    return strategy_class(symbols, parameters, risk_settings)

@router.get("/available-strategies", response_model=ApiResponse)
async def get_available_strategies():
    """Get list of available strategies for backtesting"""
    strategies = []
    
    for name, strategy_class in STRATEGY_REGISTRY.items():
        # Create a sample instance to get default parameters
        sample_strategy = strategy_class(["BTCINR"])
        
        strategies.append({
            "name": name,
            "display_name": sample_strategy.name,
            "default_parameters": sample_strategy.parameters,
            "default_risk_settings": sample_strategy.risk_settings,
            "description": strategy_class.__doc__ or "No description available"
        })
    
    return ApiResponse(
        success=True,
        message="Available strategies retrieved successfully",
        data={
            "strategies": strategies,
            "total_count": len(strategies)
        }
    )

@router.post("/run-backtest", response_model=ApiResponse)
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """Run backtest for a single strategy"""
    try:
        # Validate dates
        if request.start_date >= request.end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        if request.end_date > datetime.now():
            raise HTTPException(status_code=400, detail="End date cannot be in the future")
        
        # Create strategy
        strategy = create_strategy(
            request.strategy_name, 
            request.symbols,
            request.strategy_parameters,
            request.risk_settings
        )
        
        # Create backtest engine
        engine = BacktestEngine(request.initial_capital)
        
        # Run backtests for all symbols
        results = []
        for symbol in request.symbols:
            try:
                result = await engine.run_backtest(
                    strategy=strategy,
                    symbol=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date,
                    interval=request.interval
                )
                
                # Convert result to dict for JSON serialization
                result_dict = {
                    "strategy_name": result.strategy_name,
                    "symbol": result.symbol,
                    "start_date": result.start_date.isoformat(),
                    "end_date": result.end_date.isoformat(),
                    "total_trades": result.total_trades,
                    "winning_trades": result.winning_trades,
                    "losing_trades": result.losing_trades,
                    "win_rate": result.win_rate,
                    "total_return": result.total_return,
                    "total_return_percent": result.total_return_percent,
                    "annualized_return": result.annualized_return,
                    "max_drawdown": result.max_drawdown,
                    "max_drawdown_percent": result.max_drawdown_percent,
                    "sharpe_ratio": result.sharpe_ratio,
                    "sortino_ratio": result.sortino_ratio,
                    "avg_trade_return": result.avg_trade_return,
                    "avg_winning_trade": result.avg_winning_trade,
                    "avg_losing_trade": result.avg_losing_trade,
                    "largest_win": result.largest_win,
                    "largest_loss": result.largest_loss,
                    "total_fees": result.total_fees
                }
                
                results.append(result_dict)
                
            except Exception as e:
                logger.error(f"Error backtesting {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "error": str(e)
                })
        
        return ApiResponse(
            success=True,
            message=f"Backtest completed for {request.strategy_name}",
            data={
                "backtest_results": results,
                "request_info": {
                    "strategy": request.strategy_name,
                    "symbols": request.symbols,
                    "start_date": request.start_date.isoformat(),
                    "end_date": request.end_date.isoformat(),
                    "interval": request.interval,
                    "initial_capital": request.initial_capital
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@router.post("/compare-strategies", response_model=ApiResponse)
async def compare_strategies(request: StrategyComparisonRequest):
    """Compare multiple strategies"""
    try:
        # Create strategies
        strategies = []
        for strategy_name in request.strategy_names:
            strategy = create_strategy(strategy_name, request.symbols)
            strategies.append(strategy)
        
        # Run comparison
        comparison = StrategyComparison(request.initial_capital)
        comparison_results = await comparison.compare_strategies(
            strategies=strategies,
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            interval=request.interval
        )
        
        # Generate comparison report
        comparison_report = comparison.generate_comparison_report(comparison_results)
        
        return ApiResponse(
            success=True,
            message="Strategy comparison completed",
            data={
                "comparison_report": comparison_report,
                "request_info": {
                    "strategies": request.strategy_names,
                    "symbols": request.symbols,
                    "start_date": request.start_date.isoformat(),
                    "end_date": request.end_date.isoformat()
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error comparing strategies: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy comparison failed: {str(e)}")

@router.post("/optimize-strategy", response_model=ApiResponse)
async def optimize_strategy(request: OptimizationRequest):
    """Optimize strategy parameters"""
    try:
        # Parameter optimization using grid search
        best_params = None
        best_score = float('-inf')
        optimization_results = []
        
        # Generate parameter combinations
        param_combinations = []
        
        def generate_combinations(param_ranges, current_params=None):
            if current_params is None:
                current_params = {}
            
            if not param_ranges:
                param_combinations.append(current_params.copy())
                return
            
            param_name, param_range = list(param_ranges.items())[0]
            remaining_ranges = {k: v for k, v in param_ranges.items() if k != param_name}
            
            # Handle different parameter types
            if param_range["type"] == "range":
                start = param_range["start"]
                end = param_range["end"]
                step = param_range.get("step", 1)
                
                values = []
                current = start
                while current <= end:
                    values.append(current)
                    current += step
            
            elif param_range["type"] == "choices":
                values = param_range["values"]
            
            else:
                raise ValueError(f"Unknown parameter type: {param_range['type']}")
            
            for value in values:
                current_params[param_name] = value
                generate_combinations(remaining_ranges, current_params)
                del current_params[param_name]
        
        generate_combinations(request.parameter_ranges)
        
        # Limit combinations to prevent excessive computation
        if len(param_combinations) > 100:
            param_combinations = param_combinations[:100]
            logger.warning(f"Limited parameter combinations to 100 for performance")
        
        # Test each parameter combination
        for i, params in enumerate(param_combinations):
            try:
                strategy = create_strategy(request.strategy_name, [request.symbol], params)
                engine = BacktestEngine()
                
                result = await engine.run_backtest(
                    strategy=strategy,
                    symbol=request.symbol,
                    start_date=request.start_date,
                    end_date=request.end_date
                )
                
                # Get optimization metric value
                if request.optimization_metric == "sharpe_ratio":
                    score = result.sharpe_ratio
                elif request.optimization_metric == "total_return":
                    score = result.total_return_percent
                elif request.optimization_metric == "win_rate":
                    score = result.win_rate
                elif request.optimization_metric == "profit_factor":
                    if result.avg_losing_trade != 0:
                        score = abs(result.avg_winning_trade / result.avg_losing_trade)
                    else:
                        score = float('inf') if result.avg_winning_trade > 0 else 0
                else:
                    score = result.total_return_percent  # Default to total return
                
                optimization_results.append({
                    "parameters": params,
                    "score": score,
                    "total_return_percent": result.total_return_percent,
                    "sharpe_ratio": result.sharpe_ratio,
                    "win_rate": result.win_rate,
                    "total_trades": result.total_trades,
                    "max_drawdown_percent": result.max_drawdown_percent
                })
                
                if score > best_score:
                    best_score = score
                    best_params = params.copy()
                
            except Exception as e:
                logger.error(f"Error testing parameters {params}: {e}")
                optimization_results.append({
                    "parameters": params,
                    "error": str(e)
                })
        
        # Sort results by score
        valid_results = [r for r in optimization_results if "error" not in r]
        valid_results.sort(key=lambda x: x["score"], reverse=True)
        
        return ApiResponse(
            success=True,
            message=f"Strategy optimization completed for {request.strategy_name}",
            data={
                "best_parameters": best_params,
                "best_score": best_score,
                "optimization_metric": request.optimization_metric,
                "top_10_results": valid_results[:10],
                "total_combinations_tested": len(param_combinations),
                "successful_tests": len(valid_results)
            }
        )
        
    except Exception as e:
        logger.error(f"Error optimizing strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Strategy optimization failed: {str(e)}")

@router.get("/backtest-intervals", response_model=ApiResponse)
async def get_backtest_intervals():
    """Get available intervals for backtesting"""
    intervals = [
        {"value": "1m", "label": "1 Minute", "description": "High frequency, large data volume"},
        {"value": "5m", "label": "5 Minutes", "description": "Good for short-term strategies"},
        {"value": "15m", "label": "15 Minutes", "description": "Balanced frequency"},
        {"value": "1h", "label": "1 Hour", "description": "Recommended for most strategies"},
        {"value": "4h", "label": "4 Hours", "description": "Medium-term strategies"},
        {"value": "1d", "label": "1 Day", "description": "Long-term strategies"}
    ]
    
    return ApiResponse(
        success=True,
        message="Available intervals retrieved",
        data={"intervals": intervals}
    )

@router.get("/suggested-parameters/{strategy_name}", response_model=ApiResponse)
async def get_suggested_parameters(strategy_name: str):
    """Get suggested parameter ranges for optimization"""
    parameter_suggestions = {
        "rsi": {
            "rsi_period": {
                "type": "range",
                "start": 10,
                "end": 20,
                "step": 2,
                "description": "RSI calculation period"
            },
            "rsi_overbought": {
                "type": "range", 
                "start": 65,
                "end": 80,
                "step": 5,
                "description": "RSI overbought threshold"
            },
            "rsi_oversold": {
                "type": "range",
                "start": 20,
                "end": 35,
                "step": 5,
                "description": "RSI oversold threshold"
            }
        },
        "bollinger_bands": {
            "bb_period": {
                "type": "range",
                "start": 15,
                "end": 25,
                "step": 5,
                "description": "Bollinger Bands period"
            },
            "bb_std_dev": {
                "type": "choices",
                "values": [1.5, 2.0, 2.5],
                "description": "Standard deviation multiplier"
            }
        },
        "macd": {
            "fast_period": {
                "type": "range",
                "start": 8,
                "end": 16,
                "step": 2,
                "description": "Fast EMA period"
            },
            "slow_period": {
                "type": "range",
                "start": 20,
                "end": 30,
                "step": 2,
                "description": "Slow EMA period"
            },
            "signal_period": {
                "type": "range",
                "start": 7,
                "end": 12,
                "step": 1,
                "description": "Signal line EMA period"
            }
        },
        "volume_breakout": {
            "volume_threshold": {
                "type": "choices",
                "values": [1.5, 2.0, 2.5, 3.0],
                "description": "Volume spike threshold"
            },
            "price_breakout_percent": {
                "type": "range",
                "start": 1.0,
                "end": 3.0,
                "step": 0.5,
                "description": "Price breakout percentage"
            }
        },
        "grid_trading": {
            "grid_levels": {
                "type": "range",
                "start": 5,
                "end": 15,
                "step": 2,
                "description": "Number of grid levels"
            },
            "grid_spacing_percent": {
                "type": "choices",
                "values": [1.0, 1.5, 2.0, 2.5],
                "description": "Grid spacing percentage"
            }
        }
    }
    
    if strategy_name.lower() not in parameter_suggestions:
        raise HTTPException(status_code=404, detail=f"No parameter suggestions available for {strategy_name}")
    
    return ApiResponse(
        success=True,
        message=f"Parameter suggestions for {strategy_name}",
        data={
            "strategy": strategy_name,
            "parameter_ranges": parameter_suggestions[strategy_name.lower()],
            "optimization_metrics": [
                {"value": "sharpe_ratio", "label": "Sharpe Ratio", "description": "Risk-adjusted returns"},
                {"value": "total_return", "label": "Total Return", "description": "Absolute return percentage"},
                {"value": "win_rate", "label": "Win Rate", "description": "Percentage of winning trades"},
                {"value": "profit_factor", "label": "Profit Factor", "description": "Ratio of avg win to avg loss"}
            ]
        }
    )
