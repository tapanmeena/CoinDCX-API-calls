from fastapi import APIRouter
from app.api.v1.endpoints import market_data, orders, strategies, portfolio, analytics, backtesting

router = APIRouter()

router.include_router(market_data.router, prefix="/market", tags=["market-data"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(backtesting.router, prefix="/backtesting", tags=["backtesting"])
