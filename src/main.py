"""FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import asyncio
import logging

from src.core.database import init_db, get_db
from src.config import settings
from src.api.routes import portfolio, trades, strategies, agent, safety, human_review, config
from src.api.routes import ibkr_trading
from src.api.routes import market_mood

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    # Startup: Initialize database and IBKR if enabled
    init_db()
    logger.info(f"✅ {settings.app_name} started")
    logger.info(f"   Mode: {settings.app_mode}")
    logger.info(f"   Database: {settings.database_url}")

    # Initialize IBKR integration in the running event loop
    if settings.ibkr_enabled:
        from src.brokers.ibkr.integration import get_ibkr_integration
        try:
            ibkr = get_ibkr_integration()
            await ibkr.initialize_in_loop()
            logger.info(f"   IBKR: Initialized in event loop (connection on-demand)")
        except Exception as e:
            logger.error(f"   IBKR: Initialization failed: {e}")
    else:
        logger.info(f"   IBKR: Disabled")

    yield

    # Shutdown: Cleanup IBKR connection
    if settings.ibkr_enabled:
        from src.brokers.ibkr.integration import get_ibkr_integration
        try:
            ibkr = get_ibkr_integration()
            await ibkr.disconnect()
            logger.info("IBKR connection closed")
        except Exception as e:
            logger.error(f"Error closing IBKR connection: {e}")


app = FastAPI(
    title=settings.app_name,
    description="AI-powered trading agent with rule-based strategies",
    version="1.0.0",
    lifespan=lifespan
)

# Setup templates
templates = Jinja2Templates(directory="src/api/templates")

# Include routers
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(agent.router, prefix="/api/agent", tags=["agent"])
app.include_router(safety.router, prefix="/api/safety", tags=["safety"])
app.include_router(human_review.router, prefix="", tags=["human-review"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(ibkr_trading.router, prefix="/api/ibkr", tags=["IBKR Trading"])
app.include_router(market_mood.router, prefix="/api/market", tags=["market-mood"])


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page."""
    from src.portfolio.manager import PortfolioManager
    
    pm = PortfolioManager()
    portfolio_data = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": settings.app_name,
        "portfolio": portfolio_data,
        "holdings": holdings,
        "watchlist": settings.watchlist
    })


@app.get("/backtest", response_class=HTMLResponse)
async def backtest_page(request: Request):
    """Backtesting page."""
    return templates.TemplateResponse("backtest.html", {
        "request": request,
        "app_name": settings.app_name,
        "watchlist": settings.watchlist
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
