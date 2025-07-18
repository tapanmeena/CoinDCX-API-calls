from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class OrderSideEnum(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderTypeEnum(str, Enum):
    LIMIT = "limit_order"
    MARKET = "market_order"

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class StrategyStatusEnum(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"

# Request Models
class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading pair symbol (e.g., BTCINR)")
    side: OrderSideEnum = Field(..., description="Order side (buy/sell)")
    order_type: OrderTypeEnum = Field(..., description="Order type")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Order price (required for limit orders)")

class StrategyRequest(BaseModel):
    name: str = Field(..., description="Strategy name")
    description: Optional[str] = Field(None, description="Strategy description")
    strategy_type: str = Field(..., description="Strategy type")
    symbols: List[str] = Field(..., description="Trading symbols")
    parameters: Dict[str, Any] = Field(..., description="Strategy parameters")
    risk_settings: Dict[str, Any] = Field(..., description="Risk management settings")

class StrategyUpdateRequest(BaseModel):
    description: Optional[str] = None
    symbols: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_settings: Optional[Dict[str, Any]] = None
    status: Optional[StrategyStatusEnum] = None

# Response Models
class OrderResponse(BaseModel):
    id: int
    exchange_order_id: Optional[str]
    symbol: str
    side: OrderSideEnum
    order_type: OrderTypeEnum
    quantity: float
    price: float
    executed_quantity: float
    executed_price: float
    status: OrderStatusEnum
    strategy_id: Optional[str]
    fees: float
    created_at: datetime
    updated_at: Optional[datetime]
    executed_at: Optional[datetime]

    class Config:
        from_attributes = True

class PortfolioResponse(BaseModel):
    currency: str
    balance: float
    available_balance: float
    locked_balance: float
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class StrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    strategy_type: str
    symbols: List[str]
    parameters: Dict[str, Any]
    status: StrategyStatusEnum
    risk_settings: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    started_at: Optional[datetime]
    stopped_at: Optional[datetime]

    class Config:
        from_attributes = True

class MarketDataResponse(BaseModel):
    symbol: str
    interval: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    timestamp: datetime

    class Config:
        from_attributes = True

class PnLResponse(BaseModel):
    strategy_id: Optional[str]
    symbol: str
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    trade_count: int
    win_count: int
    loss_count: int
    win_rate: float
    date: datetime

    class Config:
        from_attributes = True

class RiskMetricsResponse(BaseModel):
    strategy_id: Optional[str]
    daily_pnl: float
    daily_trades: int
    max_drawdown: float
    var_95: float
    sharpe_ratio: float
    exposure: float
    date: datetime

    class Config:
        from_attributes = True

class TickerResponse(BaseModel):
    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    timestamp: datetime

class BalanceResponse(BaseModel):
    currency: str
    balance: float
    available_balance: float
    locked_balance: float

class ApiResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None
    error: Optional[str] = None

class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
