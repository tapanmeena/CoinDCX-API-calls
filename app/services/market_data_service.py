import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
from app.services.coindcx_client import CoinDCXClient
from app.core.config import get_settings
from app.models.schemas import MarketDataResponse, TickerResponse

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service for managing real-time market data"""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = CoinDCXClient()
        self.is_running = False
        self._market_data_cache: Dict[str, Dict] = {}
        self._ticker_cache: Dict[str, Dict] = {}
        self._subscribers: Dict[str, List] = {}
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start market data service"""
        if self.is_running:
            return
        
        logger.info("Starting Market Data Service")
        self.is_running = True
        
        # Start background tasks
        self._tasks.append(
            asyncio.create_task(self._update_market_data_loop())
        )
        self._tasks.append(
            asyncio.create_task(self._update_ticker_loop())
        )
    
    async def stop(self):
        """Stop market data service"""
        if not self.is_running:
            return
        
        logger.info("Stopping Market Data Service")
        self.is_running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
    
    async def _update_market_data_loop(self):
        """Background loop to update market data"""
        while self.is_running:
            try:
                await self._update_market_data()
                await asyncio.sleep(self.settings.MARKET_DATA_REFRESH_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in market data update loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _update_ticker_loop(self):
        """Background loop to update ticker data"""
        while self.is_running:
            try:
                await self._update_ticker_data()
                await asyncio.sleep(1)  # Update ticker every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ticker update loop: {e}")
                await asyncio.sleep(5)
    
    async def _update_market_data(self):
        """Update market data for all symbols"""
        try:
            markets = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_market_details
            )
            
            if not markets:
                return
            
            # Update market data for INR pairs
            inr_markets = [m for m in markets if m.get('coindcx_name', '').endswith('INR')]
            
            for market in inr_markets[:20]:  # Limit to top 20 to avoid rate limits
                symbol = market.get('coindcx_name')
                if not symbol:
                    continue
                
                try:
                    # Get 1m candles for the last hour
                    end_time = int(datetime.now().timestamp())
                    start_time = end_time - 3600  # 1 hour ago
                    
                    candles = await asyncio.get_event_loop().run_in_executor(
                        None, 
                        self.client.get_candles,
                        market['pair'], 
                        "1m",
                        str(start_time),
                        str(end_time)
                    )
                    
                    if candles and len(candles) > 0:
                        latest_candle = candles[-1]
                        self._market_data_cache[symbol] = {
                            "symbol": symbol,
                            "open": float(latest_candle.get('open', 0)),
                            "high": float(latest_candle.get('high', 0)),
                            "low": float(latest_candle.get('low', 0)),
                            "close": float(latest_candle.get('close', 0)),
                            "volume": float(latest_candle.get('volume', 0)),
                            "timestamp": datetime.now(),
                            "candles": candles[-60:] if len(candles) >= 60 else candles  # Last 60 minutes
                        }
                        
                        # Notify subscribers
                        await self._notify_subscribers(symbol, "market_data", self._market_data_cache[symbol])
                
                except Exception as e:
                    logger.error(f"Error updating market data for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in market data update: {e}")
    
    async def _update_ticker_data(self):
        """Update ticker data"""
        try:
            ticker_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_ticker
            )
            
            if not ticker_data:
                return
            
            for ticker in ticker_data:
                symbol = ticker.get('market')
                if symbol:
                    current_price = float(ticker.get('last_price', 0))
                    change_24h = float(ticker.get('change_24_hour', 0))
                    
                    self._ticker_cache[symbol] = {
                        "symbol": symbol,
                        "price": current_price,
                        "change_24h": change_24h,
                        "change_percent_24h": (change_24h / (current_price - change_24h)) * 100 if current_price != change_24h else 0,
                        "high_24h": float(ticker.get('high', 0)),
                        "low_24h": float(ticker.get('low', 0)),
                        "volume_24h": float(ticker.get('volume', 0)),
                        "timestamp": datetime.now()
                    }
                    
                    # Notify subscribers
                    await self._notify_subscribers(symbol, "ticker", self._ticker_cache[symbol])
                    
        except Exception as e:
            logger.error(f"Error in ticker update: {e}")
    
    async def _notify_subscribers(self, symbol: str, data_type: str, data: Dict):
        """Notify subscribers of data updates"""
        key = f"{symbol}:{data_type}"
        if key in self._subscribers:
            for callback in self._subscribers[key]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                except Exception as e:
                    logger.error(f"Error notifying subscriber: {e}")
    
    def subscribe(self, symbol: str, data_type: str, callback):
        """Subscribe to market data updates"""
        key = f"{symbol}:{data_type}"
        if key not in self._subscribers:
            self._subscribers[key] = []
        self._subscribers[key].append(callback)
    
    def unsubscribe(self, symbol: str, data_type: str, callback):
        """Unsubscribe from market data updates"""
        key = f"{symbol}:{data_type}"
        if key in self._subscribers and callback in self._subscribers[key]:
            self._subscribers[key].remove(callback)
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker data for symbol"""
        return self._ticker_cache.get(symbol)
    
    def get_all_tickers(self) -> Dict[str, Dict]:
        """Get all ticker data"""
        return self._ticker_cache.copy()
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get market data for symbol"""
        return self._market_data_cache.get(symbol)
    
    def get_candles(self, symbol: str, interval: str = "1m", limit: int = 100) -> Optional[List[Dict]]:
        """Get cached candle data"""
        market_data = self._market_data_cache.get(symbol)
        if market_data and 'candles' in market_data:
            candles = market_data['candles']
            return candles[-limit:] if len(candles) > limit else candles
        return None
    
    async def get_historical_data(self, symbol: str, interval: str, start_time: str, end_time: str) -> Optional[List[Dict]]:
        """Get historical market data"""
        try:
            # Find the pair name for this symbol
            markets = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_market_details
            )
            
            pair = None
            for market in markets:
                if market.get('coindcx_name') == symbol:
                    pair = market.get('pair')
                    break
            
            if not pair:
                return None
            
            candles = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_candles,
                pair,
                interval,
                start_time,
                end_time
            )
            
            return candles
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def calculate_price_change(self, symbol: str, minutes: int = 5) -> Optional[float]:
        """Calculate price change percentage over specified minutes"""
        market_data = self._market_data_cache.get(symbol)
        if not market_data or 'candles' not in market_data:
            return None
        
        candles = market_data['candles']
        if len(candles) < minutes:
            return None
        
        current_price = float(candles[-1].get('close', 0))
        past_price = float(candles[-minutes].get('close', 0))
        
        if past_price == 0:
            return None
        
        return ((current_price - past_price) / past_price) * 100
    
    def get_market_summary(self) -> Dict[str, Any]:
        """Get market summary statistics"""
        total_markets = len(self._ticker_cache)
        gainers = []
        losers = []
        
        for symbol, ticker in self._ticker_cache.items():
            change_percent = ticker.get('change_percent_24h', 0)
            if change_percent > 0:
                gainers.append({"symbol": symbol, "change": change_percent})
            elif change_percent < 0:
                losers.append({"symbol": symbol, "change": change_percent})
        
        # Sort by change percentage
        gainers.sort(key=lambda x: x['change'], reverse=True)
        losers.sort(key=lambda x: x['change'])
        
        return {
            "total_markets": total_markets,
            "top_gainers": gainers[:10],
            "top_losers": losers[:10],
            "updated_at": datetime.now()
        }
