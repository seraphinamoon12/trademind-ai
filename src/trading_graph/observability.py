"""Enhanced LangSmith integration for TradeMind AI."""

import asyncio
import os
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime, timezone
from functools import wraps

from src.config import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from langchain_core.tracers import LangChainTracer

try:
    from langsmith import Client
    from langchain_core.tracers import LangChainTracer
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    logger.warning("LangSmith dependencies not installed. Install with: pip install langsmith langchain-core")


class LangSmithManager:
    """Manage LangSmith tracing and monitoring."""

    def __init__(self):
        self.enabled = settings.enable_langsmith and LANGSMITH_AVAILABLE
        self.api_key = settings.langsmith_api_key
        self.project = settings.langsmith_project

        if self.enabled and self.api_key:
            try:
                self.client = Client(api_key=self.api_key)
                self.tracer = LangChainTracer(
                    project_name=self.project
                )
                logger.info(f"LangSmith tracing enabled for project: {self.project}")
            except Exception as e:
                logger.error(f"Failed to initialize LangSmith: {e}")
                self.enabled = False
                self.client = None
                self.tracer = None
        else:
            self.client = None
            self.tracer = None

    def get_tracer(self) -> Optional[LangChainTracer]:
        """Get tracer for graph execution."""
        return self.tracer

    def create_run(self, name: str, inputs: Dict[str, Any]) -> Optional[str]:
        """Create a manual run for tracking."""
        if not self.client:
            return None

        try:
            run = self.client.create_run(
                name=name,
                run_type="chain",
                inputs=inputs,
                project_name=self.project
            )
            return run.id
        except Exception as e:
            logger.error(f"Failed to create LangSmith run: {e}")
            return None

    def update_run(self, run_id: str, outputs: Dict[str, Any], error: str = None):
        """Update run with outputs or error."""
        if not self.client or not run_id:
            return

        try:
            if error:
                self.client.update_run(
                    run_id=run_id,
                    error=error,
                    end_time=datetime.now(timezone.utc)
                )
            else:
                self.client.update_run(
                    run_id=run_id,
                    outputs=outputs,
                    end_time=datetime.now(timezone.utc)
                )
        except Exception as e:
            logger.error(f"Failed to update LangSmith run: {e}")

    def add_feedback(self, run_id: str, key: str, score: float, comment: str = None):
        """Add feedback to a run."""
        if not self.client or not run_id:
            return

        try:
            self.client.create_feedback(
                run_id=run_id,
                key=key,
                score=score,
                comment=comment
            )
        except Exception as e:
            logger.error(f"Failed to add feedback to LangSmith run: {e}")

    def trace_execution(
        self,
        symbol: str,
        action: str,
        confidence: float,
        reasoning: str,
        execution_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Trace a trade execution."""
        if not self.enabled:
            return

        trace_data = {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "reasoning": reasoning,
            "execution_time_seconds": execution_time,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

        logger.info(f"Trade execution trace: {trace_data}")
        return trace_data

    def trace_debate(
        self,
        symbol: str,
        bull_confidence: float,
        bear_confidence: float,
        winner: str,
        judge_reasoning: str
    ):
        """Trace a debate result."""
        if not self.enabled:
            return

        trace_data = {
            "symbol": symbol,
            "bull_confidence": bull_confidence,
            "bear_confidence": bear_confidence,
            "winner": winner,
            "judge_reasoning": judge_reasoning,
            "confidence_delta": abs(bull_confidence - bear_confidence),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Debate result trace: {trace_data}")
        return trace_data

    def trace_human_review(
        self,
        symbol: str,
        trade_id: str,
        approved: bool,
        feedback: str,
        response_time: float
    ):
        """Trace a human review decision."""
        if not self.enabled:
            return

        trace_data = {
            "symbol": symbol,
            "trade_id": trade_id,
            "approved": approved,
            "feedback": feedback,
            "response_time_seconds": response_time,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info(f"Human review trace: {trace_data}")
        return trace_data


# Global instance
langsmith_manager = LangSmithManager()


def get_langsmith_config() -> Optional[Dict[str, Any]]:
    """
    Get LangSmith configuration if enabled.

    Returns:
        Dict with LangSmith configuration or None if disabled
    """
    if not langsmith_manager.enabled:
        return None

    config = {
        "project_name": langsmith_manager.project,
        "enabled": True
    }

    if settings.langsmith_endpoint:
        config["endpoint"] = settings.langsmith_endpoint

    return config


def log_debate_result(
    symbol: str,
    bull_confidence: float,
    bear_confidence: float,
    winner: str,
    judge_reasoning: str
) -> None:
    """
    Log a debate result for LangSmith tracing.

    Args:
        symbol: Stock symbol
        bull_confidence: Bull agent confidence
        bear_confidence: Bear agent confidence
        winner: Winner of the debate (bull/bear)
        judge_reasoning: Judge's reasoning
    """
    langsmith_manager.trace_debate(
        symbol=symbol,
        bull_confidence=bull_confidence,
        bear_confidence=bear_confidence,
        winner=winner,
        judge_reasoning=judge_reasoning
    )


def log_human_review(
    symbol: str,
    trade_id: str,
    approved: bool,
    feedback: str,
    response_time: float
) -> None:
    """
    Log a human review decision for LangSmith tracing.

    Args:
        symbol: Stock symbol
        trade_id: Trade approval request ID
        approved: Whether trade was approved
        feedback: Human feedback
        response_time: Time taken for human review
    """
    langsmith_manager.trace_human_review(
        symbol=symbol,
        trade_id=trade_id,
        approved=approved,
        feedback=feedback,
        response_time=response_time
    )


class CostTracker:
    """
    Track actual API costs from responses.

    Useful for monitoring LLM API usage costs.
    """

    def __init__(self):
        """Initialize cost tracker with zero costs and counters."""
        self.total_cost = 0.0
        self.call_counts = {
            "bull_agent": 0,
            "bear_agent": 0,
            "judge_agent": 0,
            "sentiment_agent": 0
        }
        self.daily_costs = {}

    def record_llm_call(self, response: Dict, agent_type: str = "unknown") -> float:
        """
        Record cost from LLM API response.

        Args:
            response: LLM API response containing usage information
            agent_type: Type of agent making the call

        Returns:
            Cost in USD for this call
        """
        usage = response.get('usage', {}) if isinstance(response, dict) else {}

        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        input_cost = input_tokens * 0.07 / 1_000_000
        output_cost = output_tokens * 0.40 / 1_000_000
        total_cost = input_cost + output_cost

        today = datetime.now(timezone.utc).date()
        if today not in self.daily_costs:
            self.daily_costs[today] = []

        self.daily_costs[today].append({
            'type': 'llm',
            'agent_type': agent_type,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cost': total_cost,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        self.total_cost += total_cost

        if agent_type in self.call_counts:
            self.call_counts[agent_type] += 1
        else:
            self.call_counts[agent_type] = 1

        return total_cost

    def log_call(self, agent_type: str, response: Optional[Dict] = None):
        """
        Log an API call and update costs.

        Args:
            agent_type: Type of agent making the call
            response: Optional API response with usage data
        """
        if agent_type not in self.call_counts:
            logger.warning(f"Unknown agent type: {agent_type}")
            return

        if response:
            cost = self.record_llm_call(response, agent_type)
        else:
            self.call_counts[agent_type] += 1
            logger.warning(f"No response provided for {agent_type}, cost not calculated")

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost summary.

        Returns:
            Dictionary with total cost, call counts, and cost breakdown by date
        """
        return {
            "total_cost_usd": round(self.total_cost, 4),
            "call_counts": self.call_counts.copy(),
            "cost_by_date": {
                str(date): sum(call['cost'] for call in calls)
                for date, calls in self.daily_costs.items()
            }
        }

    def reset(self):
        """Reset cost tracker, clearing all costs and counters."""
        self.total_cost = 0.0
        for key in self.call_counts:
            self.call_counts[key] = 0
        self.daily_costs = {}


# Global cost tracker instance
cost_tracker = CostTracker()
