from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.services.order_manager import OrderManager
from app.models.schemas import ApiResponse, PortfolioResponse, BalanceResponse

router = APIRouter()

# This would be injected properly in a real application
order_manager = None

def get_order_manager() -> OrderManager:
    """Dependency to get order manager"""
    global order_manager
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager service not available")
    return order_manager

@router.get("/balance", response_model=ApiResponse)
async def get_portfolio_balance(
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get complete portfolio balance"""
    try:
        balance = await order_mgr.get_portfolio_balance()
        
        return ApiResponse(
            success=True,
            message="Portfolio balance retrieved successfully",
            data=balance
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balance/{currency}", response_model=ApiResponse)
async def get_currency_balance(
    currency: str,
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get balance for a specific currency"""
    try:
        balance = await order_mgr.get_portfolio_balance(currency)
        
        if not balance:
            raise HTTPException(status_code=404, detail=f"Balance not found for {currency}")
        
        return ApiResponse(
            success=True,
            message=f"Balance for {currency} retrieved successfully",
            data=balance
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/holdings", response_model=ApiResponse)
async def get_holdings(
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get all non-zero holdings"""
    try:
        all_balances = await order_mgr.get_portfolio_balance()
        
        # Filter out zero balances
        holdings = {
            currency: balance 
            for currency, balance in all_balances.items() 
            if balance.get('balance', 0) > 0
        }
        
        # Calculate total portfolio value in INR
        total_value = 0.0
        for currency, balance in holdings.items():
            if currency == 'INR':
                total_value += balance.get('balance', 0)
            # For other currencies, we'd need to get current prices and convert
        
        return ApiResponse(
            success=True,
            message="Holdings retrieved successfully",
            data={
                "holdings": holdings,
                "total_value_inr": total_value,
                "holding_count": len(holdings)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/allocation", response_model=ApiResponse)
async def get_portfolio_allocation(
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get portfolio allocation percentages"""
    try:
        all_balances = await order_mgr.get_portfolio_balance()
        
        # Calculate total portfolio value (simplified - only INR for now)
        total_value = 0.0
        allocations = {}
        
        for currency, balance in all_balances.items():
            balance_value = balance.get('balance', 0)
            if balance_value > 0:
                if currency == 'INR':
                    total_value += balance_value
                    allocations[currency] = balance_value
                else:
                    # For crypto currencies, we'd need current prices
                    # For now, just include with placeholder value
                    allocations[currency] = balance_value
        
        # Calculate percentages
        allocation_percentages = {}
        if total_value > 0:
            for currency, value in allocations.items():
                if currency == 'INR':
                    allocation_percentages[currency] = (value / total_value) * 100
                else:
                    allocation_percentages[currency] = 0.0  # Placeholder
        
        return ApiResponse(
            success=True,
            message="Portfolio allocation retrieved successfully",
            data={
                "total_value_inr": total_value,
                "allocations": allocation_percentages,
                "raw_balances": allocations
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=ApiResponse)
async def get_portfolio_summary(
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get portfolio summary with key metrics"""
    try:
        all_balances = await order_mgr.get_portfolio_balance()
        
        # Calculate summary metrics
        total_currencies = len([
            b for b in all_balances.values() 
            if b.get('balance', 0) > 0
        ])
        
        total_inr_balance = all_balances.get('INR', {}).get('balance', 0)
        total_locked = sum(
            b.get('locked_balance', 0) 
            for b in all_balances.values()
        )
        
        # Get active orders count (would need to implement this)
        active_orders_count = 0
        
        summary = {
            "total_currencies": total_currencies,
            "total_inr_balance": total_inr_balance,
            "total_locked_balance": total_locked,
            "active_orders_count": active_orders_count,
            "available_for_trading": total_inr_balance - total_locked,
            "last_updated": "2025-01-18T12:00:00Z"  # Would be actual timestamp
        }
        
        return ApiResponse(
            success=True,
            message="Portfolio summary retrieved successfully",
            data=summary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ApiResponse)
async def get_portfolio_history(
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get portfolio value history"""
    try:
        # This would need to be implemented with historical data tracking
        # For now, return placeholder data
        history = {
            "days": days,
            "data_points": [],
            "total_return": 0.0,
            "total_return_percent": 0.0,
            "best_day": {"date": "2025-01-15", "return": 500.0},
            "worst_day": {"date": "2025-01-10", "return": -200.0}
        }
        
        return ApiResponse(
            success=True,
            message="Portfolio history retrieved successfully",
            data=history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance", response_model=ApiResponse)
async def get_portfolio_performance(
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get portfolio performance metrics"""
    try:
        # This would calculate actual performance metrics
        # For now, return placeholder data
        performance = {
            "total_return": 0.0,
            "total_return_percent": 0.0,
            "daily_return": 0.0,
            "daily_return_percent": 0.0,
            "weekly_return": 0.0,
            "weekly_return_percent": 0.0,
            "monthly_return": 0.0,
            "monthly_return_percent": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "volatility": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0
        }
        
        return ApiResponse(
            success=True,
            message="Portfolio performance retrieved successfully",
            data=performance
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
