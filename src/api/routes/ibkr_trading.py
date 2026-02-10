"""IBKR Trading API routes - Execute trades via IB Gateway."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import re

from src.core.database import get_db, Trade
from src.config import settings
from src.brokers.ibkr.integration import get_ibkr_integration
from src.brokers.base import Order, OrderType, OrderSide, OrderStatus

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Request/Response Models ==============

class OrderRequest(BaseModel):
    """Order request model."""
    symbol: str = Field(..., description="Stock symbol (e.g., AAPL)", max_length=10)
    quantity: int = Field(..., gt=0, description="Number of shares")
    side: Literal["buy", "sell"] = Field(..., description="Order side")
    order_type: Literal["market", "limit"] = Field(default="market", description="Order type")
    price: Optional[float] = Field(default=None, description="Limit price (required for limit orders)")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        """Validate symbol format."""
        v = v.upper().strip()
        if not re.match(r'^[A-Z]{1,10}$', v):
            raise ValueError('Symbol must be 1-10 uppercase letters')
        return v
    
    @validator('price')
    def validate_price(cls, v, values):
        """Validate price for limit orders."""
        if values.get('order_type') == 'limit' and (v is None or v <= 0):
            raise ValueError('Limit orders require a positive price')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 10,
                "side": "buy",
                "order_type": "market"
            }
        }


class OrderResponse(BaseModel):
    """Order response model."""
    order_id: str
    symbol: str
    quantity: int
    side: str
    order_type: str
    price: Optional[float]
    status: str
    message: str


class PositionResponse(BaseModel):
    """Position response model."""
    symbol: str
    quantity: int
    avg_cost: float
    market_price: Optional[float]
    market_value: float
    unrealized_pnl: float


class IBOrderResponse(BaseModel):
    """IB Order response model."""
    order_id: str
    symbol: str
    quantity: int
    side: str
    order_type: str
    status: str
    filled_quantity: int
    remaining_quantity: int
    avg_fill_price: Optional[float]


# ============== IBKR Status Endpoints ==============

@router.get("/status")
async def get_ibkr_status():
    """Check IBKR connection status."""
    try:
        ibkr = get_ibkr_integration()
        return {
            "enabled": settings.ibkr_enabled,
            "connected": ibkr.is_connected,
            "paper_trading": settings.ibkr_paper_trading,
            "mode": "paper" if settings.ibkr_paper_trading else "live"
        }
    except Exception as e:
        return {
            "enabled": settings.ibkr_enabled,
            "connected": False,
            "error": str(e)
        }


@router.post("/connect")
async def connect_ibkr():
    """Connect to IBKR Gateway."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        connected = await ibkr.ensure_connected()
        
        if connected:
            return {"status": "connected", "message": "Connected to IB Gateway"}
        else:
            raise HTTPException(status_code=500, detail="Failed to connect to IB Gateway")
    except Exception as e:
        logger.error(f"IBKR connect error: {e}")
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")


@router.post("/disconnect")
async def disconnect_ibkr():
    """Disconnect from IBKR Gateway."""
    try:
        ibkr = get_ibkr_integration()
        await ibkr.disconnect()
        return {"status": "disconnected", "message": "Disconnected from IB Gateway"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect error: {str(e)}")


# ============== Account & Portfolio Endpoints ==============

@router.get("/account")
async def get_ibkr_account():
    """Get IBKR account summary."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        account = await ibkr.get_account_summary()
        
        if account:
            return {
                "status": "success",
                "account": account
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to get account info")
    except Exception as e:
        logger.error(f"IBKR account error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PositionResponse])
async def get_ibkr_positions():
    """Get current positions from IBKR."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        positions = await ibkr.broker.get_positions()
        
        return [
            {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_cost": pos.avg_cost,
                "market_price": getattr(pos, 'market_price', None),
                "market_value": getattr(pos, 'market_value', pos.quantity * pos.avg_cost),
                "unrealized_pnl": getattr(pos, 'unrealized_pnl', 0.0)
            }
            for pos in positions
        ]
    except Exception as e:
        logger.error(f"IBKR positions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Trading Endpoints ==============

@router.post("/orders", response_model=OrderResponse)
async def place_order(order_req: OrderRequest):
    """Place a new order via IB Gateway."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    # Enforce paper trading for safety
    if not settings.ibkr_paper_trading:
        logger.warning(f"Live trading order rejected: {order_req.side.upper()} {order_req.quantity} {order_req.symbol}")
        raise HTTPException(
            status_code=403, 
            detail="Live trading is disabled. Enable paper trading in settings."
        )
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        # Validate limit order has price
        if order_req.order_type == "limit" and order_req.price is None:
            raise HTTPException(status_code=400, detail="Limit orders require a price")
        
        # Create order object
        order = Order(
            order_id="",  # Will be assigned by broker
            symbol=order_req.symbol.upper(),
            quantity=order_req.quantity,
            order_type=OrderType.MARKET if order_req.order_type == "market" else OrderType.LIMIT,
            side=OrderSide.BUY if order_req.side == "buy" else OrderSide.SELL,
            price=order_req.price or 0.0
        )
        
        # Validate order
        is_valid, error_msg = await ibkr.broker.validate_order(order)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Place order
        order_id = await ibkr.broker.place_order(order)
        
        logger.info(f"Order placed: {order_id} - {order_req.side.upper()} {order_req.quantity} {order_req.symbol}")
        
        return {
            "order_id": order_id,
            "symbol": order_req.symbol.upper(),
            "quantity": order_req.quantity,
            "side": order_req.side.upper(),
            "order_type": order_req.order_type.upper(),
            "price": order_req.price,
            "status": "submitted",
            "message": f"Order {order_id} submitted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Place order error: {e}")
        raise HTTPException(status_code=500, detail=f"Order failed: {str(e)}")


@router.get("/orders", response_model=List[IBOrderResponse])
async def get_open_orders():
    """Get open orders from IB Gateway."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        orders = await ibkr.broker.get_orders()
        
        return [
            {
                "order_id": str(order.order_id),
                "symbol": order.symbol,
                "quantity": order.quantity,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "status": order.status.value,
                "filled_quantity": getattr(order, 'filled_quantity', 0),
                "remaining_quantity": getattr(order, 'remaining_quantity', order.quantity),
                "avg_fill_price": getattr(order, 'avg_fill_price', None)
            }
            for order in orders
            if order.status not in [OrderStatus.FILLED, OrderStatus.CANCELLED]
        ]
    except Exception as e:
        logger.error(f"Get orders error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an open order."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        success = await ibkr.broker.cancel_order(order_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Order {order_id} cancelled",
                "order_id": order_id
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to cancel order {order_id}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel order error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order_status(order_id: str):
    """Get status of a specific order."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    # Validate order_id is numeric
    try:
        order_id_int = int(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        # Get order from broker's order cache using public method
        orders = await ibkr.broker.get_orders()
        order = next((o for o in orders if str(o.order_id) == order_id), None)
        
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
        return {
            "order_id": str(order.order_id),
            "symbol": order.symbol,
            "quantity": order.quantity,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "price": order.price,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "filled_at": order.filled_at.isoformat() if order.filled_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Market Data Endpoints ==============

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a symbol."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        
        if not await ibkr.ensure_connected():
            raise HTTPException(status_code=503, detail="Not connected to IB Gateway")
        
        # Get market price
        price = await ibkr.broker.get_market_price(symbol.upper())
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"Could not get quote for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "price": price,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "ib_gateway"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get quote error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Utility Endpoints ==============

@router.post("/sync")
async def sync_portfolio(db: Session = Depends(get_db)):
    """Sync TradeMind portfolio with IB Gateway."""
    if not settings.ibkr_enabled:
        raise HTTPException(status_code=503, detail="IBKR integration disabled")
    
    try:
        ibkr = get_ibkr_integration()
        result = await ibkr.sync_portfolio(db)
        
        if result.get("success"):
            return {
                "status": "success",
                "message": "Portfolio synced with IB Gateway",
                "cash_balance": result["cash_balance"],
                "portfolio_value": result["portfolio_value"],
                "positions_count": result["positions_count"]
            }
        else:
            raise HTTPException(status_code=500, detail=f"Sync failed: {result.get('error')}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))