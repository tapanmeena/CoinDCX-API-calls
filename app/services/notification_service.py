import asyncio
import logging
from typing import Optional, Dict, Any
import requests
import json
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications via Telegram and other channels"""
    
    def __init__(self):
        self.settings = get_settings()
        self.telegram_bot_token = self.settings.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = self.settings.TELEGRAM_CHAT_ID
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_bot_token}"
        
        # Session for connection pooling
        self.session = requests.Session()
    
    async def send_telegram_message(self, message: str) -> bool:
        """Send message via Telegram"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("Telegram credentials not configured")
            return False
        
        try:
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.session.post(url, data=data, timeout=10)
            )
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def send_order_notification(self, message: str):
        """Send order-related notification"""
        formatted_message = f"🔔 <b>Order Update</b>\n{message}"
        await self.send_telegram_message(formatted_message)
    
    async def send_trade_notification(self, trade_data: Dict[str, Any]):
        """Send trade execution notification"""
        side_emoji = "🟢" if trade_data.get('side') == 'buy' else "🔴"
        message = f"""
{side_emoji} <b>Trade Executed</b>

<b>Symbol:</b> {trade_data.get('symbol')}
<b>Side:</b> {trade_data.get('side', '').upper()}
<b>Quantity:</b> {trade_data.get('quantity')} 
<b>Price:</b> ₹{trade_data.get('price'):,.2f}
<b>Value:</b> ₹{trade_data.get('quantity', 0) * trade_data.get('price', 0):,.2f}
<b>Fees:</b> ₹{trade_data.get('fees', 0):.2f}
<b>Strategy:</b> {trade_data.get('strategy_id', 'Manual')}
        """
        await self.send_telegram_message(message.strip())
    
    async def send_strategy_notification(self, strategy_name: str, action: str, details: str = ""):
        """Send strategy-related notification"""
        emoji_map = {
            "started": "▶️",
            "stopped": "⏹️",
            "paused": "⏸️",
            "error": "❌",
            "profit": "💰",
            "loss": "📉"
        }
        
        emoji = emoji_map.get(action, "ℹ️")
        message = f"""
{emoji} <b>Strategy Update</b>

<b>Strategy:</b> {strategy_name}
<b>Action:</b> {action.upper()}
{f"<b>Details:</b> {details}" if details else ""}
        """
        await self.send_telegram_message(message.strip())
    
    async def send_pnl_notification(self, pnl_data: Dict[str, Any]):
        """Send P&L update notification"""
        total_pnl = pnl_data.get('total_pnl', 0)
        emoji = "💰" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"
        
        message = f"""
{emoji} <b>P&L Update</b>

<b>Strategy:</b> {pnl_data.get('strategy_id', 'Overall')}
<b>Symbol:</b> {pnl_data.get('symbol', 'All')}
<b>Realized P&L:</b> ₹{pnl_data.get('realized_pnl', 0):,.2f}
<b>Unrealized P&L:</b> ₹{pnl_data.get('unrealized_pnl', 0):,.2f}
<b>Total P&L:</b> ₹{total_pnl:,.2f}
<b>Trade Count:</b> {pnl_data.get('trade_count', 0)}
<b>Win Rate:</b> {pnl_data.get('win_rate', 0):.1f}%
        """
        await self.send_telegram_message(message.strip())
    
    async def send_risk_alert(self, alert_type: str, message: str):
        """Send risk management alert"""
        emoji_map = {
            "stop_loss": "🛑",
            "daily_loss_limit": "⚠️",
            "max_drawdown": "📉",
            "margin_call": "🚨",
            "high_volatility": "⚡"
        }
        
        emoji = emoji_map.get(alert_type, "⚠️")
        formatted_message = f"""
{emoji} <b>RISK ALERT</b>

<b>Type:</b> {alert_type.replace('_', ' ').title()}
<b>Alert:</b> {message}
        """
        await self.send_telegram_message(formatted_message.strip())
    
    async def send_market_alert(self, symbol: str, alert_type: str, current_price: float, details: str = ""):
        """Send market-related alert"""
        emoji_map = {
            "price_spike": "🚀",
            "price_drop": "📉",
            "volume_spike": "📊",
            "breakout": "💥",
            "support": "🔴",
            "resistance": "🟢"
        }
        
        emoji = emoji_map.get(alert_type, "📈")
        message = f"""
{emoji} <b>Market Alert</b>

<b>Symbol:</b> {symbol}
<b>Alert Type:</b> {alert_type.replace('_', ' ').title()}
<b>Current Price:</b> ₹{current_price:,.2f}
{f"<b>Details:</b> {details}" if details else ""}
        """
        await self.send_telegram_message(message.strip())
    
    async def send_error_notification(self, error_message: str, context: str = ""):
        """Send error notification"""
        message = f"""
❌ <b>Error Alert</b>

<b>Error:</b> {error_message}
{f"<b>Context:</b> {context}" if context else ""}
        """
        await self.send_telegram_message(message.strip())
    
    async def send_daily_summary(self, summary_data: Dict[str, Any]):
        """Send daily trading summary"""
        total_pnl = summary_data.get('total_pnl', 0)
        emoji = "💰" if total_pnl > 0 else "📉" if total_pnl < 0 else "➖"
        
        message = f"""
{emoji} <b>Daily Trading Summary</b>

<b>Date:</b> {summary_data.get('date', '')}
<b>Total Trades:</b> {summary_data.get('total_trades', 0)}
<b>Winning Trades:</b> {summary_data.get('winning_trades', 0)}
<b>Losing Trades:</b> {summary_data.get('losing_trades', 0)}
<b>Win Rate:</b> {summary_data.get('win_rate', 0):.1f}%
<b>Total P&L:</b> ₹{total_pnl:,.2f}
<b>Best Trade:</b> ₹{summary_data.get('best_trade', 0):,.2f}
<b>Worst Trade:</b> ₹{summary_data.get('worst_trade', 0):,.2f}
<b>Active Strategies:</b> {summary_data.get('active_strategies', 0)}
        """
        await self.send_telegram_message(message.strip())
    
    async def send_startup_notification(self):
        """Send application startup notification"""
        message = """
🚀 <b>CoinDCX Algo Trading Bot Started</b>

The trading bot has been started successfully and is ready to execute strategies.
        """
        await self.send_telegram_message(message.strip())
    
    async def send_shutdown_notification(self):
        """Send application shutdown notification"""
        message = """
⏹️ <b>CoinDCX Algo Trading Bot Stopped</b>

The trading bot has been stopped gracefully.
        """
        await self.send_telegram_message(message.strip())
    
    def __del__(self):
        """Cleanup session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
