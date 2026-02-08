"""Trades API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.core.database import get_db, Trade
from src.portfolio.manager import PortfolioManager

router = APIRouter()


class TradeRequest(BaseModel):
    symbol: str
    action: str  # BUY or SELL
    quantity: int
    price: float
    strategy: str = "manual"
    reasoning: str = ""


@router.get("/")
async def get_trades(
    limit: int = 50,
    symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get trade history."""
    query = db.query(Trade)
    
    if symbol:
        query = query.filter(Trade.symbol == symbol.upper())
    
    trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
    
    return {
        "trades": [
            {
                "id": t.id,
                "timestamp": t.timestamp.isoformat(),
                "symbol": t.symbol,
                "action": t.action,
                "quantity": t.quantity,
                "price": float(t.price),
                "total_value": float(t.total_value),
                "strategy": t.strategy,
                "confidence": float(t.confidence) if t.confidence else None
            }
            for t in trades
        ]
    }


@router.post("/")
async def execute_trade(
    trade: TradeRequest,
    db: Session = Depends(get_db)
):
    """Execute a manual trade."""
    pm = PortfolioManager()
    
    success = pm.execute_trade(
        symbol=trade.symbol,
        action=trade.action.upper(),
        quantity=trade.quantity,
        price=trade.price,
        strategy=trade.strategy,
        reasoning=trade.reasoning,
        confidence=1.0,
        agent_signals={"manual": True},
        db=db
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Trade execution failed")
    
    return {"status": "success", "message": f"{trade.action} {trade.quantity} {trade.symbol}"}
