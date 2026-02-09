"""Node for multi-agent debate protocol in LangGraph workflow."""

import asyncio
import time
from typing import Literal

from src.trading_graph.state import TradingState
from src.trading_graph.types import DebateProtocolOutput
from src.trading_graph.agents.debate_agents import BullAgent, BearAgent, JudgeAgent
from src.trading_graph.observability import cost_tracker, log_debate_result
from src.config import settings

import logging

logger = logging.getLogger(__name__)


def should_debate(state: TradingState) -> Literal["debate", "skip_debate"]:
    """Determine if debate should run based on config."""
    if settings.debate_trigger_mode == "always":
        return "debate"

    if settings.debate_trigger_mode == "high_confidence":
        return "debate" if state.get("confidence", 0) > settings.debate_confidence_threshold else "skip_debate"

    tech = state.get("technical_signals", {})
    sent = state.get("sentiment_signals", {})

    if tech and sent:
        tech_decision = tech.get("decision") or tech.get("data", {}).get("decision")
        sent_decision = sent.get("decision") or sent.get("data", {}).get("sentiment")

        if tech_decision and sent_decision:
            tech_signal = 1 if tech_decision == "BUY" else -1 if tech_decision == "SELL" else 0
            sent_signal = 1 if sent_decision == "bullish" or sent_decision == "BUY" else -1 if sent_decision == "bearish" or sent_decision == "SELL" else 0

            if abs(tech_signal - sent_signal) >= settings.debate_min_signal_difference:
                return "debate"

    return "skip_debate"


async def debate_protocol(state: TradingState) -> DebateProtocolOutput:
    """
    Run Bull vs Bear debate and get judge decision.

    Only runs when technical and sentiment signals conflict.

    Args:
        state: Trading state with technical_signals, sentiment_signals, market_data

    Returns:
        State updates with debate_result
    """
    start_time = time.time()

    try:
        symbol = state.get("symbol")
        if not symbol or len(symbol) > 5:
            raise ValueError(f"Invalid symbol: {symbol}")

        technical_signals = state.get("technical_signals", {})
        sentiment_signals = state.get("sentiment_signals", {})

        if not technical_signals:
            raise ValueError("technical_signals required")
        if not sentiment_signals:
            raise ValueError("sentiment_signals required")

        bull_agent = BullAgent()
        bear_agent = BearAgent()
        judge_agent = JudgeAgent()
        
        # Prepare market data for agents
        market_data = {}
        if state.get("market_data"):
            market_data = state.get("market_data", {})
        
        # Get arguments from both sides (concurrently)
        bull_task = bull_agent.generate_arguments(
            symbol,
            technical_signals,
            sentiment_signals,
            market_data
        )
        
        bear_task = bear_agent.generate_arguments(
            symbol,
            technical_signals,
            sentiment_signals,
            market_data
        )
        
        bull_case, bear_case = await asyncio.gather(bull_task, bear_task)
        
        # Track costs for bull and bear agents
        cost_tracker.log_call("bull_agent")
        cost_tracker.log_call("bear_agent")
        
        # Judge evaluates both sides
        decision = await judge_agent.evaluate_debate(
            symbol,
            bull_case,
            bear_case,
            technical_signals,
            sentiment_signals
        )
        
        # Track cost for judge agent
        cost_tracker.log_call("judge_agent")
        
        execution_time = time.time() - start_time
        
        # Build debate result
        debate_result = {
            "bull": bull_case,
            "bear": bear_case,
            "winner": decision["winner"],
            "decision": decision,
            "timestamp": state.get("timestamp", ""),
            "execution_time": execution_time
        }
        
        # Log debate result for observability
        log_debate_result(
            symbol=symbol,
            bull_confidence=bull_case.get("confidence", 0.0),
            bear_confidence=bear_case.get("confidence", 0.0),
            winner=decision.get("winner", "unknown"),
            judge_reasoning=decision.get("reasoning", "")
        )
        
        logger.info(
            f"Debate completed for {symbol}: {decision['winner']} wins, "
            f"recommendation: {decision['recommendation']} (took {execution_time:.2f}s)"
        )
        
        return {
            "debate_result": debate_result,
            "current_node": "debate_protocol"
        }
        
    except Exception as e:
        logger.error(f"Debate protocol failed for {state.get('symbol')}: {e}")
        return {
            "error": f"Debate protocol failed: {str(e)}",
            "current_node": "debate_protocol"
        }
