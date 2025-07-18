import time
import hmac
import hashlib
import json
import requests
from typing import Optional, Dict, List, Any
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class CoinDCXClient:
    """Enhanced CoinDCX API client with error handling and rate limiting"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.COINDCX_API_KEY
        self.secret_key = secret_key or settings.COINDCX_SECRET_KEY
        self.secret_bytes = bytes(self.secret_key, encoding='utf-8')
        
        self.public_host = settings.COINDCX_PUBLIC_URL
        self.api_host = settings.COINDCX_BASE_URL
        self.exchange_base = f"{self.api_host}/exchange/v1"
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Session for connection pooling
        self.session = requests.Session()
        
    def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()
    
    def _generate_signature(self, json_body: str) -> str:
        """Generate HMAC signature for authenticated requests"""
        return hmac.new(
            self.secret_bytes, 
            json_body.encode(), 
            hashlib.sha256
        ).hexdigest()
    
    def _generate_headers(self, json_body: str) -> Dict[str, str]:
        """Generate headers for authenticated requests"""
        signature = self._generate_signature(json_body)
        return {
            'Content-Type': 'application/json',
            'X-AUTH-APIKEY': self.api_key,
            'X-AUTH-SIGNATURE': signature
        }
    
    def _send_get_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send GET request with error handling"""
        self._rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"GET request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            return None
    
    def _send_post_request(self, url: str, data: str, headers: Dict[str, str]) -> Optional[Dict]:
        """Send POST request with error handling"""
        self._rate_limit()
        try:
            response = self.session.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"POST request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            return None
    
    # Market Data Methods
    def get_ticker(self, symbol: Optional[str] = None) -> Optional[Dict]:
        """Get ticker data for one or all symbols"""
        url = f"{self.public_host}/exchange/ticker"
        return self._send_get_request(url)
    
    def get_market_details(self) -> Optional[List[Dict]]:
        """Get all available market details"""
        url = f"{self.exchange_base}/markets_details"
        return self._send_get_request(url)
    
    def get_candles(self, pair: str, interval: str, start_time: str = "", end_time: str = "") -> Optional[List[Dict]]:
        """Get candlestick data"""
        if start_time and not start_time.isdigit():
            start_time = str(int(start_time) * 1000)
        if end_time and not end_time.isdigit():
            end_time = str(int(end_time) * 1000)
            
        url = f"{self.public_host}/market_data/candles"
        params = {
            "pair": pair,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time
        }
        return self._send_get_request(url, params)
    
    def get_order_book(self, pair: str) -> Optional[Dict]:
        """Get order book for a trading pair"""
        url = f"{self.public_host}/exchange/orderbook"
        params = {"pair": pair}
        return self._send_get_request(url, params)
    
    def get_trades(self, pair: str) -> Optional[List[Dict]]:
        """Get recent trades for a trading pair"""
        url = f"{self.public_host}/exchange/trades"
        params = {"pair": pair}
        return self._send_get_request(url, params)
    
    # Account Methods
    def get_user_balance(self, currency: Optional[str] = None) -> Optional[Dict]:
        """Get user balance for one or all currencies"""
        timestamp = int(round(time.time() * 1000))
        body = {"timestamp": timestamp}
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/users/balances"
        
        data = self._send_post_request(url, json_body, headers)
        if not data:
            return {"balance": "0", "locked_balance": "0"} if currency else []
        
        if currency is None:
            return data
        
        # Return specific currency balance
        for item in data:
            if item.get('currency') == currency:
                return item
        
        return {"balance": "0", "locked_balance": "0"}
    
    def get_user_info(self) -> Optional[Dict]:
        """Get user account information"""
        timestamp = int(round(time.time() * 1000))
        body = {"timestamp": timestamp}
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/users/info"
        
        return self._send_post_request(url, json_body, headers)
    
    # Order Methods
    def create_order(self, side: str, order_type: str, market: str, 
                    price_per_unit: float, total_quantity: float) -> Optional[Dict]:
        """Create a new order"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "side": side,
            "order_type": order_type,
            "market": market,
            "price_per_unit": price_per_unit,
            "total_quantity": total_quantity,
            "timestamp": timestamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/create"
        
        return self._send_post_request(url, json_body, headers)
    
    def get_active_orders(self, market: Optional[str] = None) -> Optional[List[Dict]]:
        """Get active orders"""
        timestamp = int(round(time.time() * 1000))
        body = {"timestamp": timestamp}
        if market:
            body["market"] = market
            
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/active_orders"
        
        return self._send_post_request(url, json_body, headers)
    
    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """Cancel a specific order"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "id": order_id,
            "timestamp": timestamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/cancel"
        
        return self._send_post_request(url, json_body, headers)
    
    def cancel_all_orders(self, market: str, side: Optional[str] = None) -> Optional[Dict]:
        """Cancel all orders for a market"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "market": market,
            "timestamp": timestamp
        }
        if side:
            body["side"] = side
            
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/cancel_all"
        
        return self._send_post_request(url, json_body, headers)
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get order status"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "id": order_id,
            "timestamp": timestamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/status"
        
        return self._send_post_request(url, json_body, headers)
    
    def get_trade_history(self, limit: int = 500, market: Optional[str] = None) -> Optional[List[Dict]]:
        """Get trade history"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "timestamp": timestamp,
            "sort": "desc",
            "limit": limit
        }
        if market:
            body["market"] = market
            
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/orders/trade_history"
        
        return self._send_post_request(url, json_body, headers)
    
    # Margin Trading Methods
    def create_margin_order(self, side: str, market: str, price: float, quantity: float,
                          leverage: int, order_type: str = "limit_order", 
                          target_price: Optional[float] = None, ecode: str = "I") -> Optional[Dict]:
        """Create margin order"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "side": side,
            "order_type": order_type,
            "market": market,
            "price": price,
            "quantity": quantity,
            "ecode": ecode,
            "leverage": leverage,
            "timestamp": timestamp
        }
        if target_price:
            body["target_price"] = target_price
            
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/margin/create"
        
        return self._send_post_request(url, json_body, headers)
    
    def get_margin_positions(self) -> Optional[List[Dict]]:
        """Get active margin positions"""
        timestamp = int(round(time.time() * 1000))
        body = {"timestamp": timestamp}
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/margin/positions"
        
        return self._send_post_request(url, json_body, headers)
    
    def close_margin_position(self, position_id: str) -> Optional[Dict]:
        """Close margin position"""
        timestamp = int(round(time.time() * 1000))
        body = {
            "id": position_id,
            "timestamp": timestamp
        }
        json_body = json.dumps(body, separators=(',', ':'))
        headers = self._generate_headers(json_body)
        url = f"{self.exchange_base}/margin/exit"
        
        return self._send_post_request(url, json_body, headers)
    
    def __del__(self):
        """Cleanup session on object destruction"""
        if hasattr(self, 'session'):
            self.session.close()
