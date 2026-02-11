"""DXY (US Dollar Index) indicator."""
from typing import Optional, Dict, Any, Literal
from datetime import datetime

from src.market_mood.models import IndicatorType, IndicatorValue
from src.market_mood.data_providers import FREDProvider


class DXYIndicator:
    """DXY indicator for risk assessment through US Dollar strength."""

    def __init__(self, provider: Optional[FREDProvider] = None):
        """Initialize DXY indicator.

        Args:
            provider: FREDProvider instance. If None, creates new instance.
        """
        self.provider = provider or FREDProvider()
        self.indicator_type = IndicatorType.DXY

    def calculate(self) -> Optional[Dict[str, Any]]:
        """Calculate DXY score (-100 to +100).

        Returns:
            Dictionary with score, trend, and metadata, or None if calculation fails
        """
        indicator_value = self.provider.fetch_with_retry(self.indicator_type)

        if indicator_value is None:
            return None

        dxy_score = indicator_value.value

        # Convert 0-100 DXY score to -100 to +100 scale
        # 0 = weak USD (risk-on = greed), 100 = strong USD (risk-off = fear)
        score = (dxy_score - 50) * 2

        # Determine trend from change
        change = indicator_value.metadata.get('change', 0)
        trend = self._determine_trend(change)

        return {
            'score': score,
            'normalized_score': score / 100.0,
            'raw_value': dxy_score,
            'trend': trend,
            'timestamp': indicator_value.timestamp,
            'source': indicator_value.source,
            'metadata': {
                'indicator': 'dxy',
                'dxy_value': indicator_value.metadata.get('dxy_value'),
                'change': change,
                'series': indicator_value.metadata.get('series'),
                'date': indicator_value.metadata.get('date'),
                'interpretation': self._interpret_dxy(dxy_score),
            }
        }

    def _determine_trend(
        self,
        change: float
    ) -> Literal['improving', 'declining', 'stable']:
        """Determine if DXY is improving (weakening = risk-on) or declining (strengthening = risk-off).

        Args:
            change: DXY change percentage

        Returns:
            Trend direction
        """
        if change > 1:
            return 'declining'
        elif change < -1:
            return 'improving'
        else:
            return 'stable'

    def _interpret_dxy(self, dxy_score: float) -> str:
        """Interpret DXY score.

        Args:
            dxy_score: DXY score (0-100)

        Returns:
            Interpretation string
        """
        if dxy_score >= 80:
            return "Very strong USD - risk-off environment (fear)"
        elif dxy_score >= 60:
            return "Strong USD - flight to safety (fear)"
        elif dxy_score >= 40:
            return "Moderate USD - balanced environment (neutral)"
        elif dxy_score >= 20:
            return "Weak USD - risk-on appetite (greed)"
        else:
            return "Very weak USD - high risk appetite (greed)"
