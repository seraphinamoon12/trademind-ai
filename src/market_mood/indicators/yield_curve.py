"""Yield Curve indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import FREDProvider


class YieldCurveIndicator:
    """Yield Curve indicator for economic outlook assessment."""

    def __init__(self, provider: Optional[FREDProvider] = None):
        """Initialize Yield Curve indicator.

        Args:
            provider: FREDProvider instance. If None, creates new instance.
        """
        self.provider = provider or FREDProvider()
        self.indicator_type = IndicatorType.YIELD_CURVE

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate yield curve score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        yc_score = indicator_value.value

        # Convert 0-100 yield curve score to -100 to +100 scale
        # 0 = inverted/recessionary (fear), 100 = steep/expansionary (greed)
        score = (yc_score - 50) * 2

        trend = 'stable'

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': yc_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'yield_curve',
                'yield_curve_data': indicator_value.metadata.get('yield_curve_data'),
                'yield_10y': indicator_value.metadata.get('yield_10y'),
                'yield_2y': indicator_value.metadata.get('yield_2y'),
                'yield_3m': indicator_value.metadata.get('yield_3m'),
                'date': indicator_value.metadata.get('date'),
                'interpretation': self._interpret_yield_curve(yc_score),
            }
        }

    def _interpret_yield_curve(self, yc_score: float) -> str:
        """Interpret yield curve score.

        Args:
            yc_score: Yield curve score (0-100)

        Returns:
            Interpretation string
        """
        if yc_score >= 75:
            return "Steep yield curve - strong growth outlook (greed)"
        elif yc_score >= 60:
            return "Normal upward sloping - expansionary (greed)"
        elif yc_score >= 40:
            return "Flattening - slowing growth (neutral)"
        elif yc_score >= 25:
            return "Near inverted - recession concerns (fear)"
        else:
            return "Inverted yield curve - recession warning (extreme fear)"
