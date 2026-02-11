"""Mood calculation engine for market mood composite scoring."""
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import logging

from src.market_mood.models import IndicatorType
from src.market_mood.config import MarketMoodConfig
from src.market_mood.indicators import (
    VIXIndicator,
    MarketBreadthIndicator,
    PutCallRatioIndicator,
    MATrendsIndicator,
    FearGreedIndicator,
    DXYIndicator,
    CreditSpreadsIndicator,
    YieldCurveIndicator,
)

logger = logging.getLogger(__name__)


class MoodCalculationEngine:
    """Engine for calculating composite market mood score from indicators."""

    def __init__(self, config: Optional[MarketMoodConfig] = None):
        """Initialize the mood calculation engine.

        Args:
            config: MarketMoodConfig instance. If None, uses default config.
        """
        self.config = config or MarketMoodConfig()
        self.indicators = {
            'vix': VIXIndicator(),
            'breadth': MarketBreadthIndicator(),
            'put_call': PutCallRatioIndicator(),
            'ma_trends': MATrendsIndicator(),
            'fear_greed': FearGreedIndicator(),
            'dxy': DXYIndicator(),
            'credit_spreads': CreditSpreadsIndicator(),
            'yield_curve': YieldCurveIndicator(),
        }
        self.weights = self.config.get_indicator_weights()

    def calculate_composite_score(
        self,
        indicator_results: Dict[str, Optional[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate composite mood score from indicator results.

        Args:
            indicator_results: Dictionary with indicator names and their results

        Returns:
            Dictionary with composite score, trend, confidence, and metadata
        """
        weighted_sum = 0.0
        total_weight = 0.0
        valid_indicators = []
        missing_indicators = []

        for indicator_name, result in indicator_results.items():
            if result is not None and 'score' in result:
                score = result['score']
                weight = self.weights.get(indicator_name, 0.0)

                weighted_sum += score * weight
                total_weight += weight
                valid_indicators.append(indicator_name)
            else:
                missing_indicators.append(indicator_name)

        if total_weight == 0:
            return {
                'score': 0.0,
                'normalized_score': 0.0,
                'trend': 'stable',
                'confidence': 0.0,
                'valid_indicators': [],
                'missing_indicators': list(indicator_results.keys()),
                'timestamp': datetime.utcnow(),
            }

        composite_score = weighted_sum / total_weight
        normalized_score = composite_score / 100.0

        return {
            'score': composite_score,
            'normalized_score': normalized_score,
            'trend': self.calculate_trend(indicator_results),
            'confidence': self.calculate_confidence(
                valid_indicators,
                list(indicator_results.keys())
            ),
            'valid_indicators': valid_indicators,
            'missing_indicators': missing_indicators,
            'timestamp': datetime.utcnow(),
        }

    def calculate_trend(
        self,
        indicator_results: Dict[str, Optional[Dict[str, Any]]]
    ) -> Literal['improving', 'declining', 'stable']:
        """Calculate overall trend from individual indicator trends.

        Args:
            indicator_results: Dictionary with indicator names and their results

        Returns:
            Overall trend direction
        """
        improving_count = 0
        declining_count = 0
        stable_count = 0

        for result in indicator_results.values():
            if result is None:
                continue

            trend = result.get('trend', 'stable')
            if trend == 'improving':
                improving_count += 1
            elif trend == 'declining':
                declining_count += 1
            else:
                stable_count += 1

        total = improving_count + declining_count + stable_count

        if total == 0:
            return 'stable'

        improving_pct = improving_count / total
        declining_pct = declining_count / total

        if improving_pct >= 0.6:
            return 'improving'
        elif declining_pct >= 0.6:
            return 'declining'
        else:
            return 'stable'

    def calculate_confidence(
        self,
        valid_indicators: List[str],
        all_indicators: List[str]
    ) -> float:
        """Calculate confidence based on data availability.

        Args:
            valid_indicators: List of valid indicator names
            all_indicators: List of all expected indicator names

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not all_indicators:
            return 0.0

        return len(valid_indicators) / len(all_indicators)

    def get_indicator_scores(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get scores from all indicators.

        Returns:
            Dictionary with indicator names and their calculated results
        """
        results = {}

        for name, indicator in self.indicators.items():
            try:
                result = indicator.calculate()
                results[name] = result
            except Exception as e:
                logger.error(f"Error calculating {name} indicator: {e}")
                results[name] = None

        return results

    def refresh_indicators(self) -> Dict[str, Optional[Dict[str, Any]]]:
        """Refresh and recalculate all indicators.

        Returns:
            Dictionary with refreshed indicator results
        """
        logger.info("Refreshing all market mood indicators")
        return self.get_indicator_scores()

    def get_mood_summary(
        self,
        indicator_results: Dict[str, Optional[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Get a comprehensive mood summary.

        Args:
            indicator_results: Dictionary with indicator names and their results

        Returns:
            Comprehensive mood summary
        """
        composite = self.calculate_composite_score(indicator_results)

        indicator_details = {}
        for name, result in indicator_results.items():
            if result:
                indicator_details[name] = {
                    'score': result.get('score'),
                    'trend': result.get('trend'),
                    'interpretation': result.get('metadata', {}).get('interpretation'),
                }
            else:
                indicator_details[name] = {
                    'score': None,
                    'trend': None,
                    'interpretation': 'Data unavailable',
                }

        return {
            'composite_score': composite['score'],
            'normalized_score': composite['normalized_score'],
            'trend': composite['trend'],
            'confidence': composite['confidence'],
            'valid_indicators': composite['valid_indicators'],
            'missing_indicators': composite['missing_indicators'],
            'indicator_details': indicator_details,
            'timestamp': composite['timestamp'],
        }
