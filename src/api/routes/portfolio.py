"""Portfolio API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict

from src.core.database import get_db
from src.config import settings
from src.portfolio.manager import PortfolioManager
from src.data.providers import yahoo_provider
from src.brokers.ibkr.integration import get_ibkr_integration

router = APIRouter()


@router.get("/")
async def get_portfolio(db: Session = Depends(get_db)):
    """Get current portfolio summary."""
    # Try to connect to IB Gateway if enabled
    if settings.ibkr_enabled:
        try:
            ibkr = get_ibkr_integration()
            account_summary = await ibkr.get_account_summary()
            if account_summary:
                return {
                    "portfolio": {
                        "total_value": account_summary["portfolio_value"],
                        "cash_balance": account_summary["cash_balance"],
                        "invested_value": account_summary["portfolio_value"] - account_summary["cash_balance"],
                        "total_return_pct": 0.0,
                        "daily_pnl": account_summary.get("daily_pnl", 0),
                        "daily_pnl_pct": 0.0
                    },
                    "holdings": {},
                    "source": "ib_gateway"
                }
        except Exception as e:
            # Fall back to internal DB
            pass
    
    # Fall back to internal database
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
        "holdings": holdings,
        "source": "internal"
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


@router.post("/sync")
async def sync_with_ibkr(db: Session = Depends(get_db)):
    """Manually sync portfolio with IB Gateway."""
    if not settings.ibkr_enabled:
        raise HTTPException(
            status_code=503,
            detail="IBKR integration disabled"
        )
    
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
            raise HTTPException(
                status_code=500,
                detail=f"Sync failed: {result.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


@router.get("/account")
async def get_account_info():
    """Get IB Gateway account information."""
    if not settings.ibkr_enabled:
        raise HTTPException(
            status_code=503,
            detail="IBKR integration disabled"
        )
    
    try:
        ibkr = get_ibkr_integration()
        account = await ibkr.get_account_summary()
        
        if account:
            return {
                "status": "connected",
                "account": account
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to get account info"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )
