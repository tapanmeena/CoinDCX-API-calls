from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from app.services.market_data_service import MarketDataService
from app.models.schemas import ApiResponse, TickerResponse, MarketDataResponse

router = APIRouter()

# Global service instance
_market_service_instance = None

def get_market_service() -> MarketDataService:
    """Dependency to get market data service"""
    global _market_service_instance
    if not _market_service_instance:
        _market_service_instance = MarketDataService()
    return _market_service_instance

@router.get("/ticker/{symbol}", response_model=ApiResponse)
async def get_ticker(
    symbol: str,
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get ticker data for a specific symbol"""
    try:
        ticker = market_service.get_ticker(symbol)
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker data not found for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Ticker data retrieved successfully",
            data=ticker
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ticker", response_model=ApiResponse)
async def get_all_tickers(
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get ticker data for all symbols"""
    try:
        tickers = market_service.get_all_tickers()
        return ApiResponse(
            success=True,
            message="All ticker data retrieved successfully",
            data=tickers
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/data/{symbol}", response_model=ApiResponse)
async def get_market_data(
    symbol: str,
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get market data for a specific symbol"""
    try:
        market_data = market_service.get_market_data(symbol)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"Market data not found for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Market data retrieved successfully",
            data=market_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candles/{symbol}", response_model=ApiResponse)
async def get_candles(
    symbol: str,
    interval: str = Query("1m", description="Candle interval (1m, 5m, 15m, 1h, 1d)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles to retrieve"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get candlestick data for a symbol"""
    try:
        candles = market_service.get_candles(symbol, interval, limit)
        if not candles:
            raise HTTPException(status_code=404, detail=f"Candle data not found for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Candle data retrieved successfully",
            data={
                "symbol": symbol,
                "interval": interval,
                "candles": candles
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/historical/{symbol}", response_model=ApiResponse)
async def get_historical_data(
    symbol: str,
    interval: str = Query("1m", description="Candle interval"),
    start_time: Optional[str] = Query(None, description="Start time (timestamp or ISO string)"),
    end_time: Optional[str] = Query(None, description="End time (timestamp or ISO string)"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get historical market data"""
    try:
        # Default to last 24 hours if no time range specified
        if not start_time:
            start_time = str(int((datetime.now() - timedelta(days=1)).timestamp()))
        if not end_time:
            end_time = str(int(datetime.now().timestamp()))
        
        historical_data = await market_service.get_historical_data(
            symbol, interval, start_time, end_time
        )
        
        if not historical_data:
            raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Historical data retrieved successfully",
            data={
                "symbol": symbol,
                "interval": interval,
                "start_time": start_time,
                "end_time": end_time,
                "data": historical_data
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price-change/{symbol}", response_model=ApiResponse)
async def get_price_change(
    symbol: str,
    minutes: int = Query(5, ge=1, le=1440, description="Time period in minutes"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get price change percentage for a symbol over specified minutes"""
    try:
        price_change = market_service.calculate_price_change(symbol, minutes)
        if price_change is None:
            raise HTTPException(status_code=404, detail=f"Price change data not available for {symbol}")
        
        return ApiResponse(
            success=True,
            message="Price change calculated successfully",
            data={
                "symbol": symbol,
                "minutes": minutes,
                "price_change_percent": price_change
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=ApiResponse)
async def get_market_summary(
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get market summary with top gainers and losers"""
    try:
        summary = market_service.get_market_summary()
        return ApiResponse(
            success=True,
            message="Market summary retrieved successfully",
            data=summary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gainers", response_model=ApiResponse)
async def get_top_gainers(
    limit: int = Query(10, ge=1, le=50, description="Number of top gainers to return"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get top gaining cryptocurrencies"""
    try:
        summary = market_service.get_market_summary()
        gainers = summary.get("top_gainers", [])[:limit]
        
        return ApiResponse(
            success=True,
            message="Top gainers retrieved successfully",
            data={
                "count": len(gainers),
                "gainers": gainers
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/losers", response_model=ApiResponse)
async def get_top_losers(
    limit: int = Query(10, ge=1, le=50, description="Number of top losers to return"),
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get top losing cryptocurrencies"""
    try:
        summary = market_service.get_market_summary()
        losers = summary.get("top_losers", [])[:limit]
        
        return ApiResponse(
            success=True,
            message="Top losers retrieved successfully",
            data={
                "count": len(losers),
                "losers": losers
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", response_model=ApiResponse)
async def get_market_data_status(
    market_service: MarketDataService = Depends(get_market_service)
):
    """Get market data service status"""
    try:
        return ApiResponse(
            success=True,
            message="Market data service status",
            data={
                "is_running": market_service.is_running,
                "total_symbols_tracked": len(market_service._ticker_cache),
                "last_update": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
