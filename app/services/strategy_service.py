import asyncio
import logging
from typing import Dict, List, Optional, Any, Type
from datetime import datetime
import json
from sqlalchemy.orm import Session
from app.strategies.base_strategy import BaseStrategy, MomentumStrategy, MeanReversionStrategy
from app.services.market_data_service import MarketDataService
from app.services.order_manager import OrderManager
from app.services.notification_service import NotificationService
from app.core.config import get_settings
from app.models.database import Strategy, StrategyStatus

logger = logging.getLogger(__name__)

class StrategyService:
    """Service for managing trading strategies"""
    
    def __init__(self):
        self.settings = get_settings()
        self.is_running = False
        self.strategies: Dict[str, BaseStrategy] = {}
        self.strategy_configs: Dict[str, Dict] = {}
        self._tasks: List[asyncio.Task] = []
        
        # Service dependencies
        self.market_data_service: Optional[MarketDataService] = None
        self.order_manager: Optional[OrderManager] = None
        self.notification_service: Optional[NotificationService] = None
        
        # Strategy class registry
        self.strategy_classes: Dict[str, Type[BaseStrategy]] = {
            "momentum": MomentumStrategy,
            "mean_reversion": MeanReversionStrategy
        }
    
    def set_services(self, 
                    market_data_service: MarketDataService,
                    order_manager: OrderManager,
                    notification_service: NotificationService):
        """Set service dependencies"""
        self.market_data_service = market_data_service
        self.order_manager = order_manager
        self.notification_service = notification_service
    
    async def start(self):
        """Start strategy service"""
        if self.is_running:
            return
        
        logger.info("Starting Strategy Service")
        self.is_running = True
        
        # Load strategies from database
        await self._load_strategies()
        
        # Start strategy execution loop
        self._tasks.append(
            asyncio.create_task(self._strategy_execution_loop())
        )
        
        # Start performance monitoring
        self._tasks.append(
            asyncio.create_task(self._performance_monitoring_loop())
        )
    
    async def stop(self):
        """Stop strategy service"""
        if not self.is_running:
            return
        
        logger.info("Stopping Strategy Service")
        self.is_running = False
        
        # Stop all strategies
        for strategy in self.strategies.values():
            await strategy.stop()
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
    
    async def _strategy_execution_loop(self):
        """Main strategy execution loop"""
        while self.is_running:
            try:
                # Execute all active strategies
                for strategy_name, strategy in self.strategies.items():
                    if strategy.is_active:
                        try:
                            signals = await strategy.execute()
                            if signals:
                                logger.info(f"Strategy {strategy_name} generated {len(signals)} signals")
                        except Exception as e:
                            logger.error(f"Error executing strategy {strategy_name}: {e}")
                            await self.notification_service.send_strategy_notification(
                                strategy_name, "error", f"Execution error: {str(e)}"
                            )
                
                # Wait for next execution cycle
                await asyncio.sleep(self.settings.STRATEGY_EXECUTION_INTERVAL)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in strategy execution loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _performance_monitoring_loop(self):
        """Monitor strategy performance and send alerts"""
        while self.is_running:
            try:
                for strategy_name, strategy in self.strategies.items():
                    if strategy.is_active:
                        # Check performance metrics
                        await self._check_strategy_performance(strategy)
                
                # Send daily summary at end of day
                await self._send_daily_summary()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in performance monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _check_strategy_performance(self, strategy: BaseStrategy):
        """Check strategy performance and send alerts"""
        try:
            # Check if strategy hit risk limits
            if not strategy.check_risk_limits():
                await strategy.pause()
                await self.notification_service.send_risk_alert(
                    "strategy_risk_limit",
                    f"Strategy {strategy.name} paused due to risk limits"
                )
            
            # Send P&L updates for significant changes
            if abs(strategy.pnl_today) > 1000:  # Significant P&L change
                pnl_data = {
                    "strategy_id": strategy.name,
                    "symbol": "All",
                    "realized_pnl": strategy.pnl_today,
                    "unrealized_pnl": 0.0,
                    "total_pnl": strategy.pnl_today,
                    "trade_count": strategy.trades_today,
                    "win_rate": 0.0  # Would need more detailed tracking
                }
                await self.notification_service.send_pnl_notification(pnl_data)
                
        except Exception as e:
            logger.error(f"Error checking strategy performance: {e}")
    
    async def _send_daily_summary(self):
        """Send daily summary of all strategies"""
        current_hour = datetime.now().hour
        if current_hour == 23:  # Send summary at 11 PM
            try:
                total_trades = sum(s.trades_today for s in self.strategies.values())
                total_pnl = sum(s.pnl_today for s in self.strategies.values())
                active_strategies = sum(1 for s in self.strategies.values() if s.is_active)
                
                summary_data = {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "total_trades": total_trades,
                    "winning_trades": 0,  # Would need detailed tracking
                    "losing_trades": 0,   # Would need detailed tracking
                    "win_rate": 0.0,
                    "total_pnl": total_pnl,
                    "best_trade": 0.0,    # Would need detailed tracking
                    "worst_trade": 0.0,   # Would need detailed tracking
                    "active_strategies": active_strategies
                }
                
                await self.notification_service.send_daily_summary(summary_data)
                
            except Exception as e:
                logger.error(f"Error sending daily summary: {e}")
    
    async def create_strategy(self, 
                            name: str,
                            strategy_type: str,
                            symbols: List[str],
                            parameters: Dict[str, Any],
                            risk_settings: Dict[str, Any],
                            db: Optional[Session] = None) -> Optional[str]:
        """Create a new strategy"""
        try:
            if name in self.strategies:
                raise ValueError(f"Strategy {name} already exists")
            
            if strategy_type not in self.strategy_classes:
                raise ValueError(f"Unknown strategy type: {strategy_type}")
            
            # Create strategy instance
            strategy_class = self.strategy_classes[strategy_type]
            strategy = strategy_class(symbols, parameters, risk_settings)
            strategy.name = name
            
            # Set service dependencies
            strategy.set_services(
                self.market_data_service,
                self.order_manager,
                self.notification_service
            )
            
            # Save to database
            if db:
                db_strategy = Strategy(
                    name=name,
                    strategy_type=strategy_type,
                    symbols=json.dumps(symbols),
                    parameters=json.dumps(parameters),
                    risk_settings=json.dumps(risk_settings),
                    status=StrategyStatus.ACTIVE
                )
                db.add(db_strategy)
                db.commit()
            
            # Add to active strategies
            self.strategies[name] = strategy
            self.strategy_configs[name] = {
                "type": strategy_type,
                "symbols": symbols,
                "parameters": parameters,
                "risk_settings": risk_settings
            }
            
            await self.notification_service.send_strategy_notification(
                name, "created", f"Strategy created with {len(symbols)} symbols"
            )
            
            logger.info(f"Strategy {name} created successfully")
            return name
            
        except Exception as e:
            logger.error(f"Error creating strategy {name}: {e}")
            return None
    
    async def start_strategy(self, name: str, db: Optional[Session] = None) -> bool:
        """Start a strategy"""
        try:
            if name not in self.strategies:
                logger.error(f"Strategy {name} not found")
                return False
            
            strategy = self.strategies[name]
            await strategy.start()
            
            # Update database
            if db:
                db_strategy = db.query(Strategy).filter(Strategy.name == name).first()
                if db_strategy:
                    db_strategy.status = StrategyStatus.ACTIVE
                    db_strategy.started_at = datetime.now()
                    db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting strategy {name}: {e}")
            return False
    
    async def stop_strategy(self, name: str, db: Optional[Session] = None) -> bool:
        """Stop a strategy"""
        try:
            if name not in self.strategies:
                logger.error(f"Strategy {name} not found")
                return False
            
            strategy = self.strategies[name]
            await strategy.stop()
            
            # Update database
            if db:
                db_strategy = db.query(Strategy).filter(Strategy.name == name).first()
                if db_strategy:
                    db_strategy.status = StrategyStatus.STOPPED
                    db_strategy.stopped_at = datetime.now()
                    db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping strategy {name}: {e}")
            return False
    
    async def pause_strategy(self, name: str, db: Optional[Session] = None) -> bool:
        """Pause a strategy"""
        try:
            if name not in self.strategies:
                logger.error(f"Strategy {name} not found")
                return False
            
            strategy = self.strategies[name]
            await strategy.pause()
            
            # Update database
            if db:
                db_strategy = db.query(Strategy).filter(Strategy.name == name).first()
                if db_strategy:
                    db_strategy.status = StrategyStatus.PAUSED
                    db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error pausing strategy {name}: {e}")
            return False
    
    async def delete_strategy(self, name: str, db: Optional[Session] = None) -> bool:
        """Delete a strategy"""
        try:
            if name in self.strategies:
                # Stop strategy first
                await self.stop_strategy(name, db)
                
                # Remove from memory
                del self.strategies[name]
                if name in self.strategy_configs:
                    del self.strategy_configs[name]
            
            # Remove from database
            if db:
                db_strategy = db.query(Strategy).filter(Strategy.name == name).first()
                if db_strategy:
                    db.delete(db_strategy)
                    db.commit()
            
            await self.notification_service.send_strategy_notification(
                name, "deleted", "Strategy has been deleted"
            )
            
            logger.info(f"Strategy {name} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting strategy {name}: {e}")
            return False
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get strategy by name"""
        return self.strategies.get(name)
    
    def get_all_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Get all strategies with their info"""
        return {
            name: strategy.get_strategy_info()
            for name, strategy in self.strategies.items()
        }
    
    def get_strategy_types(self) -> List[str]:
        """Get available strategy types"""
        return list(self.strategy_classes.keys())
    
    async def _load_strategies(self, db: Optional[Session] = None):
        """Load strategies from database"""
        try:
            if not db:
                return
            
            db_strategies = db.query(Strategy).filter(
                Strategy.status.in_([StrategyStatus.ACTIVE, StrategyStatus.PAUSED])
            ).all()
            
            for db_strategy in db_strategies:
                try:
                    symbols = json.loads(db_strategy.symbols)
                    parameters = json.loads(db_strategy.parameters)
                    risk_settings = json.loads(db_strategy.risk_settings)
                    
                    if db_strategy.strategy_type in self.strategy_classes:
                        strategy_class = self.strategy_classes[db_strategy.strategy_type]
                        strategy = strategy_class(symbols, parameters, risk_settings)
                        strategy.name = db_strategy.name
                        
                        # Set service dependencies
                        strategy.set_services(
                            self.market_data_service,
                            self.order_manager,
                            self.notification_service
                        )
                        
                        # Set active status
                        if db_strategy.status == StrategyStatus.ACTIVE:
                            strategy.is_active = True
                        
                        self.strategies[db_strategy.name] = strategy
                        self.strategy_configs[db_strategy.name] = {
                            "type": db_strategy.strategy_type,
                            "symbols": symbols,
                            "parameters": parameters,
                            "risk_settings": risk_settings
                        }
                        
                        logger.info(f"Loaded strategy {db_strategy.name} from database")
                    
                except Exception as e:
                    logger.error(f"Error loading strategy {db_strategy.name}: {e}")
            
        except Exception as e:
            logger.error(f"Error loading strategies from database: {e}")
    
    async def update_strategy_parameters(self, 
                                       name: str, 
                                       parameters: Dict[str, Any],
                                       db: Optional[Session] = None) -> bool:
        """Update strategy parameters"""
        try:
            if name not in self.strategies:
                logger.error(f"Strategy {name} not found")
                return False
            
            strategy = self.strategies[name]
            
            # Update parameters
            strategy.parameters.update(parameters)
            
            # Update database
            if db:
                db_strategy = db.query(Strategy).filter(Strategy.name == name).first()
                if db_strategy:
                    db_strategy.parameters = json.dumps(strategy.parameters)
                    db_strategy.updated_at = datetime.now()
                    db.commit()
            
            await self.notification_service.send_strategy_notification(
                name, "updated", "Strategy parameters updated"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating strategy parameters: {e}")
            return False
