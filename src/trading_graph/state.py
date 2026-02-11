"""Trading state schema for LangGraph workflows."""

import sys
from typing_extensions import TypedDict, Annotated
from typing import Optional, Dict, Any, Literal, List, Tuple
from langchain_core.messages import BaseMessage
from dataclasses import dataclass
from datetime import datetime

# Helper to import add_messages from system langgraph (avoid shadowing)
def _import_add_messages():
    """Import add_messages from system langgraph package."""
    if 'src.langgraph' in sys.modules:
        src_langgraph = sys.modules.pop('src.langgraph')
        try:
            from langgraph.graph import add_messages
            return add_messages
        finally:
            sys.modules['src.langgraph'] = src_langgraph
    else:
        from langgraph.graph import add_messages
        return add_messages

add_messages = _import_add_messages()


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


def overwrite_with_right(left, right):
    """Overwrite left value with right value (right takes precedence)."""
    return right if right is not None else left


class TradingState(TypedDict, total=False):
    """
    Shared state for all trading agents in LangGraph workflow.

    This state flows through all nodes in the graph and accumulates
    analysis results, decisions, and execution details.
    
    Note: total=False makes all fields optional for initialization.
    """

    # ===== Input Parameters =====
    symbol: str
    timeframe: str

    # ===== Portfolio & Positions =====
    positions: Annotated[dict, merge_dicts]
    portfolio_value: float
    cash_balance: float
    position_entry_prices: Annotated[dict, merge_dicts]
    sector_exposure: Annotated[dict, merge_dicts]

    # ===== Market Data =====
    market_data: Annotated[dict, merge_dicts]
    technical_indicators: Annotated[dict, merge_dicts]

    # ===== Agent Signals =====
    technical_signals: Annotated[dict, merge_dicts]
    sentiment_signals: Annotated[dict, merge_dicts]
    risk_signals: Annotated[dict, merge_dicts]
    debate_result: Annotated[dict, merge_dicts]
    market_mood_data: Annotated[dict, merge_dicts]
    market_mood_signals: Annotated[dict, merge_dicts]
    mood_indicators: Annotated[dict, merge_dicts]
    position_sizing_adjustment: Annotated[dict, merge_dicts]
    risk_adjustments: Annotated[dict, merge_dicts]
    mood_adjusted_signals: Annotated[dict, merge_dicts]

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
    current_node: Annotated[Optional[str], overwrite_with_right]

    # ===== Error Handling =====
    error: Annotated[Optional[str], overwrite_with_right]
    retry_count: int
