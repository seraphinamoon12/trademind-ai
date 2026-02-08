"""Type definitions for LangGraph node outputs."""

from typing import TypedDict, Optional


class FetchMarketDataOutput(TypedDict, total=False):
    """Output type for fetch_market_data node."""
    market_data: dict
    technical_indicators: dict
    timestamp: str
    workflow_id: str
    iteration: int
    current_node: str
    error: str


class TechnicalAnalysisOutput(TypedDict, total=False):
    """Output type for technical_analysis node."""
    technical_signals: dict
    current_node: str
    error: str


class SentimentAnalysisOutput(TypedDict, total=False):
    """Output type for sentiment_analysis node."""
    sentiment_signals: dict
    current_node: str
    error: str


class RiskAssessmentOutput(TypedDict, total=False):
    """Output type for risk_assessment node."""
    risk_signals: dict
    current_node: str
    error: str


class DebateProtocolOutput(TypedDict, total=False):
    """Output type for debate_protocol node."""
    debate_result: dict
    current_node: str
    error: str


class MakeDecisionOutput(TypedDict, total=False):
    """Output type for make_decision node."""
    final_decision: dict
    final_action: str
    confidence: float
    current_node: str
    error: str


class HumanReviewOutput(TypedDict, total=False):
    """Output type for human_review node."""
    human_approved: bool
    human_feedback: str
    current_node: str
    error: str


class ExecuteTradeOutput(TypedDict, total=False):
    """Output type for execute_trade node."""
    executed_trade: dict
    order_id: str
    current_node: str
    error: str


class RetryOutput(TypedDict, total=False):
    """Output type for retry node."""
    iteration: int
    retry_count: int
    current_node: str
    error: str


class EndOutput(TypedDict, total=False):
    """Output type for end node."""
    current_node: str
    error: str
