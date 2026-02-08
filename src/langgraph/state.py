"""Trading state schema for LangGraph workflows."""

from typing_extensions import TypedDict, Annotated
from typing import Optional, Dict, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


def merge_dicts(left, right):
    """Merge two dictionaries, right takes precedence."""
    if left is None:
        return right or {}
    if right is None:
        return left
    return {**left, **right}


def merge_lists(left, right):
    """Merge two lists."""
    if left is None:
        return right or []
    if right is None:
        return left
    return left + right


class TradingState(TypedDict):
    """
    Shared state for all trading agents in LangGraph workflow.

    This state flows through all nodes in the graph and accumulates
    analysis results, decisions, and execution details.
    """

    # ===== Input Parameters =====
    symbol: str
    timeframe: str

    # ===== Market Data =====
    market_data: Annotated[dict, merge_dicts]
    technical_indicators: Annotated[dict, merge_dicts]

    # ===== Agent Signals =====
    technical_signals: Annotated[dict, merge_dicts]
    sentiment_signals: Annotated[dict, merge_dicts]
    risk_signals: Annotated[dict, merge_dicts]
    debate_result: Annotated[dict, merge_dicts]

    # ===== Decision =====
    final_decision: Annotated[dict, merge_dicts]
    final_action: Optional[Literal["BUY", "SELL", "HOLD"]]
    confidence: float

    # ===== Execution =====
    executed_trade: Annotated[dict, merge_dicts]
    order_id: Optional[str]

    # ===== Human Feedback =====
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # ===== Messages (for LLM interactions) =====
    messages: Annotated[list[BaseMessage], add_messages]

    # ===== Metadata =====
    timestamp: str
    workflow_id: str
    iteration: int
    current_node: Optional[str]

    # ===== Error Handling =====
    error: Optional[str]
    retry_count: int
