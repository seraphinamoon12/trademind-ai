"""Safety API routes."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pathlib import Path

from src.core.database import get_db, CircuitBreakerEvent, RiskEvent
from src.core.safety_manager import safety_manager, SafetyManager
from src.core.circuit_breaker import circuit_breaker
from src.portfolio.manager import PortfolioManager

router = APIRouter()


class EmergencyStopRequest(BaseModel):
    reason: str


class CircuitBreakerResetRequest(BaseModel):
    confirm: bool = False
    reset_by: str = "manual"


# Initialize safety manager
_safety_manager: SafetyManager = None

def get_safety_manager():
    global _safety_manager
    if _safety_manager is None:
        _safety_manager = SafetyManager()
    return _safety_manager


@router.get("/status")
async def get_safety_status(db: Session = Depends(get_db)):
    """Get complete safety system status."""
    safety = get_safety_manager()
    pm = PortfolioManager()
    
    portfolio = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)
    
    status = safety.get_safety_status(
        portfolio_value=portfolio['total_value'],
        holdings=holdings
    )
    
    return status


@router.get("/circuit-breaker")
async def get_circuit_breaker_status():
    """Get circuit breaker status."""
    return circuit_breaker.get_status()


@router.post("/circuit-breaker/trigger")
async def trigger_circuit_breaker(
    request: EmergencyStopRequest,
    db: Session = Depends(get_db)
):
    """Manually trigger circuit breaker."""
    safety = get_safety_manager()
    
    # Log to database
    event = CircuitBreakerEvent(
        reason=f"MANUAL: {request.reason}",
        portfolio_value=0,  # Will be updated
        triggered_at=datetime.utcnow()
    )
    db.add(event)
    db.commit()
    
    safety.emergency_stop(request.reason, triggered_by="api")
    
    return {
        "status": "halted",
        "reason": request.reason,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/circuit-breaker/reset")
async def reset_circuit_breaker(
    request: CircuitBreakerResetRequest,
    db: Session = Depends(get_db)
):
    """Reset circuit breaker (requires explicit confirmation)."""
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to reset circuit breaker"
        )
    
    safety = get_safety_manager()
    
    if not circuit_breaker.is_halted:
        return {
            "status": "already_reset",
            "message": "Circuit breaker is not currently triggered"
        }
    
    # Update the most recent circuit breaker event
    recent_event = db.query(CircuitBreakerEvent).filter(
        CircuitBreakerEvent.reset_at.is_(None)
    ).order_by(CircuitBreakerEvent.triggered_at.desc()).first()
    
    if recent_event:
        recent_event.reset_at = datetime.utcnow()
        recent_event.reset_by = request.reset_by
        db.commit()
    
    success = safety.reset_circuit_breaker(reset_by=request.reset_by)
    
    return {
        "status": "reset" if success else "failed",
        "reset_by": request.reset_by,
        "previous_halt_reason": circuit_breaker.halt_reason if not success else None,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/emergency/stop")
async def emergency_stop(
    request: EmergencyStopRequest,
    db: Session = Depends(get_db)
):
    """
    Emergency stop endpoint.
    Immediately halts all trading via kill switch.
    """
    safety = get_safety_manager()
    
    # Create kill switch file
    kill_file = Path("/tmp/trading_stop")
    kill_file.write_text(
        f"Emergency stop triggered at {datetime.utcnow().isoformat()}\n"
        f"Reason: {request.reason}"
    )
    
    # Trigger circuit breaker
    safety.emergency_stop(request.reason, triggered_by="emergency_api")
    
    # Log to database
    event = RiskEvent(
        event_type="emergency_stop",
        reason=request.reason,
        details={"triggered_by": "emergency_api"}
    )
    db.add(event)
    db.commit()
    
    return {
        "status": "emergency_halt",
        "reason": request.reason,
        "kill_switch_file": str(kill_file),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/market")
async def get_market_status():
    """Get market hours and trading time status."""
    from src.core.time_filter import time_filter
    return time_filter.get_market_status()


@router.get("/portfolio-heat")
async def get_portfolio_heat(db: Session = Depends(get_db)):
    """Get current portfolio heat status."""
    safety = get_safety_manager()
    pm = PortfolioManager()
    
    portfolio = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)
    
    heat_status = safety.get_portfolio_heat_status(
        holdings=holdings,
        portfolio_value=portfolio['total_value']
    )
    
    return heat_status


@router.get("/position-sizing/{symbol}")
async def get_position_sizing(
    symbol: str,
    entry_price: float,
    db: Session = Depends(get_db)
):
    """
    Get volatility-based position sizing for a symbol.
    
    Args:
        symbol: Stock symbol
        entry_price: Proposed entry price
    """
    safety = get_safety_manager()
    pm = PortfolioManager()
    
    portfolio = pm.get_portfolio_value(db)
    
    sizing = safety.get_position_sizing(
        symbol=symbol.upper(),
        entry_price=entry_price,
        portfolio_value=portfolio['total_value']
    )
    
    return sizing


@router.get("/events")
async def get_risk_events(
    limit: int = 50,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get risk events history."""
    query = db.query(RiskEvent)
    
    if event_type:
        query = query.filter(RiskEvent.event_type == event_type)
    
    events = query.order_by(RiskEvent.timestamp.desc()).limit(limit).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "event_type": e.event_type,
                "symbol": e.symbol,
                "strategy": e.strategy,
                "reason": e.reason,
                "details": e.details
            }
            for e in events
        ]
    }


@router.get("/circuit-breaker/history")
async def get_circuit_breaker_history(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get circuit breaker trigger history."""
    events = db.query(CircuitBreakerEvent).order_by(
        CircuitBreakerEvent.triggered_at.desc()
    ).limit(limit).all()
    
    return {
        "events": [
            {
                "id": e.id,
                "triggered_at": e.triggered_at.isoformat(),
                "reason": e.reason,
                "portfolio_value": float(e.portfolio_value) if e.portfolio_value else None,
                "daily_pnl": float(e.daily_pnl) if e.daily_pnl else None,
                "drawdown_pct": float(e.drawdown_pct) if e.drawdown_pct else None,
                "reset_at": e.reset_at.isoformat() if e.reset_at else None,
                "reset_by": e.reset_by
            }
            for e in events
        ]
    }
