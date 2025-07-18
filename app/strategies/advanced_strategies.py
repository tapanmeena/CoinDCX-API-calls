"""
Advanced Trading Strategies
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from .base_strategy import BaseStrategy
from app.models.schemas import OrderRequest, OrderSideEnum, OrderTypeEnum

logger = logging.getLogger(__name__)

class RSIStrategy(BaseStrategy):
    """Relative Strength Index (RSI) Strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None, risk_settings: Dict[str, Any] = None):
        default_params = {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "min_price_change": 0.5,  # Minimum % price change to consider
        }
        default_risk = {
            "max_position_size": 10000,  # INR
            "stop_loss_percent": 3.0,
            "take_profit_percent": 6.0,
        }
        
        super().__init__(
            name="RSI Strategy",
            symbols=symbols,
            parameters={**default_params, **(parameters or {})},
            risk_settings={**default_risk, **(risk_settings or {})}
        )
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI for the given prices"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [delta if delta > 0 else 0 for delta in deltas]
        losses = [-delta if delta < 0 else 0 for delta in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute RSI strategy"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Get historical candle data
                candles = self.market_data_service.get_candles(symbol, "1m", 100)
                if not candles or len(candles) < self.parameters["rsi_period"] + 1:
                    continue
                
                prices = [float(candle.get('close', 0)) for candle in candles]
                current_price = prices[-1]
                
                # Calculate RSI
                rsi = self.calculate_rsi(prices, self.parameters["rsi_period"])
                
                # Check for signals
                position = self.positions.get(symbol, {})
                
                if not position:  # No current position
                    if rsi <= self.parameters["rsi_oversold"]:
                        # Buy signal
                        signals.append({
                            "symbol": symbol,
                            "action": "BUY",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"RSI oversold: {rsi:.2f}",
                            "rsi": rsi,
                            "timestamp": datetime.now()
                        })
                    elif rsi >= self.parameters["rsi_overbought"]:
                        # Sell signal (for short positions if allowed)
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL_SHORT",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"RSI overbought: {rsi:.2f}",
                            "rsi": rsi,
                            "timestamp": datetime.now()
                        })
                else:
                    # Check exit conditions
                    entry_price = position.get("entry_price", current_price)
                    side = position.get("side", "BUY")
                    
                    if side == "BUY":
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                        
                        if (rsi >= self.parameters["rsi_overbought"] or 
                            profit_pct >= self.risk_settings["take_profit_percent"] or
                            profit_pct <= -self.risk_settings["stop_loss_percent"]):
                            
                            signals.append({
                                "symbol": symbol,
                                "action": "SELL",
                                "price": current_price,
                                "quantity": position.get("quantity", 0),
                                "reason": f"Exit: RSI={rsi:.2f}, P&L={profit_pct:.2f}%",
                                "rsi": rsi,
                                "timestamp": datetime.now()
                            })
                
            except Exception as e:
                logger.error(f"Error executing RSI strategy for {symbol}: {e}")
        
        return signals


class BollingerBandsStrategy(BaseStrategy):
    """Bollinger Bands Strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None, risk_settings: Dict[str, Any] = None):
        default_params = {
            "bb_period": 20,
            "bb_std_dev": 2.0,
            "min_volume": 100000,  # Minimum 24h volume
        }
        default_risk = {
            "max_position_size": 15000,
            "stop_loss_percent": 2.5,
            "take_profit_percent": 5.0,
        }
        
        super().__init__(
            name="Bollinger Bands Strategy",
            symbols=symbols,
            parameters={**default_params, **(parameters or {})},
            risk_settings={**default_risk, **(risk_settings or {})}
        )
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            current_price = prices[-1] if prices else 0
            return current_price, current_price, current_price
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / len(recent_prices)
        
        variance = sum((price - sma) ** 2 for price in recent_prices) / len(recent_prices)
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute Bollinger Bands strategy"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Get ticker for volume check
                ticker = self.market_data_service.get_ticker(symbol)
                if not ticker or ticker.get("volume_24h", 0) < self.parameters["min_volume"]:
                    continue
                
                # Get historical data
                candles = self.market_data_service.get_candles(symbol, "5m", 50)
                if not candles or len(candles) < self.parameters["bb_period"]:
                    continue
                
                prices = [float(candle.get('close', 0)) for candle in candles]
                current_price = prices[-1]
                
                # Calculate Bollinger Bands
                upper_band, middle_band, lower_band = self.calculate_bollinger_bands(
                    prices, self.parameters["bb_period"], self.parameters["bb_std_dev"]
                )
                
                # Calculate position relative to bands
                bb_position = (current_price - lower_band) / (upper_band - lower_band)
                
                position = self.positions.get(symbol, {})
                
                if not position:
                    if current_price <= lower_band * 1.001:  # Price at or below lower band
                        signals.append({
                            "symbol": symbol,
                            "action": "BUY",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"Price below lower BB: {current_price:.2f} <= {lower_band:.2f}",
                            "bb_position": bb_position,
                            "timestamp": datetime.now()
                        })
                    elif current_price >= upper_band * 0.999:  # Price at or above upper band
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL_SHORT",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"Price above upper BB: {current_price:.2f} >= {upper_band:.2f}",
                            "bb_position": bb_position,
                            "timestamp": datetime.now()
                        })
                else:
                    # Exit conditions
                    entry_price = position.get("entry_price", current_price)
                    side = position.get("side", "BUY")
                    
                    if side == "BUY" and current_price >= middle_band:
                        # Exit long position when price reaches middle band
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL",
                            "price": current_price,
                            "quantity": position.get("quantity", 0),
                            "reason": f"Price reached middle band: {current_price:.2f}",
                            "bb_position": bb_position,
                            "timestamp": datetime.now()
                        })
                
            except Exception as e:
                logger.error(f"Error executing Bollinger Bands strategy for {symbol}: {e}")
        
        return signals


class MACDStrategy(BaseStrategy):
    """MACD (Moving Average Convergence Divergence) Strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None, risk_settings: Dict[str, Any] = None):
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9,
            "min_macd_strength": 0.1,  # Minimum MACD value for signal
        }
        default_risk = {
            "max_position_size": 12000,
            "stop_loss_percent": 3.5,
            "take_profit_percent": 7.0,
        }
        
        super().__init__(
            name="MACD Strategy",
            symbols=symbols,
            parameters={**default_params, **(parameters or {})},
            risk_settings={**default_risk, **(risk_settings or {})}
        )
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [prices[-1]] * len(prices) if prices else []
        
        multiplier = 2 / (period + 1)
        ema = [sum(prices[:period]) / period]  # First EMA is SMA
        
        for i in range(period, len(prices)):
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
        
        return ema
    
    def calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD, Signal, and Histogram"""
        fast_ema = self.calculate_ema(prices, self.parameters["fast_period"])
        slow_ema = self.calculate_ema(prices, self.parameters["slow_period"])
        
        if len(fast_ema) == 0 or len(slow_ema) == 0:
            return 0.0, 0.0, 0.0
        
        # MACD line
        macd_line = fast_ema[-1] - slow_ema[-1]
        
        # For signal line, we need more data points
        if len(prices) < self.parameters["slow_period"] + self.parameters["signal_period"]:
            return macd_line, 0.0, macd_line
        
        # Calculate MACD values for signal line
        macd_values = []
        for i in range(len(fast_ema)):
            if i < len(slow_ema):
                macd_values.append(fast_ema[i] - slow_ema[i])
        
        signal_ema = self.calculate_ema(macd_values, self.parameters["signal_period"])
        signal_line = signal_ema[-1] if signal_ema else 0.0
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute MACD strategy"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Get sufficient historical data
                candles = self.market_data_service.get_candles(symbol, "15m", 100)
                if not candles or len(candles) < self.parameters["slow_period"] + self.parameters["signal_period"]:
                    continue
                
                prices = [float(candle.get('close', 0)) for candle in candles]
                current_price = prices[-1]
                
                # Calculate MACD
                macd_line, signal_line, histogram = self.calculate_macd(prices)
                
                # Get previous MACD for crossover detection
                if len(prices) > 1:
                    prev_macd, prev_signal, prev_histogram = self.calculate_macd(prices[:-1])
                else:
                    prev_macd = prev_signal = prev_histogram = 0
                
                position = self.positions.get(symbol, {})
                
                if not position:
                    # MACD bullish crossover (MACD crosses above signal)
                    if (macd_line > signal_line and prev_macd <= prev_signal and 
                        abs(macd_line) > self.parameters["min_macd_strength"]):
                        
                        signals.append({
                            "symbol": symbol,
                            "action": "BUY",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"MACD bullish crossover: {macd_line:.4f} > {signal_line:.4f}",
                            "macd": macd_line,
                            "signal": signal_line,
                            "histogram": histogram,
                            "timestamp": datetime.now()
                        })
                    
                    # MACD bearish crossover (MACD crosses below signal)
                    elif (macd_line < signal_line and prev_macd >= prev_signal and 
                          abs(macd_line) > self.parameters["min_macd_strength"]):
                        
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL_SHORT",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"MACD bearish crossover: {macd_line:.4f} < {signal_line:.4f}",
                            "macd": macd_line,
                            "signal": signal_line,
                            "histogram": histogram,
                            "timestamp": datetime.now()
                        })
                else:
                    # Exit conditions
                    side = position.get("side", "BUY")
                    entry_price = position.get("entry_price", current_price)
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    should_exit = False
                    exit_reason = ""
                    
                    if side == "BUY":
                        if macd_line < signal_line and prev_macd >= prev_signal:
                            should_exit = True
                            exit_reason = "MACD bearish crossover"
                        elif profit_pct >= self.risk_settings["take_profit_percent"]:
                            should_exit = True
                            exit_reason = f"Take profit: {profit_pct:.2f}%"
                        elif profit_pct <= -self.risk_settings["stop_loss_percent"]:
                            should_exit = True
                            exit_reason = f"Stop loss: {profit_pct:.2f}%"
                    
                    if should_exit:
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL",
                            "price": current_price,
                            "quantity": position.get("quantity", 0),
                            "reason": exit_reason,
                            "macd": macd_line,
                            "signal": signal_line,
                            "histogram": histogram,
                            "timestamp": datetime.now()
                        })
                
            except Exception as e:
                logger.error(f"Error executing MACD strategy for {symbol}: {e}")
        
        return signals


class VolumeBreakoutStrategy(BaseStrategy):
    """Volume Breakout Strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None, risk_settings: Dict[str, Any] = None):
        default_params = {
            "volume_threshold": 2.0,  # Volume must be 2x average
            "price_breakout_percent": 1.5,  # Price must break 1.5% above resistance
            "lookback_period": 20,
            "min_price": 10.0,  # Minimum price to consider
        }
        default_risk = {
            "max_position_size": 8000,
            "stop_loss_percent": 4.0,
            "take_profit_percent": 8.0,
        }
        
        super().__init__(
            name="Volume Breakout Strategy",
            symbols=symbols,
            parameters={**default_params, **(parameters or {})},
            risk_settings={**default_risk, **(risk_settings or {})}
        )
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute Volume Breakout strategy"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Get current ticker
                ticker = self.market_data_service.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker.get("price", 0)
                current_volume = ticker.get("volume_24h", 0)
                
                if current_price < self.parameters["min_price"]:
                    continue
                
                # Get historical candles
                candles = self.market_data_service.get_candles(symbol, "1h", self.parameters["lookback_period"] + 5)
                if not candles or len(candles) < self.parameters["lookback_period"]:
                    continue
                
                # Calculate average volume and resistance level
                volumes = [float(candle.get('volume', 0)) for candle in candles[:-1]]  # Exclude current period
                avg_volume = sum(volumes) / len(volumes) if volumes else 0
                
                highs = [float(candle.get('high', 0)) for candle in candles[:-1]]
                resistance_level = max(highs) if highs else current_price
                
                # Check for volume and price breakout
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                price_breakout_pct = ((current_price - resistance_level) / resistance_level) * 100
                
                position = self.positions.get(symbol, {})
                
                if not position:
                    if (volume_ratio >= self.parameters["volume_threshold"] and 
                        price_breakout_pct >= self.parameters["price_breakout_percent"]):
                        
                        signals.append({
                            "symbol": symbol,
                            "action": "BUY",
                            "price": current_price,
                            "quantity": self.risk_settings["max_position_size"] / current_price,
                            "reason": f"Volume breakout: {volume_ratio:.2f}x volume, {price_breakout_pct:.2f}% price breakout",
                            "volume_ratio": volume_ratio,
                            "price_breakout": price_breakout_pct,
                            "resistance_level": resistance_level,
                            "timestamp": datetime.now()
                        })
                else:
                    # Exit conditions
                    entry_price = position.get("entry_price", current_price)
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    
                    if (profit_pct >= self.risk_settings["take_profit_percent"] or
                        profit_pct <= -self.risk_settings["stop_loss_percent"] or
                        volume_ratio < 1.0):  # Volume dies down
                        
                        signals.append({
                            "symbol": symbol,
                            "action": "SELL",
                            "price": current_price,
                            "quantity": position.get("quantity", 0),
                            "reason": f"Exit: P&L={profit_pct:.2f}%, Volume ratio={volume_ratio:.2f}",
                            "volume_ratio": volume_ratio,
                            "timestamp": datetime.now()
                        })
                
            except Exception as e:
                logger.error(f"Error executing Volume Breakout strategy for {symbol}: {e}")
        
        return signals


class GridTradingStrategy(BaseStrategy):
    """Grid Trading Strategy"""
    
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None, risk_settings: Dict[str, Any] = None):
        default_params = {
            "grid_levels": 10,
            "grid_spacing_percent": 2.0,  # 2% between grid levels
            "base_order_size": 1000,  # INR per grid level
            "max_grid_range_percent": 20.0,  # Maximum 20% range for grid
        }
        default_risk = {
            "max_position_size": 50000,  # Total across all grid levels
            "stop_loss_percent": 15.0,  # Wide stop for grid strategy
        }
        
        super().__init__(
            name="Grid Trading Strategy",
            symbols=symbols,
            parameters={**default_params, **(parameters or {})},
            risk_settings={**default_risk, **(risk_settings or {})}
        )
    
    async def execute(self) -> List[Dict[str, Any]]:
        """Execute Grid Trading strategy"""
        signals = []
        
        for symbol in self.symbols:
            try:
                ticker = self.market_data_service.get_ticker(symbol)
                if not ticker:
                    continue
                
                current_price = ticker.get("price", 0)
                if current_price <= 0:
                    continue
                
                # Initialize grid if not exists
                if symbol not in self.positions:
                    self.positions[symbol] = {
                        "grid_center": current_price,
                        "grid_levels": {},
                        "total_invested": 0
                    }
                
                position = self.positions[symbol]
                grid_center = position["grid_center"]
                grid_spacing = grid_center * (self.parameters["grid_spacing_percent"] / 100)
                
                # Calculate grid levels
                for i in range(-self.parameters["grid_levels"]//2, self.parameters["grid_levels"]//2 + 1):
                    if i == 0:
                        continue  # Skip center level
                    
                    grid_price = grid_center + (i * grid_spacing)
                    grid_key = f"level_{i}"
                    
                    if grid_key not in position["grid_levels"]:
                        # Place grid order
                        if i < 0:  # Buy levels (below center)
                            if current_price <= grid_price * 1.001:  # Price reached buy level
                                signals.append({
                                    "symbol": symbol,
                                    "action": "BUY",
                                    "price": grid_price,
                                    "quantity": self.parameters["base_order_size"] / grid_price,
                                    "reason": f"Grid buy level {i}: {grid_price:.2f}",
                                    "grid_level": i,
                                    "grid_price": grid_price,
                                    "timestamp": datetime.now()
                                })
                                
                                position["grid_levels"][grid_key] = {
                                    "price": grid_price,
                                    "quantity": self.parameters["base_order_size"] / grid_price,
                                    "side": "BUY"
                                }
                        
                        else:  # Sell levels (above center)
                            if current_price >= grid_price * 0.999:  # Price reached sell level
                                # Only sell if we have inventory
                                total_quantity = sum(
                                    level.get("quantity", 0) 
                                    for level in position["grid_levels"].values() 
                                    if level.get("side") == "BUY"
                                )
                                
                                if total_quantity > 0:
                                    sell_quantity = min(
                                        self.parameters["base_order_size"] / grid_price,
                                        total_quantity
                                    )
                                    
                                    signals.append({
                                        "symbol": symbol,
                                        "action": "SELL",
                                        "price": grid_price,
                                        "quantity": sell_quantity,
                                        "reason": f"Grid sell level {i}: {grid_price:.2f}",
                                        "grid_level": i,
                                        "grid_price": grid_price,
                                        "timestamp": datetime.now()
                                    })
                
            except Exception as e:
                logger.error(f"Error executing Grid Trading strategy for {symbol}: {e}")
        
        return signals
