from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from app.services.market_data_service import MarketDataService
from app.services.order_manager import OrderManager
from app.services.notification_service import NotificationService
from app.models.schemas import OrderRequest, OrderSideEnum, OrderTypeEnum

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, 
                 name: str,
                 symbols: List[str],
                 parameters: Dict[str, Any],
                 risk_settings: Dict[str, Any]):
        self.name = name
        self.symbols = symbols
        self.parameters = parameters
        self.risk_settings = risk_settings
        self.is_active = False
        self.positions = {}
        self.last_execution = None
        
        # Services
        self.market_data_service: Optional[MarketDataService] = None
        self.order_manager: Optional[OrderManager] = None
        self.notification_service: Optional[NotificationService] = None
        
        # Performance tracking
        self.trades_today = 0
        self.pnl_today = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = 0.0
    
    def set_services(self, 
                    market_data_service: MarketDataService,
                    order_manager: OrderManager,
                    notification_service: NotificationService):
        """Set service references"""
        self.market_data_service = market_data_service
        self.order_manager = order_manager
        self.notification_service = notification_service
    
    @abstractmethod
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute strategy logic and return list of signals/orders"""
        pass
    
    @abstractmethod
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information"""
        pass
    
    async def start(self):
        """Start strategy execution"""
        self.is_active = True
        await self.notification_service.send_strategy_notification(
            self.name, "started", "Strategy is now active"
        )
        logger.info(f"Strategy {self.name} started")
    
    async def stop(self):
        """Stop strategy execution"""
        self.is_active = False
        await self.notification_service.send_strategy_notification(
            self.name, "stopped", "Strategy has been stopped"
        )
        logger.info(f"Strategy {self.name} stopped")
    
    async def pause(self):
        """Pause strategy execution"""
        self.is_active = False
        await self.notification_service.send_strategy_notification(
            self.name, "paused", "Strategy execution paused"
        )
        logger.info(f"Strategy {self.name} paused")
    
    def check_risk_limits(self) -> bool:
        """Check if strategy is within risk limits"""
        # Check daily loss limit
        daily_loss_limit = self.risk_settings.get('daily_loss_limit', 5000)
        if self.pnl_today < -daily_loss_limit:
            logger.warning(f"Strategy {self.name} hit daily loss limit")
            return False
        
        # Check max drawdown
        max_drawdown_percent = self.risk_settings.get('max_drawdown_percent', 10)
        if self.peak_equity > 0:
            current_drawdown = ((self.peak_equity - self.pnl_today) / self.peak_equity) * 100
            if current_drawdown > max_drawdown_percent:
                logger.warning(f"Strategy {self.name} hit max drawdown limit")
                return False
        
        # Check trade count limit
        max_trades_per_day = self.risk_settings.get('max_trades_per_day', 20)
        if self.trades_today >= max_trades_per_day:
            logger.warning(f"Strategy {self.name} hit daily trade limit")
            return False
        
        return True
    
    async def create_order(self, symbol: str, side: str, quantity: float, price: Optional[float] = None, order_type: str = "limit_order") -> Optional[Dict]:
        """Create order through order manager"""
        if not self.check_risk_limits():
            await self.notification_service.send_risk_alert(
                "risk_limit_exceeded", 
                f"Strategy {self.name} exceeded risk limits"
            )
            return None
        
        try:
            order_request = OrderRequest(
                symbol=symbol,
                side=OrderSideEnum(side),
                order_type=OrderTypeEnum(order_type),
                quantity=quantity,
                price=price
            )
            
            result = await self.order_manager.create_order(order_request, strategy_id=self.name)
            if result:
                self.trades_today += 1
                logger.info(f"Strategy {self.name} created order: {side} {quantity} {symbol}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating order in strategy {self.name}: {e}")
            return None
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for symbol"""
        return self.market_data_service.get_market_data(symbol)
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker data for symbol"""
        return self.market_data_service.get_ticker(symbol)
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on risk parameters"""
        max_position_value = self.risk_settings.get('max_position_value', 10000)  # INR
        risk_per_trade = self.risk_settings.get('risk_per_trade_percent', 2)  # 2%
        
        # Simple position sizing based on max position value
        max_quantity = max_position_value / price
        
        # Apply risk per trade limit
        account_balance = 100000  # This should come from portfolio balance
        risk_amount = account_balance * (risk_per_trade / 100)
        risk_based_quantity = risk_amount / price
        
        return min(max_quantity, risk_based_quantity)


class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any], risk_settings: Dict[str, Any]):
        super().__init__("Momentum Strategy", symbols, parameters, risk_settings)
        
        # Strategy-specific parameters
        self.momentum_threshold = parameters.get('momentum_threshold', 3.0)  # 3% in 5 minutes
        self.stop_loss_percent = parameters.get('stop_loss_percent', 3.0)
        self.take_profit_percent = parameters.get('take_profit_percent', 2.0)
        self.lookback_minutes = parameters.get('lookback_minutes', 5)
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute momentum strategy"""
        signals = []
        
        if not self.is_active or not self.check_risk_limits():
            return signals
        
        try:
            for symbol in self.symbols:
                # Get price change over lookback period
                price_change = self.market_data_service.calculate_price_change(
                    symbol, self.lookback_minutes
                )
                
                if price_change is None:
                    continue
                
                ticker = self.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker['price']
                
                # Check if we have a position
                position = self.positions.get(symbol)
                
                if position:
                    # Manage existing position
                    entry_price = position['entry_price']
                    side = position['side']
                    quantity = position['quantity']
                    
                    if side == 'buy':
                        pnl_percent = ((current_price - entry_price) / entry_price) * 100
                        
                        # Check stop loss or take profit
                        if pnl_percent <= -self.stop_loss_percent:
                            # Stop loss
                            signal = {
                                'action': 'close_position',
                                'symbol': symbol,
                                'side': 'sell',
                                'quantity': quantity,
                                'price': current_price,
                                'reason': 'stop_loss',
                                'pnl_percent': pnl_percent
                            }
                            signals.append(signal)
                            
                        elif pnl_percent >= self.take_profit_percent:
                            # Take profit
                            signal = {
                                'action': 'close_position',
                                'symbol': symbol,
                                'side': 'sell',
                                'quantity': quantity,
                                'price': current_price,
                                'reason': 'take_profit',
                                'pnl_percent': pnl_percent
                            }
                            signals.append(signal)
                
                else:
                    # Look for entry signals
                    if price_change >= self.momentum_threshold:
                        # Strong upward momentum - buy signal
                        quantity = self.calculate_position_size(symbol, current_price)
                        
                        if quantity > 0:
                            signal = {
                                'action': 'open_position',
                                'symbol': symbol,
                                'side': 'buy',
                                'quantity': quantity,
                                'price': current_price,
                                'reason': 'momentum_breakout',
                                'momentum': price_change
                            }
                            signals.append(signal)
            
            # Execute signals
            for signal in signals:
                await self._execute_signal(signal)
            
            self.last_execution = datetime.now()
            return signals
            
        except Exception as e:
            logger.error(f"Error executing momentum strategy: {e}")
            await self.notification_service.send_strategy_notification(
                self.name, "error", f"Execution error: {str(e)}"
            )
            return []
    
    async def _execute_signal(self, signal: Dict[str, Any]):
        """Execute a trading signal"""
        try:
            symbol = signal['symbol']
            side = signal['side']
            quantity = signal['quantity']
            price = signal['price']
            action = signal['action']
            
            # Create order
            result = await self.create_order(symbol, side, quantity, price)
            
            if result:
                if action == 'open_position':
                    # Track new position
                    self.positions[symbol] = {
                        'side': side,
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': datetime.now(),
                        'order_id': result.exchange_order_id
                    }
                    
                elif action == 'close_position':
                    # Remove position
                    if symbol in self.positions:
                        del self.positions[symbol]
                
                # Send notification
                await self.notification_service.send_strategy_notification(
                    self.name,
                    action,
                    f"{side.upper()} {quantity} {symbol} at ₹{price:,.2f} - {signal['reason']}"
                )
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information"""
        return {
            "name": self.name,
            "type": "momentum",
            "parameters": {
                "momentum_threshold": self.momentum_threshold,
                "stop_loss_percent": self.stop_loss_percent,
                "take_profit_percent": self.take_profit_percent,
                "lookback_minutes": self.lookback_minutes
            },
            "symbols": self.symbols,
            "is_active": self.is_active,
            "positions": self.positions,
            "trades_today": self.trades_today,
            "pnl_today": self.pnl_today,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None
        }


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any], risk_settings: Dict[str, Any]):
        super().__init__("Mean Reversion Strategy", symbols, parameters, risk_settings)
        
        # Strategy-specific parameters
        self.oversold_threshold = parameters.get('oversold_threshold', -5.0)  # -5% in 15 minutes
        self.overbought_threshold = parameters.get('overbought_threshold', 5.0)  # 5% in 15 minutes
        self.stop_loss_percent = parameters.get('stop_loss_percent', 2.0)
        self.take_profit_percent = parameters.get('take_profit_percent', 1.5)
        self.lookback_minutes = parameters.get('lookback_minutes', 15)
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute mean reversion strategy"""
        signals = []
        
        if not self.is_active or not self.check_risk_limits():
            return signals
        
        try:
            for symbol in self.symbols:
                # Get price change over lookback period
                price_change = self.market_data_service.calculate_price_change(
                    symbol, self.lookback_minutes
                )
                
                if price_change is None:
                    continue
                
                ticker = self.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker['price']
                
                # Check if we have a position
                position = self.positions.get(symbol)
                
                if position:
                    # Manage existing position
                    entry_price = position['entry_price']
                    side = position['side']
                    quantity = position['quantity']
                    
                    if side == 'buy':
                        pnl_percent = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl_percent = ((entry_price - current_price) / entry_price) * 100
                    
                    # Check stop loss or take profit
                    if pnl_percent <= -self.stop_loss_percent:
                        # Stop loss
                        close_side = 'sell' if side == 'buy' else 'buy'
                        signal = {
                            'action': 'close_position',
                            'symbol': symbol,
                            'side': close_side,
                            'quantity': quantity,
                            'price': current_price,
                            'reason': 'stop_loss',
                            'pnl_percent': pnl_percent
                        }
                        signals.append(signal)
                        
                    elif pnl_percent >= self.take_profit_percent:
                        # Take profit
                        close_side = 'sell' if side == 'buy' else 'buy'
                        signal = {
                            'action': 'close_position',
                            'symbol': symbol,
                            'side': close_side,
                            'quantity': quantity,
                            'price': current_price,
                            'reason': 'take_profit',
                            'pnl_percent': pnl_percent
                        }
                        signals.append(signal)
                
                else:
                    # Look for entry signals
                    if price_change <= self.oversold_threshold:
                        # Oversold - buy signal (expecting reversion up)
                        quantity = self.calculate_position_size(symbol, current_price)
                        
                        if quantity > 0:
                            signal = {
                                'action': 'open_position',
                                'symbol': symbol,
                                'side': 'buy',
                                'quantity': quantity,
                                'price': current_price,
                                'reason': 'oversold_reversion',
                                'price_change': price_change
                            }
                            signals.append(signal)
                    
                    elif price_change >= self.overbought_threshold:
                        # Overbought - sell signal (expecting reversion down)
                        # Note: This would be for short selling, which may not be available
                        # For now, we'll skip this or implement as a different logic
                        pass
            
            # Execute signals
            for signal in signals:
                await self._execute_signal(signal)
            
            self.last_execution = datetime.now()
            return signals
            
        except Exception as e:
            logger.error(f"Error executing mean reversion strategy: {e}")
            await self.notification_service.send_strategy_notification(
                self.name, "error", f"Execution error: {str(e)}"
            )
            return []
    
    async def _execute_signal(self, signal: Dict[str, Any]):
        """Execute a trading signal"""
        try:
            symbol = signal['symbol']
            side = signal['side']
            quantity = signal['quantity']
            price = signal['price']
            action = signal['action']
            
            # Create order
            result = await self.create_order(symbol, side, quantity, price)
            
            if result:
                if action == 'open_position':
                    # Track new position
                    self.positions[symbol] = {
                        'side': side,
                        'quantity': quantity,
                        'entry_price': price,
                        'entry_time': datetime.now(),
                        'order_id': result.exchange_order_id
                    }
                    
                elif action == 'close_position':
                    # Remove position
                    if symbol in self.positions:
                        del self.positions[symbol]
                
                # Send notification
                await self.notification_service.send_strategy_notification(
                    self.name,
                    action,
                    f"{side.upper()} {quantity} {symbol} at ₹{price:,.2f} - {signal['reason']}"
                )
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information"""
        return {
            "name": self.name,
            "type": "mean_reversion",
            "parameters": {
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
                "stop_loss_percent": self.stop_loss_percent,
                "take_profit_percent": self.take_profit_percent,
                "lookback_minutes": self.lookback_minutes
            },
            "symbols": self.symbols,
            "is_active": self.is_active,
            "positions": self.positions,
            "trades_today": self.trades_today,
            "pnl_today": self.pnl_today,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None
        }
