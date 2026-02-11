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
    execution_time: float
    error: Optional[str]


class TechnicalAnalysisOutput(TypedDict, total=False):
    """Output type for technical_analysis node."""
    technical_signals: dict
    current_node: str
    execution_time: float
    error: Optional[str]


class SentimentAnalysisOutput(TypedDict, total=False):
    """Output type for sentiment_analysis node."""
    sentiment_signals: dict
    current_node: str
    execution_time: float
    error: Optional[str]


class MarketMoodOutput(TypedDict, total=False):
    """Output type for market_mood_analysis node."""
    market_mood_data: dict
    market_mood_signals: dict
    mood_indicators: dict
    position_sizing_adjustment: dict
    risk_adjustments: dict
    mood_adjusted_signals: dict
    current_node: str
    execution_time: float
    error: Optional[str]


class RiskAssessmentOutput(TypedDict, total=False):
    """Output type for risk_assessment node."""
    risk_signals: dict
    current_node: str
    execution_time: float
    error: Optional[str]


class DebateProtocolOutput(TypedDict, total=False):
    """Output type for debate_protocol node."""
    debate_result: dict
    current_node: str
    execution_time: float
    error: Optional[str]


class MakeDecisionOutput(TypedDict, total=False):
    """Output type for make_decision node."""
    final_decision: dict
    final_action: str
    confidence: float
    current_node: str
    execution_time: float
    error: Optional[str]


class HumanReviewOutput(TypedDict, total=False):
    """Output type for human_review node."""
    human_approved: bool
    human_feedback: str
    current_node: str
    execution_time: float
    error: Optional[str]


class ExecuteTradeOutput(TypedDict, total=False):
    """Output type for execute_trade node."""
    executed_trade: dict
    order_id: Optional[str]
    execution_status: str
    execution_time: float
    current_node: str
    error: Optional[str]


class RetryOutput(TypedDict, total=False):
    """Output type for retry node."""
    iteration: int
    retry_count: int
    current_node: str
    execution_time: float
    error: Optional[str]


class EndOutput(TypedDict, total=False):
    """Output type for end node."""
    current_node: str
    execution_time: float
    error: Optional[str]
