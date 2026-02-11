"""Market Mood Integration for Auto-Trader.

Provides integration between market mood detection and auto-trading system.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from src.market_mood.detector import MarketMoodDetector
from src.market_mood.signals import SignalGenerator
from src.config import settings

logger = logging.getLogger(__name__)


class MarketMoodAutoTraderIntegration:
    """
    Integration between Market Mood Detection and Auto-Trader.

    Features:
    - Check market mood before placing orders
    - Adjust position sizes based on mood
    - Skip trading in extreme conditions
    - Log mood data with trades
    """

    def __init__(self, detector: Optional[MarketMoodDetector] = None):
        """
        Initialize the auto-trader integration.

        Args:
            detector: MarketMoodDetector instance. If None, creates one.
        """
        self.detector = detector or MarketMoodDetector()
        self.signal_generator = SignalGenerator()
        self.enabled = getattr(settings, 'market_mood_enabled', True)

    def should_trade(self, mood_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Determine if trading should proceed based on market mood.

        Args:
            mood_data: Optional mood data. If None, fetches current mood.

        Returns:
            Tuple of (should_trade, reason, mood_context)
        """
        if not self.enabled:
            return True, "Market mood integration disabled", {}

        try:
            if mood_data is None:
                mood_data = self.detector.get_current_mood(refresh=False)

            if not mood_data:
                return True, "No mood data available, proceeding with caution", {}

            trading_signals = self.detector.get_trading_signals(refresh=False)
            mood_classification = trading_signals.get("mood_classification", "neutral")

            mood_context = {
                "classification": mood_classification,
                "composite_score": mood_data.get("composite_score", 0.0),
                "confidence": mood_data.get("confidence", 0.0),
                "signal": trading_signals.get("signal", "NO_SIGNAL"),
                "timestamp": datetime.utcnow().isoformat(),
            }

            if self._should_skip_trading(mood_classification):
                reason = f"Skipping trade due to {mood_classification} market condition"
                return False, reason, mood_context

            reason = f"Trading allowed: {mood_classification} market condition"
            return True, reason, mood_context

        except Exception as e:
            logger.error(f"Error checking trade conditions: {e}")
            return True, "Error checking mood data, proceeding with caution", {}

    def _should_skip_trading(self, mood_classification: str) -> bool:
        """
        Determine if trading should be skipped based on mood.

        Extreme Greed (> +70): Skip trading

        Args:
            mood_classification: Mood classification string

        Returns:
            True if trading should be skipped
        """
        skip_conditions = getattr(settings, 'market_mood_skip_conditions', [])
        return mood_classification in skip_conditions or mood_classification == "extreme_greed"

    def get_adjusted_position_size(
        self,
        base_quantity: int,
        mood_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Get position size adjusted based on market mood.

        Logic:
        - Extreme Fear (< -70): Increase position size by 50%
        - Fear (-70 to -30): Increase position size by 25%
        - Neutral (-30 to +30): Normal trading
        - Greed (+30 to +70): Decrease position size by 25%
        - Extreme Greed (> +70): Skip trading or reduce by 50%

        Args:
            base_quantity: Base position quantity
            mood_data: Optional mood data. If None, fetches current mood.

        Returns:
            Tuple of (adjusted_quantity, adjustment_info)
        """
        if not self.enabled:
            return base_quantity, {"multiplier": 1.0, "reason": "Market mood integration disabled"}

        try:
            if mood_data is None:
                mood_data = self.detector.get_current_mood(refresh=False)

            trading_signals = self.detector.get_trading_signals(refresh=False)
            mood_classification = trading_signals.get("mood_classification", "neutral")

            multiplier = self._get_position_size_multiplier(mood_classification)
            adjusted_quantity = int(base_quantity * multiplier)

            adjustment_info = {
                "base_quantity": base_quantity,
                "adjusted_quantity": adjusted_quantity,
                "multiplier": multiplier,
                "mood_classification": mood_classification,
                "reason": self._get_multiplier_reason(mood_classification),
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Position size adjusted: {base_quantity} -> {adjusted_quantity} "
                f"(multiplier: {multiplier:.2f}, mood: {mood_classification})"
            )

            return adjusted_quantity, adjustment_info

        except Exception as e:
            logger.error(f"Error adjusting position size: {e}")
            return base_quantity, {
                "multiplier": 1.0,
                "reason": f"Error adjusting size: {str(e)}",
            }

    def _get_position_size_multiplier(self, mood_classification: str) -> float:
        """
        Get position size multiplier based on mood classification.

        Args:
            mood_classification: Mood classification string

        Returns:
            Position size multiplier
        """
        multipliers = getattr(settings, 'market_mood_position_multipliers', {})
        return multipliers.get(
            mood_classification,
            {
                "extreme_fear": 1.5,
                "fear": 1.25,
                "neutral": 1.0,
                "greed": 0.75,
                "extreme_greed": 0.5,
            }.get(mood_classification, 1.0)
        )

    def _get_multiplier_reason(self, mood_classification: str) -> str:
        """Get human-readable reason for position size adjustment."""
        reasons = {
            "extreme_fear": "Extreme fear - increasing position size by 50%",
            "fear": "Fear - increasing position size by 25%",
            "neutral": "Neutral - normal position size",
            "greed": "Greed - decreasing position size by 25%",
            "extreme_greed": "Extreme greed - reducing position size by 50%",
        }
        return reasons.get(mood_classification, "Unknown mood - normal position size")

    def get_risk_adjustments(
        self,
        mood_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get risk management adjustments based on market mood.

        Args:
            mood_data: Optional mood data. If None, fetches current mood.

        Returns:
            Dictionary with risk adjustment suggestions
        """
        if not self.enabled:
            return {
                "stop_loss_pct": settings.stop_loss_pct,
                "take_profit_pct": settings.take_profit_pct,
                "max_position_pct": settings.max_position_pct,
                "risk_level": "moderate",
                "reason": "Market mood integration disabled",
            }

        try:
            if mood_data is None:
                mood_data = self.detector.get_current_mood(refresh=False)

            trading_signals = self.detector.get_trading_signals(refresh=False)
            mood_classification = trading_signals.get("mood_classification", "neutral")

            return self.signal_generator.get_risk_adjustments(mood_classification)

        except Exception as e:
            logger.error(f"Error getting risk adjustments: {e}")
            return {
                "stop_loss_pct": settings.stop_loss_pct,
                "take_profit_pct": settings.take_profit_pct,
                "max_position_pct": settings.max_position_pct,
                "risk_level": "moderate",
                "reason": f"Error getting adjustments: {str(e)}",
            }

    def log_trade_with_mood(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        trade_details: Dict[str, Any],
        mood_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Log trade with associated mood data.

        Args:
            symbol: Trading symbol
            action: Trade action (BUY/SELL)
            quantity: Trade quantity
            price: Trade price
            trade_details: Additional trade details
            mood_data: Optional mood data. If None, fetches current mood.

        Returns:
            Enhanced trade log with mood data
        """
        if not self.enabled:
            return trade_details

        try:
            if mood_data is None:
                mood_data = self.detector.get_current_mood(refresh=False)

            trading_signals = self.detector.get_trading_signals(refresh=False)
            mood_classification = trading_signals.get("mood_classification", "neutral")

            enhanced_trade_log = {
                **trade_details,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "market_mood": {
                    "classification": mood_classification,
                    "composite_score": mood_data.get("composite_score", 0.0),
                    "confidence": mood_data.get("confidence", 0.0),
                    "trend": mood_data.get("trend", "stable"),
                    "signal": trading_signals.get("signal", "NO_SIGNAL"),
                },
                "mood_timestamp": mood_data.get("timestamp"),
                "logged_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Trade logged with mood data: {action} {quantity} {symbol} @ ${price:.2f} "
                f"(mood: {mood_classification}, score: {mood_data.get('composite_score', 0):.1f})"
            )

            return enhanced_trade_log

        except Exception as e:
            logger.error(f"Error logging trade with mood: {e}")
            return trade_details

    def get_trading_context(
        self,
        mood_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive trading context including market mood.

        Args:
            mood_data: Optional mood data. If None, fetches current mood.

        Returns:
            Trading context with mood information
        """
        if not self.enabled:
            return {
                "market_mood_enabled": False,
                "reason": "Market mood integration disabled",
            }

        try:
            if mood_data is None:
                mood_data = self.detector.get_current_mood(refresh=False)

            trading_signals = self.detector.get_trading_signals(refresh=False)
            position_sizing = self.detector.get_position_sizing_suggestion()
            risk_adjustments = self.detector.get_risk_adjustments()

            return {
                "market_mood_enabled": True,
                "mood": {
                    "classification": trading_signals.get("mood_classification", "neutral"),
                    "composite_score": mood_data.get("composite_score", 0.0),
                    "confidence": mood_data.get("confidence", 0.0),
                    "trend": mood_data.get("trend", "stable"),
                    "signal": trading_signals.get("signal", "NO_SIGNAL"),
                    "timestamp": mood_data.get("timestamp"),
                },
                "position_sizing": position_sizing,
                "risk_adjustments": risk_adjustments,
                "recommendations": trading_signals.get("recommendations", []),
            }

        except Exception as e:
            logger.error(f"Error getting trading context: {e}")
            return {
                "market_mood_enabled": True,
                "error": str(e),
                "reason": "Error fetching market mood data",
            }


def create_mood_integration() -> MarketMoodAutoTraderIntegration:
    """
    Factory function to create a market mood integration instance.

    Returns:
        MarketMoodAutoTraderIntegration instance
    """
    return MarketMoodAutoTraderIntegration()
