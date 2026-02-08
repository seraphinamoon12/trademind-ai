"""Agent API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from src.core.database import get_db, AgentDecision
from src.data.ingestion import ingestion
from src.agents.technical import TechnicalAgent
from src.agents.risk import RiskAgent
from src.agents.sentiment import SentimentAgent
from src.agents.orchestrator import Orchestrator
from src.portfolio.manager import PortfolioManager
from src.config import settings

router = APIRouter()


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
    """Run all agents on a symbol and get combined decision."""
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
