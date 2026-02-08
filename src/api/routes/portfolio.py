"""Portfolio API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from src.core.database import get_db
from src.portfolio.manager import PortfolioManager
from src.data.providers import yahoo_provider

router = APIRouter()


@router.get("/")
async def get_portfolio(db: Session = Depends(get_db)):
    """Get current portfolio summary."""
    pm = PortfolioManager()
    portfolio = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)
    
    # Update prices
    symbols = list(holdings.keys())
    if symbols:
        prices = {s: yahoo_provider.get_current_price(s) for s in symbols}
        pm.update_prices(prices, db)
        holdings = pm.get_holdings(db)
    
    return {
        "portfolio": portfolio,
        "holdings": holdings
    }


@router.get("/holdings")
async def get_holdings(db: Session = Depends(get_db)):
    """Get current holdings."""
    pm = PortfolioManager()
    return pm.get_holdings(db)


@router.post("/update-prices")
async def update_prices(db: Session = Depends(get_db)):
    """Update prices for all holdings."""
    pm = PortfolioManager()
    holdings = pm.get_holdings(db)
    
    if not holdings:
        return {"updated": 0}
    
    symbols = list(holdings.keys())
    prices = {s: yahoo_provider.get_current_price(s) for s in symbols}
    pm.update_prices(prices, db)
    
    return {"updated": len(prices), "prices": prices}


@router.get("/performance")
async def get_performance(days: int = 30, db: Session = Depends(get_db)):
    """Get portfolio performance over time."""
    from src.core.database import PortfolioSnapshot
    from datetime import datetime, timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    snapshots = db.query(PortfolioSnapshot).filter(
        PortfolioSnapshot.timestamp >= cutoff
    ).order_by(PortfolioSnapshot.timestamp).all()
    
    return {
        "snapshots": [
            {
                "timestamp": s.timestamp.isoformat(),
                "total_value": float(s.total_value),
                "cash_balance": float(s.cash_balance),
                "invested_value": float(s.invested_value),
                "total_return_pct": float(s.total_return_pct)
            }
            for s in snapshots
        ]
    }
