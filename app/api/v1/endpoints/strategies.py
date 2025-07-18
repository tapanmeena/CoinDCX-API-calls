"""
Advanced Strategy Management API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import asyncio
import logging
import json

from app.strategies.advanced_strategies import (
    RSIStrategy, BollingerBandsStrategy, MACDStrategy, 
    VolumeBreakoutStrategy, GridTradingStrategy
)
from app.strategies.base_strategy import BaseStrategy
from app.services.market_data_service import MarketDataService
from app.models.schemas import ApiResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Strategy configuration models
class StrategyConfig(BaseModel):
    name: str = Field(..., description="Strategy name")
    display_name: str = Field(..., description="Human-readable strategy name")
    symbols: List[str] = Field(..., description="Trading symbols")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    risk_settings: Dict[str, Any] = Field(default_factory=dict, description="Risk management settings")
    is_active: bool = Field(default=False, description="Whether strategy is active")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")

class CreateStrategyRequest(BaseModel):
    strategy_type: str = Field(..., description="Type of strategy (rsi, bollinger_bands, etc.)")
    name: str = Field(..., description="Custom name for this strategy instance")
    symbols: List[str] = Field(..., description="Trading symbols")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Custom parameters")
    risk_settings: Optional[Dict[str, Any]] = Field(default=None, description="Risk management settings")

class UpdateStrategyRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Updated parameters")
    risk_settings: Optional[Dict[str, Any]] = Field(default=None, description="Updated risk settings")
    symbols: Optional[List[str]] = Field(default=None, description="Updated symbols")
    is_active: Optional[bool] = Field(default=None, description="Updated active status")

class StrategySignal(BaseModel):
    strategy_name: str
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    price: float
    timestamp: datetime
    reasoning: str

# In-memory strategy storage (replace with database in production)
active_strategies: Dict[str, StrategyConfig] = {}
strategy_signals: Dict[str, List[StrategySignal]] = {}

# Available strategy types
STRATEGY_TYPES = {
    "rsi": RSIStrategy,
    "bollinger_bands": BollingerBandsStrategy,
    "macd": MACDStrategy,
    "volume_breakout": VolumeBreakoutStrategy,
    "grid_trading": GridTradingStrategy
}

def create_strategy_instance(strategy_type: str, symbols: List[str], parameters: Dict = None, risk_settings: Dict = None) -> BaseStrategy:
    """Create strategy instance from type"""
    if strategy_type.lower() not in STRATEGY_TYPES:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    strategy_class = STRATEGY_TYPES[strategy_type.lower()]
    return strategy_class(symbols, parameters, risk_settings)

@router.get("/types", response_model=ApiResponse)
async def get_strategy_types():
    """Get available strategy types"""
    types = []
    
    for name, strategy_class in STRATEGY_TYPES.items():
        # Create sample instance to get default configuration
        sample_strategy = strategy_class(["BTCINR"])
        
        types.append({
            "type": name,
            "display_name": sample_strategy.name,
            "description": strategy_class.__doc__ or "No description available",
            "default_parameters": sample_strategy.parameters,
            "default_risk_settings": sample_strategy.risk_settings,
            "required_indicators": getattr(sample_strategy, 'required_indicators', [])
        })
    
    return ApiResponse(
        success=True,
        message="Strategy types retrieved successfully",
        data={"strategy_types": types}
    )

@router.post("/create", response_model=ApiResponse)
async def create_strategy(request: CreateStrategyRequest):
    """Create a new strategy configuration"""
    try:
        # Validate strategy type
        if request.strategy_type.lower() not in STRATEGY_TYPES:
            raise HTTPException(status_code=400, detail=f"Unknown strategy type: {request.strategy_type}")
        
        # Check if strategy name already exists
        if request.name in active_strategies:
            raise HTTPException(status_code=400, detail=f"Strategy with name '{request.name}' already exists")
        
        # Create strategy instance to validate parameters
        strategy_instance = create_strategy_instance(
            request.strategy_type,
            request.symbols,
            request.parameters,
            request.risk_settings
        )
        
        # Create strategy configuration
        config = StrategyConfig(
            name=request.name,
            display_name=strategy_instance.name,
            symbols=request.symbols,
            parameters=strategy_instance.parameters,
            risk_settings=strategy_instance.risk_settings,
            is_active=False
        )
        
        # Store configuration
        active_strategies[request.name] = config
        strategy_signals[request.name] = []
        
        return ApiResponse(
            success=True,
            message=f"Strategy '{request.name}' created successfully",
            data={
                "strategy": config.dict(),
                "strategy_type": request.strategy_type
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create strategy: {str(e)}")

@router.get("/list", response_model=ApiResponse)
async def list_strategies():
    """Get all configured strategies"""
    strategies = []
    
    for name, config in active_strategies.items():
        strategy_data = config.dict()
        strategy_data["signal_count"] = len(strategy_signals.get(name, []))
        strategies.append(strategy_data)
    
    return ApiResponse(
        success=True,
        message="Strategies retrieved successfully",
        data={
            "strategies": strategies,
            "total_count": len(strategies),
            "active_count": sum(1 for s in active_strategies.values() if s.is_active)
        }
    )

@router.get("/{strategy_name}", response_model=ApiResponse)
async def get_strategy(strategy_name: str):
    """Get specific strategy configuration"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    config = active_strategies[strategy_name]
    strategy_data = config.dict()
    strategy_data["signal_count"] = len(strategy_signals.get(strategy_name, []))
    strategy_data["recent_signals"] = strategy_signals.get(strategy_name, [])[-10:]  # Last 10 signals
    
    return ApiResponse(
        success=True,
        message="Strategy retrieved successfully",
        data={"strategy": strategy_data}
    )

@router.put("/{strategy_name}", response_model=ApiResponse)
async def update_strategy(strategy_name: str, request: UpdateStrategyRequest):
    """Update strategy configuration"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    config = active_strategies[strategy_name]
    
    try:
        # Update fields if provided
        if request.parameters is not None:
            config.parameters.update(request.parameters)
        
        if request.risk_settings is not None:
            config.risk_settings.update(request.risk_settings)
        
        if request.symbols is not None:
            config.symbols = request.symbols
        
        if request.is_active is not None:
            config.is_active = request.is_active
        
        # Validate updated configuration by creating strategy instance
        strategy_type = None
        for type_name, strategy_class in STRATEGY_TYPES.items():
            sample = strategy_class(["BTCINR"])
            if sample.name == config.display_name:
                strategy_type = type_name
                break
        
        if strategy_type:
            create_strategy_instance(strategy_type, config.symbols, config.parameters, config.risk_settings)
        
        active_strategies[strategy_name] = config
        
        return ApiResponse(
            success=True,
            message=f"Strategy '{strategy_name}' updated successfully",
            data={"strategy": config.dict()}
        )
        
    except Exception as e:
        logger.error(f"Error updating strategy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update strategy: {str(e)}")

@router.delete("/{strategy_name}", response_model=ApiResponse)
async def delete_strategy(strategy_name: str):
    """Delete strategy configuration"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    # Remove from active strategies
    del active_strategies[strategy_name]
    
    # Remove signals
    if strategy_name in strategy_signals:
        del strategy_signals[strategy_name]
    
    return ApiResponse(
        success=True,
        message=f"Strategy '{strategy_name}' deleted successfully",
        data={"deleted_strategy": strategy_name}
    )

@router.post("/{strategy_name}/activate", response_model=ApiResponse)
async def activate_strategy(strategy_name: str):
    """Activate a strategy for live trading"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    config = active_strategies[strategy_name]
    config.is_active = True
    
    # TODO: Start strategy execution in background
    # This would involve creating the strategy instance and starting signal generation
    
    return ApiResponse(
        success=True,
        message=f"Strategy '{strategy_name}' activated successfully",
        data={"strategy": config.dict()}
    )

@router.post("/{strategy_name}/deactivate", response_model=ApiResponse)
async def deactivate_strategy(strategy_name: str):
    """Deactivate a strategy"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    config = active_strategies[strategy_name]
    config.is_active = False
    
    # TODO: Stop strategy execution
    
    return ApiResponse(
        success=True,
        message=f"Strategy '{strategy_name}' deactivated successfully",
        data={"strategy": config.dict()}
    )

@router.get("/{strategy_name}/signals", response_model=ApiResponse)
async def get_strategy_signals(strategy_name: str, limit: int = 50):
    """Get recent signals from a strategy"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    signals = strategy_signals.get(strategy_name, [])
    recent_signals = signals[-limit:] if len(signals) > limit else signals
    
    # Convert to dict for JSON serialization
    signal_data = []
    for signal in recent_signals:
        signal_data.append({
            "strategy_name": signal.strategy_name,
            "symbol": signal.symbol,
            "signal_type": signal.signal_type,
            "confidence": signal.confidence,
            "price": signal.price,
            "timestamp": signal.timestamp.isoformat(),
            "reasoning": signal.reasoning
        })
    
    return ApiResponse(
        success=True,
        message=f"Signals retrieved for strategy '{strategy_name}'",
        data={
            "signals": signal_data,
            "total_signals": len(signals),
            "returned_count": len(signal_data)
        }
    )

@router.post("/{strategy_name}/test-signal", response_model=ApiResponse)
async def test_strategy_signal(strategy_name: str, symbol: str):
    """Test strategy signal generation for a specific symbol"""
    if strategy_name not in active_strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_name}' not found")
    
    try:
        config = active_strategies[strategy_name]
        
        # Find strategy type
        strategy_type = None
        for type_name, strategy_class in STRATEGY_TYPES.items():
            sample = strategy_class(["BTCINR"])
            if sample.name == config.display_name:
                strategy_type = type_name
                break
        
        if not strategy_type:
            raise HTTPException(status_code=500, detail="Could not determine strategy type")
        
        # Create strategy instance
        strategy = create_strategy_instance(
            strategy_type,
            [symbol],
            config.parameters,
            config.risk_settings
        )
        
        # Get market data service
        market_service = MarketDataService()
        
        # Get current market data
        current_data = market_service.get_ticker(symbol)
        if not current_data:
            raise HTTPException(status_code=404, detail=f"No market data available for {symbol}")
        
        # Generate signal (this is a simplified test)
        # In practice, you'd need historical data for proper signal generation
        signal_info = {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "current_price": current_data.get("last_price", 0),
            "parameters": config.parameters,
            "timestamp": datetime.now().isoformat(),
            "note": "This is a test signal based on current market data only"
        }
        
        return ApiResponse(
            success=True,
            message=f"Test signal generated for {symbol}",
            data={"signal_info": signal_info}
        )
        
    except Exception as e:
        logger.error(f"Error testing strategy signal: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test signal: {str(e)}")

@router.get("/", response_model=ApiResponse)
async def get_strategy_overview():
    """Get overview of all strategies and their performance"""
    overview = {
        "total_strategies": len(active_strategies),
        "active_strategies": sum(1 for s in active_strategies.values() if s.is_active),
        "inactive_strategies": sum(1 for s in active_strategies.values() if not s.is_active),
        "total_signals_generated": sum(len(signals) for signals in strategy_signals.values()),
        "strategies_by_type": {}
    }
    
    # Count strategies by type
    for config in active_strategies.values():
        for type_name, strategy_class in STRATEGY_TYPES.items():
            sample = strategy_class(["BTCINR"])
            if sample.name == config.display_name:
                if type_name not in overview["strategies_by_type"]:
                    overview["strategies_by_type"][type_name] = 0
                overview["strategies_by_type"][type_name] += 1
                break
    
    # Recent activity
    all_recent_signals = []
    for strategy_name, signals in strategy_signals.items():
        for signal in signals[-5:]:  # Last 5 signals per strategy
            all_recent_signals.append({
                "strategy_name": signal.strategy_name,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type,
                "timestamp": signal.timestamp.isoformat()
            })
    
    # Sort by timestamp
    all_recent_signals.sort(key=lambda x: x["timestamp"], reverse=True)
    overview["recent_activity"] = all_recent_signals[:20]  # Show last 20 signals
    
    return ApiResponse(
        success=True,
        message="Strategy overview retrieved successfully",
        data=overview
    )
