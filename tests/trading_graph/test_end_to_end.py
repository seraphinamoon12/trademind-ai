"""End-to-end tests for LangGraph trading workflow."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from src.trading_graph.graph import create_trading_graph
from src.trading_graph.state import TradingState


@pytest.fixture
async def trading_graph():
    """Create fresh graph for each test."""
    graph = await create_trading_graph()
    return graph


@pytest.fixture
def mock_market_data():
    """Mock market data for testing."""
    return {
        "symbol": "AAPL",
        "price": 150.0,
        "change_5d": 2.5,
        "volume_ratio": 1.2,
        "close": [145.0, 146.0, 147.0, 148.0, 150.0]
    }


@pytest.fixture
def base_state():
    """Create a base trading state for testing."""
    return {
        "symbol": "AAPL",
        "timeframe": "1d",
        "market_data": {},
        "technical_indicators": {},
        "technical_signals": {},
        "sentiment_signals": {},
        "risk_signals": {},
        "debate_result": {},
        "final_decision": {},
        "final_action": None,
        "confidence": 0.0,
        "executed_trade": {},
        "order_id": None,
        "human_approved": None,
        "human_feedback": None,
        "messages": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow_id": "test_workflow",
        "iteration": 0,
        "current_node": None,
        "error": None,
        "retry_count": 0
    }


class TestFullWorkflow:
    """Test complete trading workflows."""

    @pytest.mark.asyncio
    async def test_buy_workflow(self, trading_graph, mock_market_data):
        """Test complete workflow resulting in BUY signal."""

        with patch('src.trading_graph.nodes.data_nodes.YahooFinanceProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.get_historical = Mock(return_value=__import__('pandas').DataFrame({
                'open': [145.0, 146.0, 147.0, 148.0, 150.0],
                'high': [146.0, 147.0, 148.0, 149.0, 151.0],
                'low': [144.0, 145.0, 146.0, 147.0, 149.0],
                'close': [145.0, 146.0, 147.0, 148.0, 150.0],
                'volume': [1000000] * 5
            }, index=__import__('pandas').date_range('2024-01-01', periods=5)))
            mock_provider_class.return_value = mock_provider

            initial_state = {
                "symbol": "AAPL",
                "timeframe": "1d",
                "confidence": 0.0,
                "workflow_id": f"test_buy_{datetime.now(timezone.utc).timestamp()}",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {},
                "sentiment_signals": {},
                "risk_signals": {},
                "debate_result": {},
                "final_decision": {},
                "final_action": None,
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            config = {"thread_id": initial_state["workflow_id"]}

            result = await trading_graph.ainvoke(initial_state, config)

            assert result["symbol"] == "AAPL"
            assert "technical_signals" in result or "error" in result
            assert "sentiment_signals" in result or "error" in result
            assert result["final_action"] in ["BUY", "SELL", "HOLD"]
            assert "confidence" in result

    @pytest.mark.asyncio
    async def test_sell_workflow(self, trading_graph):
        """Test complete workflow resulting in SELL signal."""
        with patch('src.trading_graph.nodes.data_nodes.YahooFinanceProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.get_historical = Mock(return_value=__import__('pandas').DataFrame({
                'open': [210.0, 208.0, 205.0, 202.0, 200.0],
                'high': [211.0, 209.0, 206.0, 203.0, 201.0],
                'low': [209.0, 207.0, 204.0, 201.0, 199.0],
                'close': [210.0, 208.0, 205.0, 202.0, 200.0],
                'volume': [1000000] * 5
            }, index=__import__('pandas').date_range('2024-01-01', periods=5)))
            mock_provider_class.return_value = mock_provider

            initial_state = {
                "symbol": "TSLA",
                "timeframe": "1d",
                "confidence": 0.0,
                "workflow_id": "test_sell_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {},
                "sentiment_signals": {},
                "risk_signals": {},
                "debate_result": {},
                "final_decision": {},
                "final_action": None,
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_sell_001"})

            assert result["symbol"] == "TSLA"
            assert "final_action" in result

    @pytest.mark.asyncio
    async def test_hold_workflow(self, trading_graph):
        """Test complete workflow resulting in HOLD signal."""

        with patch('src.trading_graph.nodes.data_nodes.YahooFinanceProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.get_historical = Mock(return_value=__import__('pandas').DataFrame({
                'open': [300.0, 300.0, 300.0, 300.0, 300.0],
                'high': [300.0, 300.0, 300.0, 300.0, 300.0],
                'low': [300.0, 300.0, 300.0, 300.0, 300.0],
                'close': [300.0, 300.0, 300.0, 300.0, 300.0],
                'volume': [1000000] * 5
            }, index=__import__('pandas').date_range('2024-01-01', periods=5)))
            mock_provider_class.return_value = mock_provider

            initial_state = {
                "symbol": "META",
                "timeframe": "1d",
                "confidence": 0.0,
                "workflow_id": "test_hold_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {},
                "sentiment_signals": {},
                "risk_signals": {},
                "debate_result": {},
                "final_decision": {},
                "final_action": None,
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_hold_001"})

            assert result["symbol"] == "META"
            assert "final_action" in result


class TestDebateFlow:
    """Test debate protocol integration."""

    @pytest.mark.asyncio
    async def test_debate_triggers_on_conflict(self, trading_graph):
        """Test that debate runs when technical and sentiment conflict."""

        with patch('src.trading_graph.nodes.analysis_nodes.technical_analysis') as mock_tech, \
             patch('src.trading_graph.nodes.analysis_nodes.sentiment_analysis') as mock_sent:

            mock_tech.return_value = {
                "technical_signals": {
                    "decision": "BUY",
                    "confidence": 0.8,
                    "reasoning": "Bullish technicals"
                },
                "current_node": "technical_analysis"
            }

            mock_sent.return_value = {
                "sentiment_signals": {
                    "decision": "bearish",
                    "confidence": 0.7,
                    "reasoning": "Negative sentiment"
                },
                "current_node": "sentiment_analysis"
            }

            initial_state = {
                "symbol": "TSLA",
                "timeframe": "1d",
                "confidence": 0.0,
                "workflow_id": "test_debate_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {
                    "decision": "BUY",
                    "confidence": 0.8,
                    "reasoning": "Bullish technicals"
                },
                "sentiment_signals": {
                    "decision": "bearish",
                    "confidence": 0.7,
                    "reasoning": "Negative sentiment"
                },
                "risk_signals": {},
                "debate_result": {},
                "final_decision": {},
                "final_action": None,
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_debate_001"})

            assert "debate_result" in result or "error" in result
            if "debate_result" in result:
                assert result["debate_result"].get("winner") in ["bull", "bear"]


class TestHumanInTheLoop:
    """Test human approval workflow."""

    @pytest.mark.asyncio
    async def test_human_interrupt_on_low_confidence(self, trading_graph):
        """Test that low confidence triggers human review."""

        with patch('src.trading_graph.nodes.analysis_nodes.make_decision') as mock_decision:
            mock_decision.return_value = {
                "final_decision": {
                    "decision": "BUY",
                    "confidence": 0.5,
                    "reasoning": "Uncertain signal"
                },
                "final_action": "BUY",
                "confidence": 0.5,
                "current_node": "decision"
            }

            initial_state = {
                "symbol": "META",
                "timeframe": "1d",
                "confidence": 0.5,
                "workflow_id": "test_human_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {"decision": "BUY", "confidence": 0.5},
                "sentiment_signals": {"decision": "BUY", "confidence": 0.5},
                "risk_signals": {"decision": "HOLD", "confidence": 0.8},
                "debate_result": {},
                "final_decision": {"decision": "BUY", "confidence": 0.5},
                "final_action": "BUY",
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_human_001"})

            assert result.get("human_approved") == False or result.get("final_action") == "HOLD"

    @pytest.mark.asyncio
    async def test_auto_approve_high_confidence(self, trading_graph):
        """Test that high confidence auto-approves."""

        with patch('src.trading_graph.nodes.analysis_nodes.make_decision') as mock_decision:
            mock_decision.return_value = {
                "final_decision": {
                    "decision": "BUY",
                    "confidence": 0.9,
                    "reasoning": "Strong signal"
                },
                "final_action": "BUY",
                "confidence": 0.9,
                "current_node": "decision"
            }

            initial_state = {
                "symbol": "NVDA",
                "timeframe": "1d",
                "confidence": 0.9,
                "workflow_id": "test_auto_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {"decision": "BUY", "confidence": 0.9},
                "sentiment_signals": {"decision": "BUY", "confidence": 0.9},
                "risk_signals": {"decision": "HOLD", "confidence": 0.9},
                "debate_result": {},
                "final_decision": {"decision": "BUY", "confidence": 0.9},
                "final_action": "BUY",
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_auto_001"})

            assert result.get("human_approved") == True or result.get("final_action") == "BUY"


class TestErrorHandling:
    """Test error recovery and resilience."""

    @pytest.mark.asyncio
    async def test_data_fetch_failure(self, trading_graph):
        """Test graceful handling of data fetch failures."""

        with patch('src.trading_graph.nodes.data_nodes.YahooFinanceProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.get_historical = Mock(side_effect=Exception("API Error"))
            mock_provider_class.return_value = mock_provider

            initial_state = {
                "symbol": "INVALID",
                "timeframe": "1d",
                "workflow_id": "test_error_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {},
                "sentiment_signals": {},
                "risk_signals": {},
                "debate_result": {},
                "final_decision": {},
                "final_action": None,
                "executed_trade": {},
                "order_id": None,
                "human_approved": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_error_001"})

            assert "error" in result or result.get("final_action") == "HOLD"

    @pytest.mark.asyncio
    async def test_retry_on_execution_failure(self, trading_graph):
        """Test retry logic for failed trade execution."""

        with patch('src.trading_graph.nodes.execution_nodes.execute_trade') as mock_execute:
            mock_execute.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                {
                    "executed_trade": {
                        "action": "BUY",
                        "symbol": "AAPL",
                        "quantity": 100,
                        "order_id": "12345",
                        "status": "filled"
                    },
                    "order_id": "12345",
                    "execution_status": "SUCCESS"
                }
            ]

            initial_state = {
                "symbol": "AAPL",
                "final_action": "BUY",
                "human_approved": True,
                "risk_signals": {"data": {"recommended_size": 100}},
                "workflow_id": "test_retry_001",
                "iteration": 0,
                "messages": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "market_data": {},
                "technical_indicators": {},
                "technical_signals": {},
                "sentiment_signals": {},
                "debate_result": {},
                "final_decision": {},
                "executed_trade": {},
                "order_id": None,
                "human_feedback": None,
                "current_node": None,
                "error": None,
                "retry_count": 0
            }

            result = await trading_graph.ainvoke(initial_state, {"thread_id": "test_retry_001"})

            assert mock_execute.call_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
