import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from app.services.coindcx_client import CoinDCXClient
from app.core.config import get_settings
from app.models.database import Trade, Portfolio, OrderSide, OrderType, OrderStatus
from app.models.schemas import OrderRequest, OrderResponse
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class OrderManager:
    """Service for managing orders and portfolio"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = CoinDCXClient()
        self.notification_service = NotificationService()
        self._active_orders: Dict[str, Dict] = {}
        self._order_callbacks: Dict[str, List] = {}
    
    async def create_order(self, 
                          order_request: OrderRequest, 
                          strategy_id: Optional[str] = None,
                          db: Optional[Session] = None) -> Optional[OrderResponse]:
        """Create a new order"""
        try:
            # Validate order parameters
            if not await self._validate_order(order_request):
                raise ValueError("Order validation failed")
            
            # Check if market order and set price
            if order_request.order_type == OrderType.MARKET:
                # Get current market price for market orders
                ticker = await self._get_current_price(order_request.symbol)
                if not ticker:
                    raise ValueError(f"Unable to get market price for {order_request.symbol}")
                order_request.price = ticker['price']
            
            # Check available balance
            if not await self._check_balance(order_request):
                raise ValueError("Insufficient balance")
            
            # Create order in database first
            trade = Trade(
                exchange_order_id=None,  # Will be updated after exchange response
                symbol=order_request.symbol,
                side=order_request.side,
                order_type=order_request.order_type,
                quantity=order_request.quantity,
                price=order_request.price,
                status=OrderStatus.PENDING,
                strategy_id=strategy_id
            )
            
            if db:
                db.add(trade)
                db.commit()
                db.refresh(trade)
            
            # Submit order to exchange
            exchange_response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.create_order,
                order_request.side.value,
                order_request.order_type.value,
                order_request.symbol,
                order_request.price,
                order_request.quantity
            )
            
            if not exchange_response or not exchange_response.get('orders'):
                # Update order status to failed
                if db and trade:
                    trade.status = OrderStatus.FAILED
                    db.commit()
                raise ValueError("Order creation failed on exchange")
            
            # Update trade with exchange order ID
            exchange_order = exchange_response['orders'][0]
            if db and trade:
                trade.exchange_order_id = exchange_order.get('id')
                trade.executed_quantity = float(exchange_order.get('total_quantity', 0))
                trade.executed_price = float(exchange_order.get('price_per_unit', 0))
                trade.status = OrderStatus.FILLED if exchange_order.get('status') == 'filled' else OrderStatus.PENDING
                trade.fees = float(exchange_order.get('fee_amount', 0))
                if trade.status == OrderStatus.FILLED:
                    trade.executed_at = datetime.now()
                db.commit()
                db.refresh(trade)
            
            # Add to active orders tracking
            self._active_orders[trade.exchange_order_id] = {
                "internal_id": trade.id,
                "exchange_id": trade.exchange_order_id,
                "symbol": order_request.symbol,
                "side": order_request.side,
                "status": trade.status,
                "created_at": trade.created_at
            }
            
            # Send notification
            await self.notification_service.send_order_notification(
                f"Order created: {order_request.side.value.upper()} {order_request.quantity} {order_request.symbol} at {order_request.price}"
            )
            
            # Return order response
            return OrderResponse(
                id=trade.id,
                exchange_order_id=trade.exchange_order_id,
                symbol=trade.symbol,
                side=trade.side,
                order_type=trade.order_type,
                quantity=trade.quantity,
                price=trade.price,
                executed_quantity=trade.executed_quantity,
                executed_price=trade.executed_price,
                status=trade.status,
                strategy_id=trade.strategy_id,
                fees=trade.fees,
                created_at=trade.created_at,
                updated_at=trade.updated_at,
                executed_at=trade.executed_at
            )
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            await self.notification_service.send_error_notification(f"Order creation failed: {str(e)}")
            return None
    
    async def cancel_order(self, order_id: str, db: Optional[Session] = None) -> bool:
        """Cancel an active order"""
        try:
            # Find order in database
            if db:
                trade = db.query(Trade).filter(
                    Trade.exchange_order_id == order_id,
                    Trade.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
                ).first()
                
                if not trade:
                    logger.error(f"Order {order_id} not found or not cancellable")
                    return False
            
            # Cancel on exchange
            cancel_response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.cancel_order,
                order_id
            )
            
            if not cancel_response:
                return False
            
            # Update order status
            if db and trade:
                trade.status = OrderStatus.CANCELLED
                trade.updated_at = datetime.now()
                db.commit()
            
            # Remove from active orders
            if order_id in self._active_orders:
                del self._active_orders[order_id]
            
            await self.notification_service.send_order_notification(f"Order {order_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get current order status from exchange"""
        try:
            status_response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_order_status,
                order_id
            )
            return status_response
        except Exception as e:
            logger.error(f"Error getting order status {order_id}: {e}")
            return None
    
    async def update_order_status(self, db: Session):
        """Update status of all active orders"""
        try:
            active_orders = db.query(Trade).filter(
                Trade.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED])
            ).all()
            
            for trade in active_orders:
                if not trade.exchange_order_id:
                    continue
                
                # Get status from exchange
                status = await self.get_order_status(trade.exchange_order_id)
                if not status:
                    continue
                
                # Update trade record
                old_status = trade.status
                if status.get('status') == 'filled':
                    trade.status = OrderStatus.FILLED
                    trade.executed_at = datetime.now()
                elif status.get('status') == 'cancelled':
                    trade.status = OrderStatus.CANCELLED
                elif status.get('status') == 'partially_filled':
                    trade.status = OrderStatus.PARTIALLY_FILLED
                
                # Update executed quantities and fees
                trade.executed_quantity = float(status.get('total_quantity', trade.executed_quantity))
                trade.executed_price = float(status.get('price_per_unit', trade.executed_price))
                trade.fees = float(status.get('fee_amount', trade.fees))
                trade.updated_at = datetime.now()
                
                # Notify if status changed
                if old_status != trade.status:
                    await self.notification_service.send_order_notification(
                        f"Order {trade.exchange_order_id} status changed: {old_status.value} -> {trade.status.value}"
                    )
                
                # Remove from active tracking if completed
                if trade.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                    if trade.exchange_order_id in self._active_orders:
                        del self._active_orders[trade.exchange_order_id]
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating order statuses: {e}")
    
    async def get_portfolio_balance(self, currency: Optional[str] = None) -> Dict:
        """Get current portfolio balance"""
        try:
            balance_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_user_balance,
                currency
            )
            
            if currency:
                return {
                    "currency": currency,
                    "balance": float(balance_data.get('balance', 0)),
                    "available_balance": float(balance_data.get('balance', 0)) - float(balance_data.get('locked_balance', 0)),
                    "locked_balance": float(balance_data.get('locked_balance', 0))
                }
            else:
                portfolio = {}
                for item in balance_data:
                    curr = item.get('currency')
                    if curr:
                        portfolio[curr] = {
                            "currency": curr,
                            "balance": float(item.get('balance', 0)),
                            "available_balance": float(item.get('balance', 0)) - float(item.get('locked_balance', 0)),
                            "locked_balance": float(item.get('locked_balance', 0))
                        }
                return portfolio
                
        except Exception as e:
            logger.error(f"Error getting portfolio balance: {e}")
            return {}
    
    async def _validate_order(self, order_request: OrderRequest) -> bool:
        """Validate order parameters"""
        try:
            # Check if symbol exists
            markets = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_market_details
            )
            
            valid_symbols = [m.get('coindcx_name') for m in markets if m.get('coindcx_name')]
            if order_request.symbol not in valid_symbols:
                logger.error(f"Invalid symbol: {order_request.symbol}")
                return False
            
            # Check minimum order size
            if order_request.quantity <= 0:
                logger.error("Order quantity must be positive")
                return False
            
            # Check price for limit orders
            if order_request.order_type == OrderType.LIMIT and (not order_request.price or order_request.price <= 0):
                logger.error("Price must be specified and positive for limit orders")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False
    
    async def _check_balance(self, order_request: OrderRequest) -> bool:
        """Check if sufficient balance is available"""
        try:
            if order_request.side == OrderSide.BUY:
                # Check INR balance for buy orders
                balance = await self.get_portfolio_balance("INR")
                required_amount = order_request.quantity * order_request.price
                if balance.get('available_balance', 0) < required_amount:
                    logger.error(f"Insufficient INR balance. Required: {required_amount}, Available: {balance.get('available_balance', 0)}")
                    return False
            else:
                # Check asset balance for sell orders
                asset_currency = order_request.symbol.replace('INR', '')
                balance = await self.get_portfolio_balance(asset_currency)
                if balance.get('available_balance', 0) < order_request.quantity:
                    logger.error(f"Insufficient {asset_currency} balance. Required: {order_request.quantity}, Available: {balance.get('available_balance', 0)}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking balance: {e}")
            return False
    
    async def _get_current_price(self, symbol: str) -> Optional[Dict]:
        """Get current market price for symbol"""
        try:
            ticker_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_ticker
            )
            
            if not ticker_data:
                return None
            
            for ticker in ticker_data:
                if ticker.get('market') == symbol:
                    return {
                        'price': float(ticker.get('last_price', 0)),
                        'bid': float(ticker.get('bid', 0)),
                        'ask': float(ticker.get('ask', 0))
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def add_order_callback(self, order_id: str, callback):
        """Add callback for order status updates"""
        if order_id not in self._order_callbacks:
            self._order_callbacks[order_id] = []
        self._order_callbacks[order_id].append(callback)
    
    async def _notify_order_callbacks(self, order_id: str, status_data: Dict):
        """Notify callbacks about order status changes"""
        if order_id in self._order_callbacks:
            for callback in self._order_callbacks[order_id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(status_data)
                    else:
                        callback(status_data)
                except Exception as e:
                    logger.error(f"Error in order callback: {e}")
    
    async def get_trade_history(self, 
                               symbol: Optional[str] = None, 
                               limit: int = 100,
                               db: Optional[Session] = None) -> List[Dict]:
        """Get trade history"""
        try:
            if db:
                query = db.query(Trade)
                if symbol:
                    query = query.filter(Trade.symbol == symbol)
                
                trades = query.order_by(Trade.created_at.desc()).limit(limit).all()
                
                return [
                    {
                        "id": trade.id,
                        "exchange_order_id": trade.exchange_order_id,
                        "symbol": trade.symbol,
                        "side": trade.side.value,
                        "order_type": trade.order_type.value,
                        "quantity": trade.quantity,
                        "price": trade.price,
                        "executed_quantity": trade.executed_quantity,
                        "executed_price": trade.executed_price,
                        "status": trade.status.value,
                        "strategy_id": trade.strategy_id,
                        "fees": trade.fees,
                        "created_at": trade.created_at.isoformat(),
                        "executed_at": trade.executed_at.isoformat() if trade.executed_at else None
                    }
                    for trade in trades
                ]
            
            # Fallback to exchange API
            exchange_history = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_trade_history,
                limit,
                symbol
            )
            
            return exchange_history or []
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
