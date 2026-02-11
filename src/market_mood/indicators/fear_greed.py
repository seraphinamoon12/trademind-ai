"""Fear & Greed indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import FREDProvider


class FearGreedIndicator:
    """Fear & Greed indicator for sentiment assessment."""

    def __init__(self, provider: Optional[FREDProvider] = None):
        """Initialize Fear & Greed indicator.

        Args:
            provider: FREDProvider instance. If None, creates new instance.
        """
        self.provider = provider or FREDProvider()
        self.indicator_type = IndicatorType.FEAR_GREED

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate Fear & Greed score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        fg_score = indicator_value.value

        # Convert 0-100 Fear & Greed score to -100 to +100 scale
        # 0 = extreme fear (-100), 50 = neutral (0), 100 = extreme greed (+100)
        score = (fg_score - 50) * 2

        trend = 'stable'

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': fg_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'fear_greed',
                'components': indicator_value.metadata.get('components'),
                'interpretation': self._interpret_fg(fg_score),
            }
        }

    def _interpret_fg(self, fg_score: float) -> str:
        """Interpret Fear & Greed score.

        Args:
            fg_score: Fear & Greed score (0-100)

        Returns:
            Interpretation string
        """
        if fg_score >= 85:
            return "Extreme Greed - market euphoria, potential bubble"
        elif fg_score >= 75:
            return "Greed - strong bullish sentiment"
        elif fg_score >= 60:
            return "Moderate Greed - optimistic sentiment"
        elif fg_score >= 45:
            return "Neutral - balanced market sentiment"
        elif fg_score >= 30:
            return "Moderate Fear - cautious sentiment"
        elif fg_score >= 20:
            return "Fear - bearish sentiment, capitulation"
        else:
            return "Extreme Fear - panic selling, opportunity zone"
