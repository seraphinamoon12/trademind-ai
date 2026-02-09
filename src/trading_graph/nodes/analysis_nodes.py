"""Nodes for technical, sentiment, and decision analysis in LangGraph workflow."""

import time
import pandas as pd

from src.trading_graph.state import TradingState
from src.trading_graph.types import TechnicalAnalysisOutput, SentimentAnalysisOutput, MakeDecisionOutput
from src.agents.technical import TechnicalAgent
from src.agents.sentiment import SentimentAgent
from src.config import settings
from src.core.serialization import convert_numpy_types


async def technical_analysis(state: TradingState) -> TechnicalAnalysisOutput:
    """
    Perform technical analysis using TechnicalAgent.

    Integrates RSI and MACD strategies from existing TechnicalAgent.

    Args:
        state: Trading state with market_data and technical_indicators

    Returns:
        State updates with technical_signals
    """
    start_time = time.time()

    try:
        symbol = state["symbol"]
        market_data_dict = state.get("market_data", {})

        if not market_data_dict:
            elapsed = time.time() - start_time
            return {
                "error": "No market data available for technical analysis",
                "current_node": "technical_analysis",
                "execution_time": elapsed
            }

        data = pd.DataFrame(market_data_dict)
        if data.empty:
            elapsed = time.time() - start_time
            return {
                "error": "Market data is empty",
                "current_node": "technical_analysis",
                "execution_time": elapsed
            }

        tech_agent = TechnicalAgent()
        signal = await tech_agent.analyze(symbol, data)

        technical_signals = {
            "decision": signal.decision.value,
            "confidence": float(signal.confidence),
            "reasoning": signal.reasoning,
            "agent_name": signal.agent_name,
            "data": convert_numpy_types(signal.data or {})
        }

        elapsed = time.time() - start_time
        return {
            "technical_signals": technical_signals,
            "current_node": "technical_analysis",
            "execution_time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error": f"Technical analysis failed: {str(e)}",
            "current_node": "technical_analysis",
            "execution_time": elapsed
        }
        
        # Convert dict back to DataFrame
        data = pd.DataFrame(market_data_dict)
        if data.empty:
            return {
                "error": "Market data is empty",
                "current_node": "technical_analysis"
            }
        
        # Initialize TechnicalAgent
        tech_agent = TechnicalAgent()
        
        # Analyze
        signal = await tech_agent.analyze(symbol, data)
        
        # Convert AgentSignal to technical_signals format
        technical_signals = {
            "decision": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "agent_name": signal.agent_name,
            "data": signal.data or {}
        }
        
        return {
            "technical_signals": technical_signals,
            "current_node": "technical_analysis"
        }
        
    except Exception as e:
        return {
            "error": f"Technical analysis failed: {str(e)}",
            "current_node": "technical_analysis"
        }


async def sentiment_analysis(state: TradingState) -> SentimentAnalysisOutput:
    """
    Perform sentiment analysis using SentimentAgent with ZAI GLM-4.7 Flash.

    Uses GLM-4.7 Flash model for cost efficiency (30-minute cache).
    Falls back to rule-based analysis if API unavailable.

    Args:
        state: Trading state with market_data

    Returns:
        State updates with sentiment_signals
    """
    start_time = time.time()

    try:
        symbol = state["symbol"]
        market_data_dict = state.get("market_data", {})

        if not market_data_dict:
            elapsed = time.time() - start_time
            return {
                "error": "No market data available for sentiment analysis",
                "current_node": "sentiment_analysis",
                "execution_time": elapsed
            }

        data = pd.DataFrame(market_data_dict)
        if data.empty:
            elapsed = time.time() - start_time
            return {
                "error": "Market data is empty",
                "current_node": "sentiment_analysis",
                "execution_time": elapsed
            }

        sentiment_agent = SentimentAgent()
        signal = await sentiment_agent.analyze(symbol, data)

        sentiment_signals = {
            "decision": signal.decision.value,
            "confidence": float(signal.confidence),
            "reasoning": signal.reasoning,
            "agent_name": signal.agent_name,
            "data": convert_numpy_types(signal.data or {})
        }

        elapsed = time.time() - start_time
        return {
            "sentiment_signals": sentiment_signals,
            "current_node": "sentiment_analysis",
            "execution_time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error": f"Sentiment analysis failed: {str(e)}",
            "current_node": "sentiment_analysis",
            "execution_time": elapsed
        }


async def make_decision(state: TradingState) -> MakeDecisionOutput:
    """
    Combine signals from technical, sentiment, and risk using weighted voting.

    Weight distribution:
    - Technical: 40%
    - Sentiment: 30%
    - Risk: 30%

    Args:
        state: Trading state with technical_signals, sentiment_signals, risk_signals

    Returns:
        State updates with final_decision, final_action, confidence
    """
    start_time = time.time()

    try:
        technical = state.get("technical_signals", {})
        sentiment = state.get("sentiment_signals", {})
        risk = state.get("risk_signals", {})

        if not technical or not sentiment:
            elapsed = time.time() - start_time
            return {
                "error": "Missing required signals for decision",
                "current_node": "make_decision",
                "execution_time": elapsed
            }

        tech_weight = settings.technical_weight
        sentiment_weight = settings.sentiment_weight
        risk_weight = settings.risk_weight

        total_weight = tech_weight + sentiment_weight
        if risk:
            total_weight += risk_weight

        votes = {
            "BUY": 0.0,
            "SELL": 0.0,
            "HOLD": 0.0
        }

        tech_decision = technical.get("decision", "HOLD")
        tech_confidence = technical.get("confidence", 0.0)
        if tech_decision in votes:
            votes[tech_decision] += tech_confidence * tech_weight

        sent_decision = sentiment.get("decision", "HOLD")
        sent_confidence = sentiment.get("confidence", 0.0)
        if sent_decision in votes:
            votes[sent_decision] += sent_confidence * sentiment_weight

        if risk and risk.get("decision") == "VETO":
            final_decision = {
                "decision": "HOLD",
                "confidence": 0.95,
                "reasoning": f"Risk veto: {risk.get('reasoning', 'Risk check failed')}",
                "breakdown": {
                    "technical": technical,
                    "sentiment": sentiment,
                    "risk": risk
                }
            }

            elapsed = time.time() - start_time
            return {
                "final_decision": final_decision,
                "final_action": "HOLD",
                "confidence": 0.95,
                "current_node": "make_decision",
                "execution_time": elapsed
            }
        elif risk:
            risk_decision = risk.get("decision", "HOLD")
            risk_confidence = risk.get("confidence", 0.0)
            if risk_decision in votes:
                votes[risk_decision] += risk_confidence * risk_weight

        max_vote = max(votes.values())
        final_action = max(votes, key=lambda k: votes[k])

        confidence = min(max_vote / total_weight, 1.0) if total_weight > 0 else 0.0

        reasoning_parts = []

        if technical:
            tech_part = f"Technical: {technical.get('decision', 'HOLD')} ({technical.get('confidence', 0.0):.2f})"
            reasoning_parts.append(tech_part)

        if sentiment:
            sent_part = f"Sentiment: {sentiment.get('decision', 'HOLD')} ({sentiment.get('confidence', 0.0):.2f})"
            reasoning_parts.append(sent_part)

        if risk and risk.get("decision") != "VETO":
            risk_part = f"Risk: {risk.get('decision', 'HOLD')} ({risk.get('confidence', 0.0):.2f})"
            reasoning_parts.append(risk_part)

        final_reasoning = f"Weighted voting ({final_action}): {'; '.join(reasoning_parts)}"

        final_decision = {
            "decision": final_action,
            "confidence": confidence,
            "reasoning": final_reasoning,
            "breakdown": {
                "technical": technical,
                "sentiment": sentiment,
                "risk": risk
            },
            "votes": votes,
            "weights": {
                "technical": tech_weight,
                "sentiment": sentiment_weight,
                "risk": risk_weight
            }
        }

        elapsed = time.time() - start_time
        return {
            "final_decision": final_decision,
            "final_action": final_action,
            "confidence": confidence,
            "current_node": "make_decision",
            "execution_time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error": f"Decision making failed: {str(e)}",
            "current_node": "make_decision",
            "execution_time": elapsed
        }
