"""Integration tests for Market Mood Phase 3."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.trading_graph.nodes.market_mood_node import (
    market_mood_analysis,
    _apply_mood_adjustments,
    _get_position_size_multiplier,
    should_skip_trading,
    get_mood_context,
)
from src.trading.integration.market_mood_integration import (
    MarketMoodAutoTraderIntegration,
    create_mood_integration,
)
from src.trading_graph.state import TradingState
from src.core.database import MoodHistory, MoodSignal, MoodIndicatorValue, get_db
from src.market_mood.models import IndicatorType, IndicatorValue, MoodScore
from src.market_mood.detector import MarketMoodDetector
from src.config import settings


@pytest.fixture
def mock_detector():
    """Create a mock MarketMoodDetector."""
    detector = Mock(spec=MarketMoodDetector)
    detector.get_current_mood.return_value = {
        "composite_score": 10.0,
        "normalized_score": -20.0,
        "trend": "improving",
        "confidence": 0.85,
        "valid_indicators": ["vix", "market_breadth", "put_call_ratio", "ma_trends"],
        "missing_indicators": [],
        "indicator_details": {
            "vix": {"score": 80.0, "value": 12.0, "trend": "improving"},
            "market_breadth": {"score": -30.0, "value": 35.0, "trend": "declining"},
            "put_call_ratio": {"score": 50.0, "value": 1.0, "trend": "stable"},
            "ma_trends": {"score": 60.0, "value": 70.0, "trend": "improving"},
        },
        "timestamp": datetime.now(timezone.utc),
    }
    detector.get_trading_signals.return_value = {
        "signal": "BUY",
        "mood_classification": "extreme_fear",
        "confidence": 0.85,
        "strength": "strong",
        "recommendations": ["Increase position size by 50%", "Buy the dip"],
        "timestamp": datetime.now(timezone.utc),
    }
    detector.get_indicator_scores.return_value = {
        "vix": {"score": 80.0, "value": 12.0, "trend": "improving", "timestamp": datetime.now(timezone.utc)},
        "market_breadth": {"score": -30.0, "value": 35.0, "trend": "declining", "timestamp": datetime.now(timezone.utc)},
        "put_call_ratio": {"score": 50.0, "value": 1.0, "trend": "stable", "timestamp": datetime.now(timezone.utc)},
        "ma_trends": {"score": 60.0, "value": 70.0, "trend": "improving", "timestamp": datetime.now(timezone.utc)},
    }
    detector.get_position_sizing_suggestion.return_value = {
        "multiplier": 1.5,
        "reason": "Extreme fear - increasing position size by 50%",
        "max_position_pct": 0.15,
    }
    detector.get_risk_adjustments.return_value = {
        "stop_loss_pct": 0.04,
        "take_profit_pct": 0.12,
        "max_position_pct": 0.15,
        "risk_level": "low",
    }
    return detector


@pytest.fixture
def sample_trading_state():
    """Create a sample trading state."""
    return TradingState(
        symbol="AAPL",
        timeframe="1d",
        technical_signals={"action": "BUY", "confidence": 0.75},
        sentiment_signals={"action": "BUY", "confidence": 0.65},
    )


class TestMarketMoodNodeIntegration:
    """Tests for MarketMoodNode integration with LangGraph."""

    @pytest.mark.asyncio
    async def test_market_mood_analysis_success(self, sample_trading_state, mock_detector):
        """Test successful market mood analysis."""
        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            result = await market_mood_analysis(sample_trading_state)

            assert result["market_mood_data"]["composite_score"] == 10.0
            assert result["market_mood_data"]["normalized_score"] == -20.0
            assert result["market_mood_data"]["trend"] == "improving"
            assert result["market_mood_data"]["confidence"] == 0.85
            assert result["market_mood_signals"]["signal"] == "BUY"
            assert result["market_mood_signals"]["mood_classification"] == "extreme_fear"
            assert result["current_node"] == "market_mood_analysis"
            assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_market_mood_analysis_disabled(self, sample_trading_state):
        """Test market mood analysis when disabled."""
        with patch("src.trading_graph.nodes.market_mood_node.settings") as mock_settings:
            mock_settings.market_mood_enabled = False
            result = await market_mood_analysis(sample_trading_state)

            assert "error" in result
            assert "disabled" in result["error"].lower()
            assert result["current_node"] == "market_mood_analysis"

    @pytest.mark.asyncio
    async def test_market_mood_analysis_error_handling(self, sample_trading_state):
        """Test error handling in market mood analysis."""
        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector") as MockDetector:
            MockDetector.side_effect = Exception("Detector initialization failed")
            result = await market_mood_analysis(sample_trading_state)

            assert "error" in result
            assert "failed" in result["error"].lower()
            assert result["current_node"] == "market_mood_analysis"

    @pytest.mark.asyncio
    async def test_mood_adjusted_signals(self, sample_trading_state, mock_detector):
        """Test mood-adjusted trading signals."""
        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            result = await market_mood_analysis(sample_trading_state)

            adjusted_signals = result["mood_adjusted_signals"]
            assert adjusted_signals["mood_classification"] == "extreme_fear"
            assert adjusted_signals["position_size_multiplier"] == 1.5
            assert adjusted_signals["stop_loss_adjustment"] == 0.04
            assert adjusted_signals["take_profit_adjustment"] == 0.12
            assert adjusted_signals["max_position_adjustment"] == 0.15
            assert adjusted_signals["risk_level"] == "low"

    @pytest.mark.asyncio
    async def test_indicator_details_propagation(self, sample_trading_state, mock_detector):
        """Test that indicator details are properly propagated."""
        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            result = await market_mood_analysis(sample_trading_state)

            indicators = result["mood_indicators"]
            assert "vix" in indicators
            assert "market_breadth" in indicators
            assert "put_call_ratio" in indicators
            assert "ma_trends" in indicators


class TestMoodBasedPositionSizing:
    """Tests for mood-based position sizing calculations."""

    @pytest.mark.parametrize("classification,expected_multiplier", [
        ("extreme_fear", 1.5),
        ("fear", 1.25),
        ("neutral", 1.0),
        ("greed", 0.75),
        ("extreme_greed", 0.5),
        ("unknown", 1.0),
    ])
    def test_position_size_multiplier(self, classification, expected_multiplier):
        """Test position size multipliers for different moods."""
        multiplier = _get_position_size_multiplier(classification)
        assert multiplier == expected_multiplier

    def test_should_skip_trading_extreme_greed(self):
        """Test skipping trading in extreme greed."""
        assert should_skip_trading("extreme_greed") is True

    @pytest.mark.parametrize("mood", ["extreme_fear", "fear", "neutral", "greed"])
    def test_should_not_skip_trading_normal_conditions(self, mood):
        """Test not skipping trading in normal conditions."""
        assert should_skip_trading(mood) is False

    def test_apply_mood_adjustments_extreme_fear(self):
        """Test applying adjustments for extreme fear."""
        result = _apply_mood_adjustments(
            technical_signals={"action": "BUY"},
            sentiment_signals={"action": "BUY"},
            market_mood_signals={"mood_classification": "extreme_fear", "signal": "BUY"},
            position_sizing={"multiplier": 1.5},
            risk_adjustments={"stop_loss_pct": 0.04, "take_profit_pct": 0.12, "max_position_pct": 0.15, "risk_level": "low"}
        )

        assert result["position_size_multiplier"] == 1.5
        assert result["stop_loss_adjustment"] == 0.04
        assert result["take_profit_adjustment"] == 0.12

    def test_apply_mood_adjustments_neutral(self):
        """Test applying adjustments for neutral mood."""
        result = _apply_mood_adjustments(
            technical_signals={"action": "HOLD"},
            sentiment_signals={"action": "HOLD"},
            market_mood_signals={"mood_classification": "neutral", "signal": "NO_SIGNAL"},
            position_sizing={"multiplier": 1.0},
            risk_adjustments={"stop_loss_pct": 0.05, "take_profit_pct": 0.10, "max_position_pct": 0.10, "risk_level": "moderate"}
        )

        assert result["position_size_multiplier"] == 1.0
        assert result["stop_loss_adjustment"] == 0.05

    def test_get_mood_context(self):
        """Test getting simplified mood context."""
        mood_data = {
            "mood_classification": "extreme_fear",
            "signal": "BUY",
            "confidence": 0.85,
            "composite_score": -50.0,
            "trend": "improving",
        }
        context = get_mood_context(mood_data)

        assert context["classification"] == "extreme_fear"
        assert context["signal"] == "BUY"
        assert context["confidence"] == 0.85
        assert context["composite_score"] == -50.0
        assert context["trend"] == "improving"


class TestMarketMoodAutoTraderIntegration:
    """Tests for auto-trader integration with market mood."""

    @pytest.fixture
    def integration(self, mock_detector):
        """Create auto-trader integration instance."""
        return MarketMoodAutoTraderIntegration(detector=mock_detector)

    def test_should_trade_extreme_fear(self, integration):
        """Test that trading is allowed in extreme fear."""
        should_trade, reason, context = integration.should_trade()

        assert should_trade is True
        assert "extreme_fear" in reason.lower()
        assert context["classification"] == "extreme_fear"

    def test_should_trade_extreme_greed(self, integration, mock_detector):
        """Test that trading is skipped in extreme greed."""
        mock_detector.get_trading_signals.return_value = {
            "mood_classification": "extreme_greed",
            "signal": "SELL",
            "confidence": 0.8,
            "timestamp": datetime.now(timezone.utc),
        }

        should_trade, reason, context = integration.should_trade()

        assert should_trade is False
        assert "skip" in reason.lower()
        assert context["classification"] == "extreme_greed"

    def test_should_trade_disabled(self, mock_detector):
        """Test trading when integration is disabled."""
        integration = MarketMoodAutoTraderIntegration(detector=mock_detector)
        integration.enabled = False

        should_trade, reason, context = integration.should_trade()

        assert should_trade is True
        assert "disabled" in reason.lower()

    def test_get_adjusted_position_size_extreme_fear(self, integration):
        """Test position size adjustment for extreme fear."""
        adjusted_quantity, info = integration.get_adjusted_position_size(100)

        assert adjusted_quantity == 150
        assert info["multiplier"] == 1.5
        assert "extreme fear" in info["reason"].lower()

    def test_get_adjusted_position_size_neutral(self, integration, mock_detector):
        """Test position size adjustment for neutral mood."""
        mock_detector.get_trading_signals.return_value = {
            "mood_classification": "neutral",
            "signal": "NO_SIGNAL",
            "confidence": 0.5,
            "timestamp": datetime.now(timezone.utc),
        }

        adjusted_quantity, info = integration.get_adjusted_position_size(100)

        assert adjusted_quantity == 100
        assert info["multiplier"] == 1.0

    def test_get_adjusted_position_size_extreme_greed(self, integration, mock_detector):
        """Test position size adjustment for extreme greed."""
        mock_detector.get_trading_signals.return_value = {
            "mood_classification": "extreme_greed",
            "signal": "SELL",
            "confidence": 0.8,
            "timestamp": datetime.now(timezone.utc),
        }

        adjusted_quantity, info = integration.get_adjusted_position_size(100)

        assert adjusted_quantity == 50
        assert info["multiplier"] == 0.5

    def test_get_risk_adjustments(self, integration):
        """Test getting risk adjustments."""
        adjustments = integration.get_risk_adjustments()

        assert "stop_loss_pct" in adjustments
        assert "take_profit_pct" in adjustments
        assert "max_position_pct" in adjustments
        assert "risk_level" in adjustments

    def test_log_trade_with_mood(self, integration):
        """Test logging trade with mood data."""
        trade_details = {
            "strategy": "RSI",
            "reasoning": "Oversold condition",
        }
        enhanced_log = integration.log_trade_with_mood(
            symbol="AAPL",
            action="BUY",
            quantity=150,
            price=150.0,
            trade_details=trade_details
        )

        assert enhanced_log["symbol"] == "AAPL"
        assert enhanced_log["action"] == "BUY"
        assert enhanced_log["quantity"] == 150
        assert "market_mood" in enhanced_log
        assert enhanced_log["market_mood"]["classification"] == "extreme_fear"

    def test_get_trading_context(self, integration):
        """Test getting comprehensive trading context."""
        context = integration.get_trading_context()

        assert context["market_mood_enabled"] is True
        assert "mood" in context
        assert "position_sizing" in context
        assert "risk_adjustments" in context
        assert "recommendations" in context

    def test_create_mood_integration_factory(self, mock_detector):
        """Test factory function for creating integration instance."""
        with patch("src.trading.integration.market_mood_integration.MarketMoodDetector", return_value=mock_detector):
            integration = create_mood_integration()

            assert isinstance(integration, MarketMoodAutoTraderIntegration)
            assert integration.detector is not None


class TestDatabaseOperations:
    """Tests for database operations related to market mood."""

    @pytest.fixture
    def db_session(self):
        """Create a test database session."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite:///:memory:")
        MoodHistory.metadata.create_all(bind=engine)
        MoodSignal.metadata.create_all(bind=engine)
        MoodIndicatorValue.metadata.create_all(bind=engine)

        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.close()

    def test_save_mood_history(self, db_session):
        """Test saving mood history to database."""
        mood_history = MoodHistory(
            timestamp=datetime.now(timezone.utc),
            overall_score=25.0,
            sentiment="extreme_fear",
            confidence=0.85,
            components={
                "vix": 80.0,
                "market_breadth": -30.0,
                "put_call_ratio": 50.0,
            }
        )

        db_session.add(mood_history)
        db_session.commit()

        retrieved = db_session.query(MoodHistory).first()
        assert retrieved.overall_score == 25.0
        assert retrieved.sentiment == "extreme_fear"
        assert retrieved.confidence == 0.85

    def test_save_mood_signal(self, db_session):
        """Test saving mood signal to database."""
        mood_signal = MoodSignal(
            timestamp=datetime.now(timezone.utc),
            signal="BUY",
            strength="strong",
            reasoning="Market in extreme fear - buying opportunity",
            actions={
                "position_multiplier": 1.5,
                "stop_loss": 0.04,
                "take_profit": 0.12,
            }
        )

        db_session.add(mood_signal)
        db_session.commit()

        retrieved = db_session.query(MoodSignal).first()
        assert retrieved.signal == "BUY"
        assert retrieved.strength == "strong"

    def test_save_mood_indicator_value(self, db_session):
        """Test saving individual indicator values to database."""
        indicator_value = MoodIndicatorValue(
            timestamp=datetime.now(timezone.utc),
            indicator_type="vix",
            value=12.5,
            score=80.0,
            trend="improving",
            indicator_metadata={"previous": 15.0, "change": -2.5}
        )

        db_session.add(indicator_value)
        db_session.commit()

        retrieved = db_session.query(MoodIndicatorValue).first()
        assert retrieved.indicator_type == "vix"
        assert retrieved.value == 12.5
        assert retrieved.score == 80.0
        assert retrieved.trend == "improving"

    def test_query_mood_history_by_date_range(self, db_session):
        """Test querying mood history within a date range."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        history_entries = [
            MoodHistory(timestamp=yesterday, overall_score=10.0, sentiment="extreme_fear", confidence=0.9, components={}),
            MoodHistory(timestamp=now, overall_score=50.0, sentiment="neutral", confidence=0.8, components={}),
        ]

        db_session.add_all(history_entries)
        db_session.commit()

        results = db_session.query(MoodHistory).filter(
            MoodHistory.timestamp >= yesterday
        ).all()

        assert len(results) == 2

    def test_query_mood_signals_by_strength(self, db_session):
        """Test querying mood signals by strength."""
        signals = [
            MoodSignal(
                timestamp=datetime.now(timezone.utc),
                signal="BUY",
                strength="weak",
                reasoning="Weak buy signal",
                actions={}
            ),
            MoodSignal(
                timestamp=datetime.now(timezone.utc),
                signal="SELL",
                strength="strong",
                reasoning="Strong sell signal",
                actions={}
            ),
        ]

        db_session.add_all(signals)
        db_session.commit()

        strong_signals = db_session.query(MoodSignal).filter(
            MoodSignal.strength == "strong"
        ).all()

        assert len(strong_signals) == 1
        assert strong_signals[0].signal == "SELL"

    def test_query_indicators_by_type(self, db_session):
        """Test querying indicator values by type."""
        indicators = [
            MoodIndicatorValue(
                timestamp=datetime.now(timezone.utc),
                indicator_type="vix",
                value=15.0,
                score=70.0,
                trend="stable",
                metadata={}
            ),
            MoodIndicatorValue(
                timestamp=datetime.now(timezone.utc),
                indicator_type="market_breadth",
                value=60.0,
                score=20.0,
                trend="improving",
                metadata={}
            ),
        ]

        db_session.add_all(indicators)
        db_session.commit()

        vix_indicators = db_session.query(MoodIndicatorValue).filter(
            MoodIndicatorValue.indicator_type == "vix"
        ).all()

        assert len(vix_indicators) == 1
        assert vix_indicators[0].value == 15.0


class TestMarketMoodDetectionAccuracy:
    """Tests for market mood detection accuracy."""

    @pytest.mark.parametrize("vix_value,expected_score,expected_trend", [
        (10.0, 80.0, "stable"),
        (15.0, 50.0, "stable"),
        (20.0, 0.0, "stable"),
        (30.0, -50.0, "stable"),
        (40.0, -100.0, "stable"),
    ])
    def test_vix_scoring_accuracy(self, vix_value, expected_score, expected_trend):
        """Test VIX indicator scoring accuracy."""
        from src.market_mood.indicators.vix import VIXIndicator

        indicator = VIXIndicator()
        mock_value = IndicatorValue(
            indicator_type=IndicatorType.VIX,
            value=vix_value,
            source="test",
            metadata={"previous": vix_value - 2.0 if vix_value > 10 else vix_value + 2.0},
        )

        with patch.object(indicator.provider, 'fetch_with_retry', return_value=mock_value):
            result = indicator.calculate()

            assert result is not None
            assert result['score'] == expected_score

    @pytest.mark.parametrize("breadth_value,expected_score", [
        (90.0, 80.0),
        (70.0, 40.0),
        (50.0, 0.0),
        (30.0, -40.0),
        (10.0, -80.0),
    ])
    def test_market_breadth_scoring_accuracy(self, breadth_value, expected_score):
        """Test market breadth indicator scoring accuracy."""
        from src.market_mood.indicators.breadth import MarketBreadthIndicator

        indicator = MarketBreadthIndicator()
        mock_value = IndicatorValue(
            indicator_type=IndicatorType.MARKET_BREADTH,
            value=breadth_value,
            source="test",
            metadata={"price_change": 1.0, "date": "2024-01-01"},
        )

        with patch.object(indicator.provider, 'fetch_with_retry', return_value=mock_value):
            result = indicator.calculate()

            assert result is not None
            assert result['score'] == expected_score

    @pytest.mark.parametrize("components,expected_sentiment,expected_score_range", [
        ({"vix": 80.0, "market_breadth": -30.0}, "fear", (-30, 30)),
        ({"vix": -80.0, "market_breadth": 30.0}, "greed", (-30, 30)),
        ({"vix": 0.0, "market_breadth": 0.0, "put_call": 0.0}, "neutral", (-10, 10)),
    ])
    def test_composite_mood_calculation(self, components, expected_sentiment, expected_score_range):
        """Test composite mood calculation accuracy."""
        mood_score = MoodScore.from_components(
            {IndicatorType(k): v for k, v in components.items()}
        )

        assert mood_score.sentiment == expected_sentiment
        assert expected_score_range[0] <= mood_score.overall_score <= expected_score_range[1]


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_indicator_data(self, sample_trading_state):
        """Test handling of empty indicator data."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_current_mood.return_value = {
            "composite_score": 0.0,
            "normalized_score": 0.0,
            "trend": "stable",
            "confidence": 0.0,
            "valid_indicators": [],
            "missing_indicators": ["vix", "market_breadth", "put_call_ratio", "ma_trends"],
            "indicator_details": {},
            "timestamp": datetime.now(timezone.utc),
        }
        mock_detector.get_trading_signals.return_value = {
            "signal": "NO_SIGNAL",
            "mood_classification": "neutral",
            "confidence": 0.0,
            "strength": "none",
            "recommendations": [],
            "timestamp": datetime.now(timezone.utc),
        }
        mock_detector.get_indicator_scores.return_value = {}
        mock_detector.get_position_sizing_suggestion.return_value = {
            "multiplier": 1.0,
            "reason": "No data available",
            "max_position_pct": 0.10,
        }
        mock_detector.get_risk_adjustments.return_value = {
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "max_position_pct": 0.10,
            "risk_level": "moderate",
        }

        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            result = await market_mood_analysis(sample_trading_state)

            assert result["market_mood_data"]["confidence"] == 0.0
            assert len(result["market_mood_data"]["missing_indicators"]) == 4

    @pytest.mark.asyncio
    async def test_detector_exception_handling(self, sample_trading_state):
        """Test handling of detector exceptions."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_current_mood.side_effect = Exception("Network error")

        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            result = await market_mood_analysis(sample_trading_state)

            assert "error" in result
            assert "failed" in result["error"].lower()

    def test_position_sizing_with_zero_quantity(self):
        """Test position sizing with zero base quantity."""
        integration = MarketMoodAutoTraderIntegration()
        integration.enabled = False

        adjusted_quantity, info = integration.get_adjusted_position_size(0)

        assert adjusted_quantity == 0
        assert info["multiplier"] == 1.0

    def test_position_sizing_with_negative_quantity(self):
        """Test position sizing with negative quantity."""
        integration = MarketMoodAutoTraderIntegration()
        integration.enabled = False

        adjusted_quantity, info = integration.get_adjusted_position_size(-100)

        assert adjusted_quantity == -100
        assert info["multiplier"] == 1.0

    def test_unknown_mood_classification_handling(self):
        """Test handling of unknown mood classification."""
        multiplier = _get_position_size_multiplier("unknown_mood")

        assert multiplier == 1.0

    @pytest.mark.asyncio
    async def test_concurrent_mood_requests(self, sample_trading_state, mock_detector):
        """Test handling of concurrent mood requests."""
        import asyncio

        with patch("src.trading_graph.nodes.market_mood_node.MarketMoodDetector", return_value=mock_detector):
            results = await asyncio.gather(
                market_mood_analysis(sample_trading_state),
                market_mood_analysis(sample_trading_state),
                market_mood_analysis(sample_trading_state),
            )

            assert all(r["market_mood_data"]["composite_score"] == 10.0 for r in results)

    def test_mood_history_with_null_components(self, db_session):
        """Test saving mood history with null components."""
        mood_history = MoodHistory(
            timestamp=datetime.now(timezone.utc),
            overall_score=50.0,
            sentiment="neutral",
            confidence=0.5,
            components=None
        )

        db_session.add(mood_history)
        db_session.commit()

        retrieved = db_session.query(MoodHistory).first()
        assert retrieved.components is None

    def test_indicator_value_with_null_metadata(self, db_session):
        """Test saving indicator value with null metadata."""
        indicator_value = MoodIndicatorValue(
            timestamp=datetime.now(timezone.utc),
            indicator_type="vix",
            value=15.0,
            score=70.0,
            trend="stable",
            metadata=None
        )

        db_session.add(indicator_value)
        db_session.commit()

        retrieved = db_session.query(MoodIndicatorValue).first()
        assert retrieved.metadata is None
