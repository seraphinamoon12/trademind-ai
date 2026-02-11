"""Market Mood node for LangGraph workflow."""

import time
from typing import Dict, Any

from src.trading_graph.state import TradingState
from src.trading_graph.types import MarketMoodOutput
from src.market_mood.detector import MarketMoodDetector
from src.config import settings


async def market_mood_analysis(state: TradingState) -> MarketMoodOutput:
    """
    Perform market mood analysis using MarketMoodDetector.

    Fetches current market mood, adjusts trading signals based on mood,
    and provides mood context to other nodes.

    Args:
        state: Trading state

    Returns:
        State updates with market_mood_data, mood_adjusted_signals
    """
    start_time = time.time()

    try:
        symbol = state.get("symbol", "MARKET")

        if not settings.market_mood_enabled:
            elapsed = time.time() - start_time
            return {
                "error": "Market mood detection is disabled",
                "current_node": "market_mood_analysis",
                "execution_time": elapsed
            }

        detector = MarketMoodDetector()

        mood_data = detector.get_current_mood(refresh=False)
        trading_signals = detector.get_trading_signals(refresh=False)

        indicator_scores = detector.get_indicator_scores()

        position_sizing = detector.get_position_sizing_suggestion()
        risk_adjustments = detector.get_risk_adjustments()

        mood_adjusted_signals = _apply_mood_adjustments(
            state.get("technical_signals", {}),
            state.get("sentiment_signals", {}),
            trading_signals,
            position_sizing,
            risk_adjustments
        )

        elapsed = time.time() - start_time
        return {
            "market_mood_data": {
                "composite_score": mood_data.get("composite_score", 0.0),
                "normalized_score": mood_data.get("normalized_score", 0.0),
                "trend": mood_data.get("trend", "stable"),
                "confidence": mood_data.get("confidence", 0.0),
                "valid_indicators": mood_data.get("valid_indicators", []),
                "missing_indicators": mood_data.get("missing_indicators", []),
                "indicator_details": mood_data.get("indicator_details", {}),
                "timestamp": mood_data.get("timestamp"),
            },
            "market_mood_signals": {
                "signal": trading_signals.get("signal", "NO_SIGNAL"),
                "mood_classification": trading_signals.get("mood_classification", "neutral"),
                "confidence": trading_signals.get("confidence", 0.0),
                "recommendations": trading_signals.get("recommendations", []),
                "timestamp": trading_signals.get("timestamp"),
            },
            "mood_indicators": indicator_scores,
            "position_sizing_adjustment": position_sizing,
            "risk_adjustments": risk_adjustments,
            "mood_adjusted_signals": mood_adjusted_signals,
            "current_node": "market_mood_analysis",
            "execution_time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error": f"Market mood analysis failed: {str(e)}",
            "current_node": "market_mood_analysis",
            "execution_time": elapsed
        }


def _apply_mood_adjustments(
    technical_signals: Dict[str, Any],
    sentiment_signals: Dict[str, Any],
    market_mood_signals: Dict[str, Any],
    position_sizing: Dict[str, Any],
    risk_adjustments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply market mood adjustments to trading signals.

    Adjusts position sizes and risk parameters based on market mood.

    Args:
        technical_signals: Technical analysis signals
        sentiment_signals: Sentiment analysis signals
        market_mood_signals: Market mood trading signals
        position_sizing: Position sizing suggestions
        risk_adjustments: Risk adjustment suggestions

    Returns:
        Dictionary with mood-adjusted signals
    """
    mood_classification = market_mood_signals.get("mood_classification", "neutral")
    mood_signal = market_mood_signals.get("signal", "NO_SIGNAL")

    adjusted_signals = {
        "original_technical": technical_signals,
        "original_sentiment": sentiment_signals,
        "mood_classification": mood_classification,
        "mood_signal": mood_signal,
        "position_size_multiplier": _get_position_size_multiplier(mood_classification),
        "stop_loss_adjustment": risk_adjustments.get("stop_loss_pct"),
        "take_profit_adjustment": risk_adjustments.get("take_profit_pct"),
        "max_position_adjustment": risk_adjustments.get("max_position_pct"),
        "risk_level": risk_adjustments.get("risk_level", "moderate"),
    }

    return adjusted_signals


def _get_position_size_multiplier(mood_classification: str) -> float:
    """
    Get position size multiplier based on mood classification.

    Logic:
    - Extreme Fear (< -70): Increase position size by 50%
    - Fear (-70 to -30): Increase position size by 25%
    - Neutral (-30 to +30): Normal trading
    - Greed (+30 to +70): Decrease position size by 25%
    - Extreme Greed (> +70): Skip trading or reduce by 50%

    Args:
        mood_classification: Mood classification string

    Returns:
        Position size multiplier
    """
    multipliers = {
        "extreme_fear": 1.5,
        "fear": 1.25,
        "neutral": 1.0,
        "greed": 0.75,
        "extreme_greed": 0.5,
    }

    return multipliers.get(mood_classification, 1.0)


def should_skip_trading(mood_classification: str) -> bool:
    """
    Determine if trading should be skipped based on extreme conditions.

    Args:
        mood_classification: Mood classification string

    Returns:
        True if trading should be skipped
    """
    return mood_classification == "extreme_greed"


def get_mood_context(mood_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get mood context for other nodes in the graph.

    Args:
        mood_data: Market mood data

    Returns:
        Simplified mood context
    """
    return {
        "classification": mood_data.get("mood_classification", "neutral"),
        "signal": mood_data.get("signal", "NO_SIGNAL"),
        "confidence": mood_data.get("confidence", 0.0),
        "composite_score": mood_data.get("composite_score", 0.0),
        "trend": mood_data.get("trend", "stable"),
    }
