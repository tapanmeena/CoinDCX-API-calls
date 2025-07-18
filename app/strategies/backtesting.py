"""
Comprehensive Backtesting Framework for Trading Strategies
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.services.coindcx_client import CoinDCXClient
from app.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Individual trade record"""
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    side: str  # 'BUY' or 'SELL'
    pnl: float = 0.0
    pnl_percent: float = 0.0
    fees: float = 0.0
    strategy_signal: Dict[str, Any] = None
    is_open: bool = True

@dataclass
class BacktestResults:
    """Backtest results container"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    
    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Returns
    total_return: float = 0.0
    total_return_percent: float = 0.0
    annualized_return: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Trade analysis
    avg_trade_return: float = 0.0
    avg_winning_trade: float = 0.0
    avg_losing_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Timing
    avg_trade_duration: timedelta = timedelta()
    total_fees: float = 0.0
    
    # Data
    trades: List[Trade] = None
    equity_curve: List[float] = None
    daily_returns: List[float] = None


class HistoricalDataManager:
    """Manages historical market data for backtesting"""
    
    def __init__(self):
        self.client = CoinDCXClient()
        self.data_cache = {}
    
    async def get_historical_data(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical OHLCV data"""
        cache_key = f"{symbol}_{interval}_{start_date.date()}_{end_date.date()}"
        
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        try:
            # Convert dates to timestamps
            start_timestamp = str(int(start_date.timestamp()))
            end_timestamp = str(int(end_date.timestamp()))
            
            # Find market pair for symbol
            markets = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_market_details
            )
            
            pair = None
            for market in markets:
                if market.get('coindcx_name') == symbol:
                    pair = market.get('pair')
                    break
            
            if not pair:
                logger.error(f"No market pair found for symbol: {symbol}")
                return pd.DataFrame()
            
            # Get candle data
            candles = await asyncio.get_event_loop().run_in_executor(
                None,
                self.client.get_candles,
                pair,
                interval,
                start_timestamp,
                end_timestamp
            )
            
            if not candles:
                logger.warning(f"No candle data received for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(candles)
            
            # Standardize column names and types
            df['timestamp'] = pd.to_datetime(df['time'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            # Cache the data
            self.data_cache[cache_key] = df
            
            logger.info(f"Loaded {len(df)} candles for {symbol} from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return pd.DataFrame()


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000.0, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate  # 0.1% commission
        self.data_manager = HistoricalDataManager()
    
    async def run_backtest(self, 
                          strategy: BaseStrategy, 
                          symbol: str,
                          start_date: datetime,
                          end_date: datetime,
                          interval: str = "1h") -> BacktestResults:
        """Run backtest for a strategy on a symbol"""
        
        logger.info(f"Starting backtest for {strategy.name} on {symbol} from {start_date} to {end_date}")
        
        # Get historical data
        df = await self.data_manager.get_historical_data(symbol, interval, start_date, end_date)
        if df.empty:
            logger.error(f"No data available for backtesting {symbol}")
            return BacktestResults(strategy.name, symbol, start_date, end_date)
        
        # Initialize backtest state
        trades = []
        open_positions = {}
        equity_curve = [self.initial_capital]
        current_capital = self.initial_capital
        peak_equity = self.initial_capital
        max_drawdown = 0.0
        
        # Create a mock market data service for strategy
        mock_service = MockMarketDataService(df)
        strategy.market_data_service = mock_service
        
        # Iterate through historical data
        for i, (timestamp, row) in enumerate(df.iterrows()):
            try:
                # Update mock service with current data
                mock_service.update_current_data(i, timestamp, row)
                
                # Execute strategy
                signals = await strategy.execute()
                
                # Process signals
                for signal in signals:
                    trade = self._process_signal(signal, timestamp, row, open_positions)
                    if trade:
                        trades.append(trade)
                        
                        # Update capital
                        if not trade.is_open:
                            current_capital += trade.pnl - trade.fees
                
                # Calculate current equity (including unrealized P&L)
                current_equity = current_capital
                for pos in open_positions.values():
                    if pos.side == 'BUY':
                        unrealized_pnl = (row['close'] - pos.entry_price) * pos.quantity
                        current_equity += unrealized_pnl
                
                equity_curve.append(current_equity)
                
                # Update drawdown
                if current_equity > peak_equity:
                    peak_equity = current_equity
                else:
                    drawdown = (peak_equity - current_equity) / peak_equity
                    max_drawdown = max(max_drawdown, drawdown)
                
            except Exception as e:
                logger.error(f"Error processing timestamp {timestamp}: {e}")
                continue
        
        # Close any remaining open positions
        final_timestamp = df.index[-1]
        final_price = df.iloc[-1]['close']
        
        for symbol_key, position in list(open_positions.items()):
            exit_trade = Trade(
                symbol=position.symbol,
                entry_time=position.entry_time,
                exit_time=final_timestamp,
                entry_price=position.entry_price,
                exit_price=final_price,
                quantity=position.quantity,
                side=position.side,
                is_open=False
            )
            
            if position.side == 'BUY':
                exit_trade.pnl = (final_price - position.entry_price) * position.quantity
            else:
                exit_trade.pnl = (position.entry_price - final_price) * position.quantity
            
            exit_trade.pnl_percent = (exit_trade.pnl / (position.entry_price * position.quantity)) * 100
            exit_trade.fees = (exit_trade.exit_price * exit_trade.quantity * self.commission_rate)
            
            trades.append(exit_trade)
            current_capital += exit_trade.pnl - exit_trade.fees
            del open_positions[symbol_key]
        
        # Calculate final results
        results = self._calculate_results(strategy.name, symbol, start_date, end_date, trades, equity_curve)
        
        logger.info(f"Backtest completed for {strategy.name} on {symbol}")
        logger.info(f"Total trades: {results.total_trades}, Win rate: {results.win_rate:.2%}")
        logger.info(f"Total return: {results.total_return_percent:.2%}, Max drawdown: {results.max_drawdown_percent:.2%}")
        
        return results
    
    def _process_signal(self, signal: Dict[str, Any], timestamp: datetime, row: pd.Series, open_positions: Dict) -> Optional[Trade]:
        """Process a trading signal"""
        symbol = signal.get('symbol')
        action = signal.get('action')
        price = signal.get('price', row['close'])
        quantity = signal.get('quantity', 0)
        
        if not symbol or not action or quantity <= 0:
            return None
        
        # Generate position key
        position_key = f"{symbol}_{action}"
        
        if action in ['BUY', 'SELL_SHORT']:
            # Opening a new position
            if position_key in open_positions:
                return None  # Position already open
            
            trade = Trade(
                symbol=symbol,
                entry_time=timestamp,
                entry_price=price,
                quantity=quantity,
                side=action,
                strategy_signal=signal,
                fees=price * quantity * self.commission_rate
            )
            
            open_positions[position_key] = trade
            return trade
        
        elif action in ['SELL', 'COVER']:
            # Closing a position
            buy_key = f"{symbol}_BUY"
            short_key = f"{symbol}_SELL_SHORT"
            
            position = None
            if buy_key in open_positions:
                position = open_positions[buy_key]
                del open_positions[buy_key]
            elif short_key in open_positions:
                position = open_positions[short_key]
                del open_positions[short_key]
            
            if not position:
                return None  # No position to close
            
            # Calculate P&L
            if position.side == 'BUY':
                pnl = (price - position.entry_price) * position.quantity
            else:  # SHORT
                pnl = (position.entry_price - price) * position.quantity
            
            # Update position
            position.exit_time = timestamp
            position.exit_price = price
            position.pnl = pnl
            position.pnl_percent = (pnl / (position.entry_price * position.quantity)) * 100
            position.fees += price * position.quantity * self.commission_rate
            position.is_open = False
            
            return position
        
        return None
    
    def _calculate_results(self, strategy_name: str, symbol: str, start_date: datetime, 
                          end_date: datetime, trades: List[Trade], equity_curve: List[float]) -> BacktestResults:
        """Calculate comprehensive backtest results"""
        
        results = BacktestResults(strategy_name, symbol, start_date, end_date)
        results.trades = trades
        results.equity_curve = equity_curve
        
        if not trades:
            return results
        
        # Filter closed trades for analysis
        closed_trades = [t for t in trades if not t.is_open]
        
        if not closed_trades:
            return results
        
        # Basic trade statistics
        results.total_trades = len(closed_trades)
        results.winning_trades = len([t for t in closed_trades if t.pnl > 0])
        results.losing_trades = len([t for t in closed_trades if t.pnl < 0])
        results.win_rate = results.winning_trades / results.total_trades if results.total_trades > 0 else 0
        
        # Returns
        total_pnl = sum(t.pnl for t in closed_trades)
        total_fees = sum(t.fees for t in closed_trades)
        results.total_return = total_pnl - total_fees
        results.total_return_percent = (results.total_return / self.initial_capital) * 100
        
        # Annualized return
        days = (end_date - start_date).days
        if days > 0:
            results.annualized_return = ((1 + results.total_return_percent / 100) ** (365 / days) - 1) * 100
        
        # Risk metrics
        if equity_curve:
            peak = self.initial_capital
            max_dd = 0
            for equity in equity_curve:
                if equity > peak:
                    peak = equity
                else:
                    drawdown = (peak - equity) / peak
                    max_dd = max(max_dd, drawdown)
            
            results.max_drawdown = peak - min(equity_curve)
            results.max_drawdown_percent = max_dd * 100
            
            # Calculate daily returns for Sharpe ratio
            daily_returns = []
            for i in range(1, len(equity_curve)):
                daily_return = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                daily_returns.append(daily_return)
            
            results.daily_returns = daily_returns
            
            if daily_returns:
                avg_daily_return = np.mean(daily_returns)
                std_daily_return = np.std(daily_returns)
                
                if std_daily_return > 0:
                    # Assuming 252 trading days per year, risk-free rate of 5%
                    risk_free_rate = 0.05 / 252
                    results.sharpe_ratio = (avg_daily_return - risk_free_rate) / std_daily_return * np.sqrt(252)
                    
                    # Sortino ratio (downside deviation)
                    negative_returns = [r for r in daily_returns if r < 0]
                    if negative_returns:
                        downside_std = np.std(negative_returns)
                        results.sortino_ratio = (avg_daily_return - risk_free_rate) / downside_std * np.sqrt(252)
        
        # Trade analysis
        pnls = [t.pnl for t in closed_trades]
        results.avg_trade_return = np.mean(pnls)
        
        winning_pnls = [t.pnl for t in closed_trades if t.pnl > 0]
        losing_pnls = [t.pnl for t in closed_trades if t.pnl < 0]
        
        if winning_pnls:
            results.avg_winning_trade = np.mean(winning_pnls)
            results.largest_win = max(winning_pnls)
        
        if losing_pnls:
            results.avg_losing_trade = np.mean(losing_pnls)
            results.largest_loss = min(losing_pnls)
        
        # Trade duration
        durations = []
        for trade in closed_trades:
            if trade.exit_time:
                duration = trade.exit_time - trade.entry_time
                durations.append(duration)
        
        if durations:
            results.avg_trade_duration = sum(durations, timedelta()) / len(durations)
        
        results.total_fees = total_fees
        
        return results


class MockMarketDataService:
    """Mock market data service for backtesting"""
    
    def __init__(self, historical_data: pd.DataFrame):
        self.historical_data = historical_data
        self.current_index = 0
        self.current_timestamp = None
        self.current_row = None
    
    def update_current_data(self, index: int, timestamp: datetime, row: pd.Series):
        """Update current data point"""
        self.current_index = index
        self.current_timestamp = timestamp
        self.current_row = row
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker data"""
        if self.current_row is None:
            return None
        
        return {
            "symbol": symbol,
            "price": self.current_row['close'],
            "high_24h": self.current_row['high'],
            "low_24h": self.current_row['low'],
            "volume_24h": self.current_row['volume'],
            "change_24h": 0,  # Simplified
            "change_percent_24h": 0,
            "timestamp": self.current_timestamp
        }
    
    def get_candles(self, symbol: str, interval: str = "1m", limit: int = 100) -> Optional[List[Dict]]:
        """Get historical candles up to current point"""
        if self.current_index < limit:
            start_idx = 0
        else:
            start_idx = self.current_index - limit + 1
        
        end_idx = self.current_index + 1
        subset = self.historical_data.iloc[start_idx:end_idx]
        
        candles = []
        for timestamp, row in subset.iterrows():
            candles.append({
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
                'time': timestamp
            })
        
        return candles


class BacktestReportGenerator:
    """Generate detailed backtest reports"""
    
    @staticmethod
    def generate_report(results: BacktestResults) -> Dict[str, Any]:
        """Generate comprehensive backtest report"""
        
        report = {
            "strategy_info": {
                "name": results.strategy_name,
                "symbol": results.symbol,
                "start_date": results.start_date.isoformat(),
                "end_date": results.end_date.isoformat(),
                "test_duration_days": (results.end_date - results.start_date).days
            },
            "performance_summary": {
                "total_return": f"{results.total_return:.2f}",
                "total_return_percent": f"{results.total_return_percent:.2f}%",
                "annualized_return": f"{results.annualized_return:.2f}%",
                "max_drawdown": f"{results.max_drawdown:.2f}",
                "max_drawdown_percent": f"{results.max_drawdown_percent:.2f}%",
                "sharpe_ratio": f"{results.sharpe_ratio:.3f}",
                "sortino_ratio": f"{results.sortino_ratio:.3f}"
            },
            "trade_statistics": {
                "total_trades": results.total_trades,
                "winning_trades": results.winning_trades,
                "losing_trades": results.losing_trades,
                "win_rate": f"{results.win_rate:.2%}",
                "avg_trade_return": f"{results.avg_trade_return:.2f}",
                "avg_winning_trade": f"{results.avg_winning_trade:.2f}",
                "avg_losing_trade": f"{results.avg_losing_trade:.2f}",
                "largest_win": f"{results.largest_win:.2f}",
                "largest_loss": f"{results.largest_loss:.2f}",
                "avg_trade_duration": str(results.avg_trade_duration),
                "total_fees": f"{results.total_fees:.2f}"
            }
        }
        
        # Add trade details
        if results.trades:
            trade_details = []
            for trade in results.trades:
                trade_details.append({
                    "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "side": trade.side,
                    "pnl": trade.pnl,
                    "pnl_percent": trade.pnl_percent,
                    "fees": trade.fees,
                    "is_open": trade.is_open
                })
            
            report["trade_details"] = trade_details
        
        return report
    
    @staticmethod
    def save_report(results: BacktestResults, filename: str):
        """Save report to JSON file"""
        report = BacktestReportGenerator.generate_report(results)
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Backtest report saved to {filename}")


# Example usage and strategy comparison
class StrategyComparison:
    """Compare multiple strategies on the same data"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.backtest_engine = BacktestEngine(initial_capital)
    
    async def compare_strategies(self, 
                                strategies: List[BaseStrategy],
                                symbols: List[str],
                                start_date: datetime,
                                end_date: datetime,
                                interval: str = "1h") -> Dict[str, List[BacktestResults]]:
        """Compare multiple strategies across multiple symbols"""
        
        comparison_results = {}
        
        for strategy in strategies:
            strategy_results = []
            
            for symbol in symbols:
                try:
                    result = await self.backtest_engine.run_backtest(
                        strategy, symbol, start_date, end_date, interval
                    )
                    strategy_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error backtesting {strategy.name} on {symbol}: {e}")
            
            comparison_results[strategy.name] = strategy_results
        
        return comparison_results
    
    def generate_comparison_report(self, comparison_results: Dict[str, List[BacktestResults]]) -> Dict[str, Any]:
        """Generate comparison report"""
        
        summary = {}
        
        for strategy_name, results in comparison_results.items():
            if not results:
                continue
            
            # Aggregate results across symbols
            total_return = sum(r.total_return_percent for r in results)
            avg_return = total_return / len(results)
            
            total_trades = sum(r.total_trades for r in results)
            total_winning = sum(r.winning_trades for r in results)
            avg_win_rate = (total_winning / total_trades) * 100 if total_trades > 0 else 0
            
            avg_sharpe = sum(r.sharpe_ratio for r in results if r.sharpe_ratio) / len(results)
            max_drawdown = max(r.max_drawdown_percent for r in results)
            
            summary[strategy_name] = {
                "symbols_tested": len(results),
                "avg_return_percent": avg_return,
                "total_trades": total_trades,
                "avg_win_rate": avg_win_rate,
                "avg_sharpe_ratio": avg_sharpe,
                "max_drawdown_percent": max_drawdown,
                "symbol_results": {
                    r.symbol: {
                        "return_percent": r.total_return_percent,
                        "trades": r.total_trades,
                        "win_rate": r.win_rate * 100,
                        "sharpe_ratio": r.sharpe_ratio,
                        "max_drawdown": r.max_drawdown_percent
                    }
                    for r in results
                }
            }
        
        return summary
