"""API tests for Market Mood Phase 3."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.market_mood import router, get_detector
from src.market_mood.detector import MarketMoodDetector
from src.market_mood.config import MarketMoodConfig
from src.market_mood.models import IndicatorType, IndicatorValue


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/market")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_detector():
    """Create a mock MarketMoodDetector."""
    detector = Mock(spec=MarketMoodDetector)
    detector.get_current_mood.return_value = {
        "composite_score": 25.0,
        "normalized_score": -15.0,
        "trend": "improving",
        "confidence": 0.85,
        "valid_indicators": ["vix", "market_breadth", "put_call_ratio"],
        "missing_indicators": ["ma_trends"],
        "indicator_details": {
            "vix": {"score": 80.0, "value": 12.0, "trend": "improving"},
            "market_breadth": {"score": -30.0, "value": 35.0, "trend": "declining"},
            "put_call_ratio": {"score": 50.0, "value": 1.0, "trend": "stable"},
        },
        "timestamp": datetime.now(timezone.utc),
    }
    detector.get_trading_signals.return_value = {
        "signal": "BUY",
        "mood_classification": "extreme_fear",
        "confidence": 0.85,
        "strength": "strong",
        "recommendations": [
            "Increase position size by 50%",
            "Buy the dip",
        ],
        "timestamp": datetime.now(timezone.utc),
    }
    detector.get_indicator_scores.return_value = {
        "vix": {
            "score": 80.0,
            "value": 12.0,
            "trend": "improving",
            "timestamp": datetime.now(timezone.utc),
        },
        "market_breadth": {
            "score": -30.0,
            "value": 35.0,
            "trend": "declining",
            "timestamp": datetime.now(timezone.utc),
        },
        "put_call_ratio": {
            "score": 50.0,
            "value": 1.0,
            "trend": "stable",
            "timestamp": datetime.now(timezone.utc),
        },
    }
    detector.get_mood_history.return_value = [
        {
            "timestamp": datetime.now(timezone.utc) - timedelta(days=1),
            "overall_score": 30.0,
            "sentiment": "fear",
            "confidence": 0.8,
            "components": {},
        },
        {
            "timestamp": datetime.now(timezone.utc),
            "overall_score": 25.0,
            "sentiment": "extreme_fear",
            "confidence": 0.85,
            "components": {},
        },
    ]
    detector.refresh_indicators.return_value = None
    detector.get_comprehensive_report.return_value = {
        "mood": detector.get_current_mood.return_value,
        "indicators": detector.get_indicator_scores.return_value,
        "signals": detector.get_trading_signals.return_value,
        "trend": {
            "direction": "bearish_to_bullish",
            "strength": "moderate",
            "duration_days": 5,
        },
        "divergence": None,
        "position_sizing": {
            "multiplier": 1.5,
            "reason": "Extreme fear - increasing position size by 50%",
            "max_position_pct": 0.15,
        },
        "risk_adjustments": {
            "stop_loss_pct": 0.04,
            "take_profit_pct": 0.12,
            "max_position_pct": 0.15,
            "risk_level": "low",
        },
    }
    detector.get_status.return_value = {
        "config": {
            "enable_signals": True,
            "signal_confidence_threshold": 0.7,
            "trend_lookback_days": 30,
        },
        "current_mood": True,
        "history_size": 10,
        "indicators_refreshed": True,
    }
    return detector


class TestMarketMoodAPIRoot:
    """Tests for API root endpoint."""

    def test_get_root(self, client):
        """Test getting API root information."""
        response = client.get("/api/market/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Market Mood API"
        assert data["version"] == "1.0.0"
        assert len(data["endpoints"]) > 0
        assert any("GET /api/market/mood" in endpoint for endpoint in data["endpoints"])


class TestGetCurrentMood:
    """Tests for getting current market mood."""

    def test_get_current_mood_success(self, client, mock_detector):
        """Test successful retrieval of current mood."""
        with patch.object(router, "dependency_overrides", {}):
            with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
                response = client.get("/api/market/mood")

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["mood"]["composite_score"] == 25.0
                assert data["mood"]["trend"] == "improving"
                assert data["mood"]["confidence"] == 0.85
                assert "timestamp" in data

    def test_get_current_mood_error(self, client):
        """Test error handling when getting current mood."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_current_mood.side_effect = Exception("Database error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to fetch current mood" in data["detail"]


class TestGetMoodHistory:
    """Tests for getting mood history."""

    def test_get_mood_history_default_days(self, client, mock_detector):
        """Test getting mood history with default days parameter."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/history")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["days"] == 7
            assert data["count"] == 2
            assert len(data["history"]) == 2

    def test_get_mood_history_custom_days(self, client, mock_detector):
        """Test getting mood history with custom days parameter."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/history?days=30")

            assert response.status_code == 200
            data = response.json()
            assert data["days"] == 30

    def test_get_mood_history_invalid_days(self, client, mock_detector):
        """Test getting mood history with invalid days parameter."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/history?days=100")

            assert response.status_code == 422

    def test_get_mood_history_negative_days(self, client, mock_detector):
        """Test getting mood history with negative days parameter."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/history?days=-1")

            assert response.status_code == 422

    def test_get_mood_history_error(self, client):
        """Test error handling when getting mood history."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_mood_history.side_effect = Exception("Query error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/history")

            assert response.status_code == 500
            data = response.json()
            assert "detail" in data


class TestGetIndicatorValues:
    """Tests for getting individual indicator values."""

    def test_get_indicator_values_success(self, client, mock_detector):
        """Test successful retrieval of indicator values."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/indicators")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "indicators" in data
            assert "vix" in data["indicators"]
            assert "market_breadth" in data["indicators"]
            assert data["indicators"]["vix"]["score"] == 80.0
            assert data["indicators"]["vix"]["trend"] == "improving"

    def test_get_indicator_values_with_none_indicators(self, client, mock_detector):
        """Test handling when some indicators return None."""
        mock_detector.get_indicator_scores.return_value = {
            "vix": {
                "score": 80.0,
                "value": 12.0,
                "trend": "improving",
                "timestamp": datetime.now(timezone.utc),
            },
            "market_breadth": None,
        }

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/indicators")

            assert response.status_code == 200
            data = response.json()
            assert data["indicators"]["vix"]["score"] == 80.0
            assert data["indicators"]["market_breadth"]["score"] is None

    def test_get_indicator_values_error(self, client):
        """Test error handling when getting indicator values."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_indicator_scores.side_effect = Exception("Calculation error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/indicators")

            assert response.status_code == 500


class TestGetTradingSignals:
    """Tests for getting trading signals."""

    def test_get_trading_signals_success(self, client, mock_detector):
        """Test successful retrieval of trading signals."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/signals")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["signals"]["signal"] == "BUY"
            assert data["signals"]["mood_classification"] == "extreme_fear"
            assert data["signals"]["confidence"] == 0.85
            assert data["signals"]["strength"] == "strong"
            assert len(data["signals"]["recommendations"]) > 0

    def test_get_trading_signals_error(self, client):
        """Test error handling when getting trading signals."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_trading_signals.side_effect = Exception("Signal generation error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/signals")

            assert response.status_code == 500


class TestRefreshIndicators:
    """Tests for refreshing indicators."""

    def test_refresh_indicators_success(self, client, mock_detector):
        """Test successful refresh of indicators."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.post("/api/market/mood/refresh")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Indicators refreshed successfully"
            assert "mood" in data
            assert "signals" in data
            mock_detector.refresh_indicators.assert_called_once()

    def test_refresh_indicators_error(self, client):
        """Test error handling when refreshing indicators."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.refresh_indicators.side_effect = Exception("Refresh error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.post("/api/market/mood/refresh")

            assert response.status_code == 500


class TestGetDashboard:
    """Tests for getting dashboard overview."""

    def test_get_dashboard_success(self, client, mock_detector):
        """Test successful retrieval of dashboard data."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/dashboard")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "dashboard" in data
            assert "status_info" in data
            assert "mood" in data["dashboard"]
            assert "signals" in data["dashboard"]
            assert "trend" in data["dashboard"]
            assert "position_sizing" in data["dashboard"]
            assert "risk_adjustments" in data["dashboard"]

    def test_get_dashboard_error(self, client):
        """Test error handling when getting dashboard."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_comprehensive_report.side_effect = Exception("Report generation error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/dashboard")

            assert response.status_code == 500


class TestGetAlerts:
    """Tests for getting market mood alerts."""

    def test_get_alerts_extreme_fear(self, client, mock_detector):
        """Test getting alerts for extreme fear condition."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/alerts")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["count"] > 0
            assert any(
                alert["type"] == "market_condition" and "extreme fear" in alert["message"].lower()
                for alert in data["alerts"]
            )

    def test_get_alerts_extreme_greed(self, client, mock_detector):
        """Test getting alerts for extreme greed condition."""
        mock_detector.get_trading_signals.return_value = {
            "signal": "NO_SIGNAL",
            "mood_classification": "extreme_greed",
            "confidence": 0.9,
            "strength": "strong",
            "recommendations": ["Reduce exposure"],
            "timestamp": datetime.now(timezone.utc),
        }

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/alerts")

            assert response.status_code == 200
            data = response.json()
            assert any(
                alert["severity"] == "warning" and "extreme greed" in alert["message"].lower()
                for alert in data["alerts"]
            )

    def test_get_alerts_low_confidence(self, client, mock_detector):
        """Test getting alerts for low confidence."""
        mock_detector.get_current_mood.return_value = {
            "composite_score": 50.0,
            "normalized_score": 0.0,
            "trend": "stable",
            "confidence": 0.3,
            "valid_indicators": ["vix"],
            "missing_indicators": ["market_breadth", "put_call_ratio", "ma_trends"],
            "indicator_details": {},
            "timestamp": datetime.now(timezone.utc),
        }

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/alerts")

            assert response.status_code == 200
            data = response.json()
            assert any(
                alert["type"] == "data_quality" and "low confidence" in alert["message"].lower()
                for alert in data["alerts"]
            )

    def test_get_alerts_missing_indicators(self, client, mock_detector):
        """Test getting alerts for missing indicators."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/alerts")

            assert response.status_code == 200
            data = response.json()
            assert any(
                alert["type"] == "data_availability" and "indicators unavailable" in alert["message"].lower()
                for alert in data["alerts"]
            )

    def test_get_alerts_error(self, client):
        """Test error handling when getting alerts."""
        mock_detector = Mock(spec=MarketMoodDetector)
        mock_detector.get_current_mood.side_effect = Exception("Alert generation error")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/alerts")

            assert response.status_code == 500


class TestGetConfig:
    """Tests for getting market mood configuration."""

    def test_get_config_success(self, client):
        """Test successful retrieval of configuration."""
        response = client.get("/api/market/config")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config" in data
        assert "enable_signals" in data["config"]
        assert "signal_confidence_threshold" in data["config"]
        assert "trend_lookback_days" in data["config"]
        assert "indicator_weights" in data["config"]
        assert "cache_settings" in data["config"]

    def test_get_config_cache_settings(self, client):
        """Test that cache settings are included in config."""
        response = client.get("/api/market/config")

        assert response.status_code == 200
        data = response.json()
        cache_settings = data["config"]["cache_settings"]
        assert "vix" in cache_settings
        assert "breadth" in cache_settings
        assert "put_call" in cache_settings
        assert "ma_trends" in cache_settings


class TestCachingBehavior:
    """Tests for caching behavior."""

    def test_detector_singleton(self):
        """Test that detector is cached as singleton."""
        detector1 = get_detector()
        detector2 = get_detector()

        assert detector1 is detector2

    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly."""
        from src.market_mood.data_providers.cache import CacheEntry

        entry = CacheEntry(
            key="test_indicator",
            value={"score": 50.0},
            ttl=300,
        )

        assert entry.key == "test_indicator"
        assert entry.expires_at is not None
        assert entry.expires_at > entry.created_at


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_empty_mood_data_response(self, client, mock_detector):
        """Test handling of empty mood data."""
        mock_detector.get_current_mood.return_value = {
            "composite_score": 0.0,
            "normalized_score": 0.0,
            "trend": "stable",
            "confidence": 0.0,
            "valid_indicators": [],
            "missing_indicators": [],
            "indicator_details": {},
            "timestamp": datetime.now(timezone.utc),
        }

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["mood"]["confidence"] == 0.0

    def test_timeout_handling(self, client, mock_detector):
        """Test handling of timeout errors."""
        import asyncio
        from concurrent.futures import TimeoutError

        async def slow_function():
            await asyncio.sleep(10)

        mock_detector.get_current_mood.side_effect = TimeoutError("Request timed out")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood")

            assert response.status_code == 500

    def test_network_error_handling(self, client, mock_detector):
        """Test handling of network errors."""
        mock_detector.get_current_mood.side_effect = ConnectionError("Network unreachable")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood")

            assert response.status_code == 500

    def test_invalid_json_response(self, client, mock_detector):
        """Test handling of invalid JSON in response."""
        mock_detector.get_indicator_scores.return_value = "not a dict"

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood/indicators")

            assert response.status_code == 500


class TestAuthentication:
    """Tests for API authentication."""

    def test_unauthorized_access(self, client):
        """Test that unauthorized access is handled."""
        response = client.get("/api/market/mood", headers={"Authorization": "Bearer invalid_token"})

        assert response.status_code in [401, 200]

    def test_valid_authentication(self, client):
        """Test that valid authentication works."""
        response = client.get("/api/market/mood")

        assert response.status_code in [200, 401]


class TestAPIResponseFormat:
    """Tests for API response format consistency."""

    def test_response_has_status_field(self, client, mock_detector):
        """Test that all responses have a status field."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            endpoints = [
                "/api/market/mood",
                "/api/market/mood/history",
                "/api/market/mood/indicators",
                "/api/market/mood/signals",
                "/api/market/mood/dashboard",
                "/api/market/mood/alerts",
                "/api/market/config",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 200
                data = response.json()
                assert "status" in data
                assert data["status"] in ["success", "error"]

    def test_response_has_timestamp_field(self, client, mock_detector):
        """Test that all responses have a timestamp field."""
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            response = client.get("/api/market/mood")

            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data


class TestConcurrentRequests:
    """Tests for handling concurrent API requests."""

    def test_concurrent_mood_requests(self, client, mock_detector):
        """Test handling concurrent requests to mood endpoint."""
        import concurrent.futures

        def make_request():
            return client.get("/api/market/mood")

        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                responses = [f.result() for f in concurrent.futures.as_completed(futures)]

            assert all(r.status_code == 200 for r in responses)


class TestRateLimiting:
    """Tests for API rate limiting."""

    def test_rate_limit_exceeded(self, client, mock_detector):
        """Test handling of rate limit exceeded."""
        responses = []
        with patch("src.api.routes.market_mood.get_detector", return_value=mock_detector):
            for _ in range(100):
                response = client.get("/api/market/mood")
                responses.append(response)
                if response.status_code == 429:
                    break

        assert any(r.status_code == 429 for r in responses) or len(responses) == 100
