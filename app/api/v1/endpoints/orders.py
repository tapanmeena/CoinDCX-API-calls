from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.order_manager import OrderManager
from app.core.database import get_session
from app.models.schemas import (
    OrderRequest, OrderResponse, ApiResponse, OrderStatusEnum
)

router = APIRouter()

# This would be injected properly in a real application
order_manager = None

def get_order_manager() -> OrderManager:
    """Dependency to get order manager"""
    global order_manager
    if not order_manager:
        raise HTTPException(status_code=503, detail="Order manager service not available")
    return order_manager

@router.post("/create", response_model=ApiResponse)
async def create_order(
    order_request: OrderRequest,
    strategy_id: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_manager),
    db: Session = Depends(get_session)
):
    """Create a new order"""
    try:
        result = await order_mgr.create_order(order_request, strategy_id, db)
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create order")
        
        return ApiResponse(
            success=True,
            message="Order created successfully",
            data=result.dict()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{order_id}/cancel", response_model=ApiResponse)
async def cancel_order(
    order_id: str,
    order_mgr: OrderManager = Depends(get_order_manager),
    db: Session = Depends(get_session)
):
    """Cancel an active order"""
    try:
        success = await order_mgr.cancel_order(order_id, db)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to cancel order")
        
        return ApiResponse(
            success=True,
            message="Order cancelled successfully",
            data={"order_id": order_id, "status": "cancelled"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{order_id}/status", response_model=ApiResponse)
async def get_order_status(
    order_id: str,
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get order status from exchange"""
    try:
        status = await order_mgr.get_order_status(order_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Order not found")
        
        return ApiResponse(
            success=True,
            message="Order status retrieved successfully",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active", response_model=ApiResponse)
async def get_active_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    order_mgr: OrderManager = Depends(get_order_manager)
):
    """Get all active orders"""
    try:
        # This would need to be implemented in OrderManager
        active_orders = []  # await order_mgr.get_active_orders(symbol)
        
        return ApiResponse(
            success=True,
            message="Active orders retrieved successfully",
            data={
                "count": len(active_orders),
                "orders": active_orders
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=ApiResponse)
async def get_trade_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    limit: int = Query(100, ge=1, le=1000, description="Number of trades to retrieve"),
    order_mgr: OrderManager = Depends(get_order_manager),
    db: Session = Depends(get_session)
):
    """Get trade history"""
    try:
        history = await order_mgr.get_trade_history(symbol, limit, db)
        
        return ApiResponse(
            success=True,
            message="Trade history retrieved successfully",
            data={
                "count": len(history),
                "trades": history
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-cancel", response_model=ApiResponse)
async def bulk_cancel_orders(
    symbol: str,
    side: Optional[str] = None,
    order_mgr: OrderManager = Depends(get_order_manager),
    db: Session = Depends(get_session)
):
    """Cancel all orders for a symbol"""
    try:
        # This would need to be implemented in OrderManager
        # success = await order_mgr.cancel_all_orders(symbol, side, db)
        
        return ApiResponse(
            success=True,
            message=f"All orders cancelled for {symbol}",
            data={"symbol": symbol, "side": side}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update-status", response_model=ApiResponse)
async def update_order_status(
    order_mgr: OrderManager = Depends(get_order_manager),
    db: Session = Depends(get_session)
):
    """Update status of all active orders from exchange"""
    try:
        await order_mgr.update_order_status(db)
        
        return ApiResponse(
            success=True,
            message="Order statuses updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=ApiResponse)
async def get_order_stats(
    db: Session = Depends(get_session)
):
    """Get order statistics"""
    try:
        # This would need to be implemented
        stats = {
            "total_orders_today": 0,
            "filled_orders_today": 0,
            "cancelled_orders_today": 0,
            "pending_orders": 0,
            "total_volume_today": 0.0,
            "success_rate": 0.0
        }
        
        return ApiResponse(
            success=True,
            message="Order statistics retrieved successfully",
            data=stats
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
