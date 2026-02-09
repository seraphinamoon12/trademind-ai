"""Node for human-in-the-loop review in LangGraph workflow."""

import asyncio
import uuid
import time
from datetime import datetime, timezone

from src.trading_graph.state import TradingState
from src.trading_graph.types import HumanReviewOutput
from src.trading_graph.observability import log_human_review
from src.config import settings
from src.api.routes.human_review import create_trade_approval_request, await_trade_approval

import logging

logger = logging.getLogger(__name__)


async def human_review(state: TradingState) -> HumanReviewOutput:
    """
    Human-in-the-loop approval with WebSocket notification.
    
    Only triggers when confidence is below threshold.
    
    Args:
        state: Trading state with final_action, confidence
        
    Returns:
        State updates with human_approved and human_feedback
    """
    start_time = time.time()
    
    try:
        confidence = state.get("confidence", 0.0)
        threshold = getattr(settings, 'human_review_threshold', 0.75)
        
        # Auto-approve high confidence trades
        if confidence >= threshold:
            logger.info(
                f"Auto-approving trade for {state['symbol']} "
                f"(confidence: {confidence:.2f} >= threshold: {threshold})"
            )
            return {
                "human_approved": True,
                "human_feedback": "Auto-approved (high confidence)",
                "current_node": "human_review"
            }
        
        # Low confidence - require human review
        logger.info(
            f"Requesting human review for {state['symbol']} "
            f"(confidence: {confidence:.2f} < threshold: {threshold})"
        )
        
        symbol = state["symbol"]
        final_action = state.get("final_action", "HOLD")
        final_decision = state.get("final_decision", {})
        
        # Create trade approval request
        trade_id = await create_trade_approval_request(
            symbol=symbol,
            action=final_action,
            confidence=confidence,
            reasoning=final_decision.get("reasoning", ""),
            technical_signals=state.get("technical_signals", {}),
            sentiment_signals=state.get("sentiment_signals", {}),
            debate_result=state.get("debate_result", {})
        )
        
        # Wait for human decision (with timeout)
        timeout = 300  # 5 minutes
        
        logger.info(f"Waiting for human approval for trade {trade_id} (timeout: {timeout}s)")
        
        result = await await_trade_approval(trade_id, timeout=timeout)
        
        approved = result.get("approved", False)
        feedback = result.get("feedback", "")
        
        response_time = time.time() - start_time
        
        # Log human review for observability
        log_human_review(
            symbol=symbol,
            trade_id=trade_id,
            approved=approved,
            feedback=feedback,
            response_time=response_time
        )
        
        logger.info(
            f"Trade {trade_id} {'approved' if approved else 'rejected'} "
            f"by human in {response_time:.2f}s: {feedback}"
        )
        
        return {
            "human_approved": approved,
            "human_feedback": feedback,
            "current_node": "human_review"
        }
        
    except Exception as e:
        logger.error(f"Human review failed for {state.get('symbol')}: {e}")
        # On error, reject the trade for safety
        return {
            "human_approved": False,
            "human_feedback": f"Human review error: {str(e)}",
            "current_node": "human_review"
        }
