"""Agent API routes."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio

from src.core.database import get_db, AgentDecision
from src.data.ingestion import ingestion
from src.agents.technical import TechnicalAgent
from src.agents.risk import RiskAgent
from src.agents.sentiment import SentimentAgent
from src.agents.orchestrator import Orchestrator
from src.portfolio.manager import PortfolioManager
from src.config import settings

router = APIRouter()


@router.post("/analyze-batch")
async def analyze_batch(
    symbols: List[str] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Analyze multiple symbols concurrently (batch mode).

    This is the DEFAULT and RECOMMENDED way to analyze stocks.
    7x faster than sequential analysis by running all agents in parallel.

    Args:
        symbols: List of stock symbols to analyze (e.g., ["AAPL", "TSLA", "NVDA"])

    Returns:
        Dictionary with results for all symbols
    """
    if not symbols:
        raise HTTPException(status_code=400, detail="No symbols provided")

    if len(symbols) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed per batch")

    # Get portfolio context once (shared across all analyses)
    pm = PortfolioManager()
    portfolio = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)

    # Run all analyses concurrently
    tasks = [
        _analyze_single_symbol(sym, portfolio, holdings, db)
        for sym in symbols
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    successful = []
    errors = []

    for symbol, result in zip(symbols, results):
        if isinstance(result, Exception):
            errors.append({"symbol": symbol, "error": str(result)})
        else:
            successful.append(result)

    return {
        "batch_size": len(symbols),
        "successful": len(successful),
        "errors": len(errors),
        "results": successful,
        "error_details": errors if errors else None
    }


async def _analyze_single_symbol(
    symbol: str,
    portfolio: dict,
    holdings: list,
    db: Session
) -> dict:
    """Analyze a single symbol (helper for batch)."""
    # Get data
    df = ingestion.get_stored_data(symbol, days=365, db=db)

    if df is None:
        ingestion.ingest_symbol(symbol, db=db)
        df = ingestion.get_stored_data(symbol, days=365, db=db)

    if df is None or df.empty:
        raise Exception(f"No data for {symbol}")

    # Run agents concurrently
    agents_tasks = []

    # Technical Agent
    technical_agent = TechnicalAgent()
    agents_tasks.append(technical_agent.analyze(symbol, df))

    # Risk Agent
    risk_agent = RiskAgent()
    agents_tasks.append(risk_agent.analyze(
        symbol, df,
        portfolio_value=portfolio['total_value'],
        current_holdings=holdings
    ))

    # Sentiment Agent (if enabled)
    if settings.sentiment_enabled:
        sentiment_agent = SentimentAgent()
        agents_tasks.append(sentiment_agent.analyze(symbol, df))

    # Wait for all agents
    signals = await asyncio.gather(*agents_tasks)

    # Log decisions
    pm = PortfolioManager()
    for signal in signals:
        pm.log_agent_decision(
            symbol=symbol,
            agent=signal.agent_name,
            decision=signal.decision.value,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            data=signal.data,
            db=db
        )

    # Combine with orchestrator
    orchestrator = Orchestrator()
    latest_price = float(df['close'].iloc[-1])

    final_decision = orchestrator.decide(
        symbol=symbol,
        signals=signals,
        portfolio_value=portfolio['total_value'],
        current_price=latest_price
    )

    return {
        "symbol": symbol,
        "current_price": latest_price,
        "final_decision": final_decision.to_dict(),
        "agent_signals": [
            {
                "agent": s.agent_name,
                "decision": s.decision.value,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in final_decision.agent_signals
        ]
    }


@router.get("/decisions")
async def get_decisions(
    symbol: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get agent decision history."""
    query = db.query(AgentDecision)
    
    if symbol:
        query = query.filter(AgentDecision.symbol == symbol.upper())
    if agent:
        query = query.filter(AgentDecision.agent == agent)
    
    decisions = query.order_by(AgentDecision.timestamp.desc()).limit(limit).all()
    
    return {
        "decisions": [
            {
                "id": d.id,
                "timestamp": d.timestamp.isoformat(),
                "symbol": d.symbol,
                "agent": d.agent,
                "decision": d.decision,
                "confidence": float(d.confidence) if d.confidence else None,
                "reasoning": d.reasoning,
                "data": d.data
            }
            for d in decisions
        ]
    }


@router.post("/analyze/{symbol}")
async def analyze_symbol(
    symbol: str,
    db: Session = Depends(get_db)
):
    """
    Run all agents on a single symbol.

    ⚠️ DEPRECATED: Use /analyze-batch for better performance.
    Single-symbol analysis is 7x slower than batch mode.
    """
    # Get data
    df = ingestion.get_stored_data(symbol, days=365, db=db)
    
    if df is None:
        ingestion.ingest_symbol(symbol, db=db)
        df = ingestion.get_stored_data(symbol, days=365, db=db)
    
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    
    # Get portfolio context
    pm = PortfolioManager()
    portfolio = pm.get_portfolio_value(db)
    holdings = pm.get_holdings(db)
    
    # Run agents
    signals = []
    
    # Technical Agent
    technical_agent = TechnicalAgent()
    technical_signal = await technical_agent.analyze(symbol, df)
    signals.append(technical_signal)
    
    # Risk Agent
    risk_agent = RiskAgent()
    risk_signal = await risk_agent.analyze(
        symbol, df,
        portfolio_value=portfolio['total_value'],
        current_holdings=holdings
    )
    signals.append(risk_signal)
    
    # Sentiment Agent (if enabled)
    if settings.sentiment_enabled:
        sentiment_agent = SentimentAgent()
        sentiment_signal = await sentiment_agent.analyze(symbol, df)
        signals.append(sentiment_signal)
    
    # Log all decisions
    for signal in signals:
        pm.log_agent_decision(
            symbol=symbol,
            agent=signal.agent_name,
            decision=signal.decision.value,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            data=signal.data,
            db=db
        )
    
    # Combine with orchestrator
    orchestrator = Orchestrator()
    latest_price = float(df['close'].iloc[-1])
    
    final_decision = orchestrator.decide(
        symbol=symbol,
        signals=signals,
        portfolio_value=portfolio['total_value'],
        current_price=latest_price
    )
    
    return {
        "symbol": symbol,
        "current_price": latest_price,
        "final_decision": final_decision.to_dict(),
        "agent_signals": [
            {
                "agent": s.agent_name,
                "decision": s.decision.value,
                "confidence": s.confidence,
                "reasoning": s.reasoning
            }
            for s in final_decision.agent_signals
        ]
    }
