"""Strategies API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from src.core.database import get_db
from src.data.ingestion import ingestion
from src.data.indicators import TechnicalIndicators
from src.strategies.rsi_reversion import RSIMeanReversionStrategy
from src.strategies.ma_crossover import MACrossoverStrategy
from src.backtest.engine import BacktestEngine

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str  # rsi or ma_crossover
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_cash: float = 100000


@router.get("/")
async def list_strategies():
    """List available strategies."""
    return {
        "strategies": [
            {
                "name": "rsi_mean_reversion",
                "description": "RSI Mean Reversion - Buy oversold, Sell overbought",
                "parameters": {
                    "rsi_period": 14,
                    "oversold": 30,
                    "overbought": 70
                }
            },
            {
                "name": "ma_crossover",
                "description": "MA Crossover - Golden Cross buy, Death Cross sell",
                "parameters": {
                    "fast_period": 50,
                    "slow_period": 200
                }
            }
        ]
    }


@router.post("/signal")
async def get_signal(
    symbol: str,
    strategy: str = "rsi",
    db: Session = Depends(get_db)
):
    """Get current signal for a symbol."""
    # Get data
    df = ingestion.get_stored_data(symbol, days=365, db=db)
    
    if df is None:
        # Fetch and store
        ingestion.ingest_symbol(symbol, db=db)
        df = ingestion.get_stored_data(symbol, days=365, db=db)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    # Generate signal
    if strategy == "rsi":
        strat = RSIMeanReversionStrategy()
    elif strategy == "ma_crossover":
        strat = MACrossoverStrategy()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy}")
    
    signal = strat.generate_signal(df, symbol)
    
    if signal is None:
        return {"symbol": symbol, "signal": "HOLD", "confidence": 0}
    
    return {
        "symbol": signal.symbol,
        "signal": signal.signal.value,
        "confidence": signal.confidence,
        "strategy": signal.strategy,
        "price": signal.price,
        "metadata": signal.metadata
    }


@router.post("/backtest")
async def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(get_db)
):
    """Run backtest for a strategy."""
    # Get data
    df = ingestion.get_stored_data(request.symbol, days=730, db=db)
    
    if df is None:
        ingestion.ingest_symbol(request.symbol, period="2y", db=db)
        df = ingestion.get_stored_data(request.symbol, days=730, db=db)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {request.symbol}")
    
    # Select strategy
    if request.strategy == "rsi":
        strat = RSIMeanReversionStrategy()
    elif request.strategy == "ma_crossover":
        strat = MACrossoverStrategy()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {request.strategy}")
    
    try:
        # Run backtest
        engine = BacktestEngine(initial_cash=request.initial_cash)
        
        start_date = datetime.fromisoformat(request.start_date) if request.start_date else None
        end_date = datetime.fromisoformat(request.end_date) if request.end_date else None
        
        results = engine.run(
            data=df,
            symbol=request.symbol,
            strategy_fn=strat.generate_signal,
            start_date=start_date,
            end_date=end_date
        )
        
        # Ensure all values are serializable
        for key in results:
            if results[key] is None:
                results[key] = 0
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")
