from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Enum
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, enum.Enum):
    LIMIT = "limit_order"
    MARKET = "market_order"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"

class StrategyStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"

class Trade(Base):
    """Trade execution record"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    exchange_order_id = Column(String(100), unique=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_quantity = Column(Float, default=0.0)
    executed_price = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    strategy_id = Column(String(50), index=True)
    fees = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    executed_at = Column(DateTime(timezone=True))

class Portfolio(Base):
    """Portfolio holdings"""
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    currency = Column(String(10), unique=True, nullable=False, index=True)
    balance = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    locked_balance = Column(Float, default=0.0)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Strategy(Base):
    """Trading strategy configuration"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    strategy_type = Column(String(50), nullable=False)
    symbols = Column(Text)  # JSON string of symbols
    parameters = Column(Text)  # JSON string of parameters
    status = Column(Enum(StrategyStatus), default=StrategyStatus.ACTIVE)
    risk_settings = Column(Text)  # JSON string of risk parameters
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True))
    stopped_at = Column(DateTime(timezone=True))

class MarketData(Base):
    """Market data cache"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    interval = Column(String(10), nullable=False)
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

class PnL(Base):
    """Profit and Loss tracking"""
    __tablename__ = "pnl"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(50), index=True)
    symbol = Column(String(20), nullable=False, index=True)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    trade_count = Column(Integer, default=0)
    win_count = Column(Integer, default=0)
    loss_count = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    date = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class RiskMetrics(Base):
    """Risk management metrics"""
    __tablename__ = "risk_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(50), index=True)
    daily_pnl = Column(Float, default=0.0)
    daily_trades = Column(Integer, default=0)
    max_drawdown = Column(Float, default=0.0)
    var_95 = Column(Float, default=0.0)  # Value at Risk 95%
    sharpe_ratio = Column(Float, default=0.0)
    exposure = Column(Float, default=0.0)  # Total exposure in INR
    date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
