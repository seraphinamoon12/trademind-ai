"""Trend detection for market mood analysis."""
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime, timedelta
import logging

from src.market_mood.config import MarketMoodConfig

logger = logging.getLogger(__name__)


class TrendDetector:
    """Detect trends in market mood over time."""

    def __init__(self, config: Optional[MarketMoodConfig] = None):
        """Initialize the trend detector.

        Args:
            config: MarketMoodConfig instance. If None, uses default config.
        """
        self.config = config or MarketMoodConfig()
        self.history: List[Dict[str, Any]] = []

    def detect_mood_trend(
        self,
        current_mood: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect if mood is improving, declining, or stable.

        Args:
            current_mood: Current mood data

        Returns:
            Dictionary with trend information
        """
        if not self.history:
            return {
                'trend': 'stable',
                'momentum': 0.0,
                'acceleration': 0.0,
                'days_analyzed': 0,
            }

        current_score = current_mood.get('score', 0.0)
        lookback = min(len(self.history), self.config.trend_lookback_days)

        if lookback < 2:
            return {
                'trend': 'stable',
                'momentum': 0.0,
                'acceleration': 0.0,
                'days_analyzed': lookback,
            }

        recent_scores = [
            entry.get('score', 0.0)
            for entry in self.history[-lookback:]
        ]

        momentum = self.calculate_momentum(recent_scores, current_score)
        acceleration = self.calculate_acceleration(recent_scores, current_score)
        trend = self._classify_trend(momentum, acceleration)

        return {
            'trend': trend,
            'momentum': momentum,
            'acceleration': acceleration,
            'days_analyzed': lookback,
            'recent_average': sum(recent_scores) / len(recent_scores),
        }

    def calculate_momentum(
        self,
        historical_scores: List[float],
        current_score: float
    ) -> float:
        """Calculate momentum as rate of change.

        Args:
            historical_scores: List of historical scores
            current_score: Current score

        Returns:
            Momentum value
        """
        if not historical_scores:
            return 0.0

        avg_historical = sum(historical_scores) / len(historical_scores)
        momentum = current_score - avg_historical

        return momentum

    def calculate_acceleration(
        self,
        historical_scores: List[float],
        current_score: float
    ) -> float:
        """Calculate acceleration (rate of change of momentum).

        Args:
            historical_scores: List of historical scores
            current_score: Current score

        Returns:
            Acceleration value
        """
        if len(historical_scores) < 2:
            return 0.0

        all_scores = historical_scores + [current_score]
        changes = [
            all_scores[i] - all_scores[i-1]
            for i in range(1, len(all_scores))
        ]

        if not changes:
            return 0.0

        return changes[-1] - (sum(changes[:-1]) / len(changes[:-1]))

    def _classify_trend(
        self,
        momentum: float,
        acceleration: float
    ) -> Literal['strongly_improving', 'improving', 'stable', 'declining', 'strongly_declining']:
        """Classify trend based on momentum and acceleration.

        Args:
            momentum: Momentum value
            acceleration: Acceleration value

        Returns:
            Trend classification
        """
        threshold = self.config.momentum_threshold

        if momentum > threshold and acceleration > threshold / 2:
            return 'strongly_improving'
        elif momentum > threshold:
            return 'improving'
        elif momentum < -threshold and acceleration < -threshold / 2:
            return 'strongly_declining'
        elif momentum < -threshold:
            return 'declining'
        else:
            return 'stable'

    def identify_divergences(
        self,
        mood_data: Dict[str, Any],
        price_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Identify divergences between mood and price.

        Args:
            mood_data: Mood data
            price_data: Optional price data

        Returns:
            Dictionary with divergence information
        """
        if not self.history or not price_data:
            return {
                'divergence': False,
                'type': None,
                'description': 'Insufficient data for divergence analysis',
            }

        mood_score = mood_data.get('score', 0.0)
        price_change = price_data.get('change', 0.0)

        mood_trend = self.detect_mood_trend(mood_data)['trend']

        divergence = False
        divergence_type = None
        description = 'No significant divergence'

        if mood_trend == 'improving' and price_change < -2:
            divergence = True
            divergence_type = 'bullish'
            description = 'Bullish divergence: Mood improving while price declining - potential reversal'
        elif mood_trend == 'declining' and price_change > 2:
            divergence = True
            divergence_type = 'bearish'
            description = 'Bearish divergence: Mood declining while price rising - potential reversal'
        elif mood_trend == 'strongly_improving' and price_change < -5:
            divergence = True
            divergence_type = 'strong_bullish'
            description = 'Strong bullish divergence: Significant mood improvement vs price decline'
        elif mood_trend == 'strongly_declining' and price_change > 5:
            divergence = True
            divergence_type = 'strong_bearish'
            description = 'Strong bearish divergence: Significant mood decline vs price rise'

        return {
            'divergence': divergence,
            'type': divergence_type,
            'description': description,
            'mood_trend': mood_trend,
            'price_change': price_change,
        }

    def update_history(self, mood_data: Dict[str, Any]) -> None:
        """Update mood history with new data point.

        Args:
            mood_data: Mood data to add to history
        """
        entry = {
            'score': mood_data.get('score', 0.0),
            'trend': mood_data.get('trend', 'stable'),
            'confidence': mood_data.get('confidence', 0.0),
            'timestamp': mood_data.get('timestamp', datetime.utcnow()),
        }

        self.history.append(entry)

        if len(self.history) > self.config.history_cache_size:
            self.history = self.history[-self.config.history_cache_size:]

    def get_momentum_summary(
        self,
        mood_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get comprehensive momentum summary.

        Args:
            mood_data: Current mood data

        Returns:
            Momentum summary dictionary
        """
        trend_info = self.detect_mood_trend(mood_data)

        return {
            'trend': trend_info['trend'],
            'momentum': trend_info['momentum'],
            'momentum_pct': (trend_info['momentum'] / 100.0) if trend_info['days_analyzed'] > 0 else 0.0,
            'acceleration': trend_info['acceleration'],
            'days_analyzed': trend_info['days_analyzed'],
            'recent_average': trend_info['recent_average'],
            'strength': self._get_trend_strength(trend_info),
        }

    def _get_trend_strength(
        self,
        trend_info: Dict[str, Any]
    ) -> str:
        """Get trend strength description.

        Args:
            trend_info: Trend information dictionary

        Returns:
            Trend strength description
        """
        momentum = abs(trend_info['momentum'])
        threshold = self.config.momentum_threshold

        if momentum > threshold * 2:
            return 'very_strong'
        elif momentum > threshold * 1.5:
            return 'strong'
        elif momentum > threshold:
            return 'moderate'
        elif momentum > threshold * 0.5:
            return 'weak'
        else:
            return 'none'

    def clear_history(self) -> None:
        """Clear mood history."""
        self.history = []

    def get_history(self, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get mood history.

        Args:
            days: Number of days to return. If None, returns all.

        Returns:
            List of historical mood entries
        """
        if days is None or days >= len(self.history):
            return self.history.copy()

        return self.history[-days:]
