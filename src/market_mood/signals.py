"""Signal generator for trading signals based on market mood."""
from typing import Dict, Any, List, Literal, Optional
from datetime import datetime
import logging

from src.market_mood.config import MarketMoodConfig

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Generate trading signals from market mood composite score."""

    def __init__(self, config: Optional[MarketMoodConfig] = None):
        """Initialize the signal generator.

        Args:
            config: MarketMoodConfig instance. If None, uses default config.
        """
        self.config = config or MarketMoodConfig()

    def generate_signals(
        self,
        mood_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate trading signals from mood data.

        Args:
            mood_data: Dictionary with composite mood score and metadata

        Returns:
            Dictionary with trading signals and recommendations
        """
        score = mood_data.get('score', 0.0)
        confidence = mood_data.get('confidence', 0.0)
        trend = mood_data.get('trend', 'stable')

        mood_classification = self.classify_mood(score)
        signal = self._determine_signal(mood_classification, confidence)

        return {
            'signal': signal,
            'mood_classification': mood_classification,
            'confidence': confidence,
            'score': score,
            'trend': trend,
            'recommendations': self.get_recommendations(
                mood_classification,
                signal,
                confidence
            ),
            'timestamp': datetime.utcnow(),
        }

    def classify_mood(
        self,
        score: float
    ) -> Literal['extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed']:
        """Classify mood based on score.

        Args:
            score: Composite mood score (-100 to +100)

        Returns:
            Mood classification
        """
        if score <= self.config.extreme_fear_threshold:
            return 'extreme_fear'
        elif score <= self.config.fear_threshold:
            return 'fear'
        elif score < self.config.greed_threshold:
            return 'neutral'
        elif score < self.config.extreme_greed_threshold:
            return 'greed'
        else:
            return 'extreme_greed'

    def _determine_signal(
        self,
        mood_classification: str,
        confidence: float
    ) -> Literal['STRONG_BUY', 'BUY', 'HOLD', 'REDUCE', 'SELL', 'NO_SIGNAL']:
        """Determine trading signal from mood classification and confidence.

        Args:
            mood_classification: Mood classification
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            Trading signal
        """
        if not self.config.enable_signals:
            return 'NO_SIGNAL'

        if confidence < self.config.signal_confidence_threshold:
            return 'NO_SIGNAL'

        signal_map = {
            'extreme_fear': 'STRONG_BUY',
            'fear': 'BUY',
            'neutral': 'HOLD',
            'greed': 'REDUCE',
            'extreme_greed': 'SELL',
        }

        return signal_map.get(mood_classification, 'HOLD')

    def get_recommendations(
        self,
        mood_classification: str,
        signal: str,
        confidence: float
    ) -> List[str]:
        """Get actionable trading recommendations.

        Args:
            mood_classification: Mood classification
            signal: Trading signal
            confidence: Confidence score

        Returns:
            List of recommendation strings
        """
        recommendations = []

        if signal == 'NO_SIGNAL':
            recommendations.append('Insufficient confidence to generate signals')
            return recommendations

        if confidence < 0.8:
            recommendations.append(
                f'Moderate confidence ({confidence:.1%}). Consider additional analysis.'
            )

        if mood_classification == 'extreme_fear':
            recommendations.extend([
                'Market in extreme fear - strong buying opportunity',
                'Consider accumulating quality positions',
                'Reduce cash allocation',
                'Focus on defensive sectors',
            ])
        elif mood_classification == 'fear':
            recommendations.extend([
                'Market fearful - buying opportunity',
                'Consider adding to positions',
                'Look for value opportunities',
            ])
        elif mood_classification == 'neutral':
            recommendations.extend([
                'Market neutral - maintain current allocation',
                'Rebalance if needed',
                'Stay disciplined with strategy',
            ])
        elif mood_classification == 'greed':
            recommendations.extend([
                'Market greedy - consider reducing exposure',
                'Take profits on extended positions',
                'Increase cash reserves',
            ])
        elif mood_classification == 'extreme_greed':
            recommendations.extend([
                'Market in extreme greed - strong sell signal',
                'Reduce risk exposure significantly',
                'Hedge existing positions',
                'Increase cash allocation',
            ])

        return recommendations

    def get_position_sizing_suggestion(
        self,
        signal: str,
        confidence: float
    ) -> Dict[str, Any]:
        """Get position sizing suggestions based on signal and confidence.

        Args:
            signal: Trading signal
            confidence: Confidence score

        Returns:
            Dictionary with position sizing recommendations
        """
        base_sizing = {
            'STRONG_BUY': {'min': 0.8, 'target': 1.0, 'max': 1.2},
            'BUY': {'min': 0.5, 'target': 0.75, 'max': 1.0},
            'HOLD': {'min': 0.0, 'target': 0.0, 'max': 0.2},
            'REDUCE': {'min': -0.5, 'target': -0.75, 'max': -1.0},
            'SELL': {'min': -0.8, 'target': -1.0, 'max': -1.2},
            'NO_SIGNAL': {'min': 0.0, 'target': 0.0, 'max': 0.0},
        }

        sizing = base_sizing.get(signal, base_sizing['HOLD'])

        confidence_multiplier = 0.5 + confidence * 0.5

        return {
            'min_allocation': sizing['min'] * confidence_multiplier,
            'target_allocation': sizing['target'] * confidence_multiplier,
            'max_allocation': sizing['max'] * confidence_multiplier,
            'confidence_multiplier': confidence_multiplier,
        }

    def get_risk_adjustments(
        self,
        mood_classification: str
    ) -> Dict[str, Any]:
        """Get risk management adjustments based on mood.

        Args:
            mood_classification: Mood classification

        Returns:
            Dictionary with risk adjustment suggestions
        """
        risk_adjustments = {
            'extreme_fear': {
                'stop_loss_pct': 0.08,
                'take_profit_pct': 0.15,
                'max_position_pct': 0.15,
                'risk_level': 'aggressive',
            },
            'fear': {
                'stop_loss_pct': 0.06,
                'take_profit_pct': 0.12,
                'max_position_pct': 0.12,
                'risk_level': 'moderate_aggressive',
            },
            'neutral': {
                'stop_loss_pct': 0.05,
                'take_profit_pct': 0.10,
                'max_position_pct': 0.10,
                'risk_level': 'moderate',
            },
            'greed': {
                'stop_loss_pct': 0.04,
                'take_profit_pct': 0.08,
                'max_position_pct': 0.08,
                'risk_level': 'conservative',
            },
            'extreme_greed': {
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.05,
                'max_position_pct': 0.05,
                'risk_level': 'very_conservative',
            },
        }

        return risk_adjustments.get(mood_classification, risk_adjustments['neutral'])
