"""Trading state schema for LangGraph workflows."""

from typing_extensions import TypedDict, Annotated
from typing import Optional, Dict, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


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
    market_data: Optional[Dict[str, Any]]
    technical_indicators: Optional[Dict[str, Any]]

    # ===== Agent Signals =====
    technical_signals: Optional[Dict[str, Any]]
    sentiment_signals: Optional[Dict[str, Any]]
    risk_signals: Optional[Dict[str, Any]]
    debate_result: Optional[Dict[str, Any]]

    # ===== Decision =====
    final_decision: Optional[Dict[str, Any]]
    final_action: Optional[Literal["BUY", "SELL", "HOLD"]]
    confidence: float

    # ===== Execution =====
    executed_trade: Optional[Dict[str, Any]]
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
