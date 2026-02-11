"""Main Market Mood Detector class for orchestrating all components."""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from src.market_mood.config import MarketMoodConfig
from src.market_mood.engine import MoodCalculationEngine
from src.market_mood.signals import SignalGenerator
from src.market_mood.trends import TrendDetector

logger = logging.getLogger(__name__)


class MarketMoodDetector:
    """Main detector class for market mood analysis."""

    def __init__(self, config: Optional[MarketMoodConfig] = None):
        """Initialize the market mood detector.

        Args:
            config: MarketMoodConfig instance. If None, uses default config.
        """
        self.config = config or MarketMoodConfig()
        self.engine = MoodCalculationEngine(self.config)
        self.signal_generator = SignalGenerator(self.config)
        self.trend_detector = TrendDetector(self.config)

        self._current_mood: Optional[Dict[str, Any]] = None
        self._current_indicators: Optional[Dict[str, Optional[Dict[str, Any]]]] = None
        self._current_signals: Optional[Dict[str, Any]] = None

    def get_current_mood(self, refresh: bool = False) -> Dict[str, Any]:
        """Get current market mood.

        Args:
            refresh: If True, refresh indicators before calculating

        Returns:
            Dictionary with current mood information
        """
        if refresh or self._current_mood is None:
            self.refresh_indicators()

        if self._current_mood is None:
            return self._get_empty_mood()

        return self._current_mood

    def refresh_indicators(self) -> None:
        """Refresh all indicators and recalculate mood."""
        logger.info("Refreshing market mood indicators")

        self._current_indicators = self.engine.refresh_indicators()
        self._current_mood = self.engine.get_mood_summary(self._current_indicators)
        self._current_signals = self.signal_generator.generate_signals(self._current_mood)

        self.trend_detector.update_history(self._current_mood)

    def get_mood_history(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get mood history.

        Args:
            days: Number of days to return. If None, returns all.

        Returns:
            List of historical mood entries
        """
        return self.trend_detector.get_history(days)

    def get_trading_signals(self, refresh: bool = False) -> Dict[str, Any]:
        """Get current trading signals.

        Args:
            refresh: If True, refresh mood before generating signals

        Returns:
            Dictionary with trading signals and recommendations
        """
        if refresh or self._current_signals is None:
            self.get_current_mood(refresh=True)

        if self._current_signals is None:
            return {
                'signal': 'NO_SIGNAL',
                'mood_classification': 'neutral',
                'confidence': 0.0,
                'score': 0.0,
                'trend': 'stable',
                'recommendations': [],
                'timestamp': datetime.utcnow(),
            }

        return self._current_signals

    def get_indicator_scores(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get scores from all indicators.

        Returns:
            Dictionary with indicator names and their calculated results
        """
        if self._current_indicators is None:
            self.refresh_indicators()

        return self._current_indicators or {}

    def get_momentum_summary(self) -> Dict[str, Any]:
        """Get momentum summary.

        Returns:
            Dictionary with momentum information
        """
        if self._current_mood is None:
            self.get_current_mood()

        return self.trend_detector.get_momentum_summary(self._current_mood or {})

    def identify_divergences(
        self,
        price_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Identify divergences between mood and price.

        Args:
            price_data: Optional price data

        Returns:
            Dictionary with divergence information
        """
        if self._current_mood is None:
            self.get_current_mood()

        return self.trend_detector.identify_divergences(
            self._current_mood or {},
            price_data
        )

    def get_position_sizing_suggestion(self) -> Dict[str, Any]:
        """Get position sizing suggestions.

        Returns:
            Dictionary with position sizing recommendations
        """
        if self._current_signals is None:
            self.get_trading_signals()

        signal = self._current_signals.get('signal', 'NO_SIGNAL') if self._current_signals else 'NO_SIGNAL'
        confidence = self._current_signals.get('confidence', 0.0) if self._current_signals else 0.0

        return self.signal_generator.get_position_sizing_suggestion(signal, confidence)

    def get_risk_adjustments(self) -> Dict[str, Any]:
        """Get risk management adjustments.

        Returns:
            Dictionary with risk adjustment suggestions
        """
        if self._current_signals is None:
            self.get_trading_signals()

        mood_classification = self._current_signals.get('mood_classification', 'neutral') if self._current_signals else 'neutral'

        return self.signal_generator.get_risk_adjustments(mood_classification)

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Get comprehensive market mood report.

        Returns:
            Comprehensive report with all available information
        """
        self.get_current_mood()

        return {
            'mood': self._current_mood or self._get_empty_mood(),
            'indicators': self.get_indicator_scores(),
            'signals': self.get_trading_signals(),
            'trend': self.get_momentum_summary(),
            'divergence': self.identify_divergences(),
            'position_sizing': self.get_position_sizing_suggestion(),
            'risk_adjustments': self.get_risk_adjustments(),
            'report_timestamp': datetime.utcnow(),
        }

    def _get_empty_mood(self) -> Dict[str, Any]:
        """Get empty mood result when data is unavailable.

        Returns:
            Empty mood dictionary
        """
        return {
            'composite_score': 0.0,
            'normalized_score': 0.0,
            'trend': 'stable',
            'confidence': 0.0,
            'valid_indicators': [],
            'missing_indicators': [],
            'indicator_details': {},
            'timestamp': datetime.utcnow(),
        }

    def clear_history(self) -> None:
        """Clear mood history."""
        self.trend_detector.clear_history()

    def get_status(self) -> Dict[str, Any]:
        """Get detector status.

        Returns:
            Status dictionary
        """
        return {
            'config': {
                'enable_signals': self.config.enable_signals,
                'signal_confidence_threshold': self.config.signal_confidence_threshold,
                'trend_lookback_days': self.config.trend_lookback_days,
            },
            'current_mood': self._current_mood is not None,
            'history_size': len(self.trend_detector.history),
            'indicators_refreshed': self._current_indicators is not None,
        }
