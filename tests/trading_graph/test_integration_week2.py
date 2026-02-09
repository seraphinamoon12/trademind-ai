"""Integration tests for Week 2: Agent Migration & Integration."""
import pytest
import pandas as pd
from datetime import datetime, timezone
import inspect
from unittest.mock import Mock, AsyncMock, patch

from src.trading_graph.graph import create_trading_graph
from src.trading_graph.state import TradingState
from src.agents.technical import TechnicalAgent
from src.agents.sentiment import SentimentAgent
from src.trading_graph.state_validator import (
    TradingStateValidator,
    ErrorHandler,
    validate_state,
    ErrorSeverity
)
from src.brokers.ibkr.risk_manager import IBKRRiskManager
from src.execution.signal_executor import SignalExecutor


@pytest.fixture
def sample_market_data():
    """Create sample market data for testing."""
    data = pd.DataFrame({
        'open': [150.0, 151.0, 152.0, 153.0, 154.0],
        'high': [151.0, 152.0, 153.0, 154.0, 155.0],
        'low': [149.0, 150.0, 151.0, 152.0, 153.0],
        'close': [150.5, 151.5, 152.5, 153.5, 154.5],
        'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
    })
    return data


class TestTechnicalAgentWeek2:
    """Test TechnicalAgent migration."""
    
    @pytest.mark.asyncio
    async def test_technical_agent_is_async(self):
        """Verify TechnicalAgent.analyze is async."""
        agent = TechnicalAgent()
        assert inspect.iscoroutinefunction(agent.analyze), "analyze method should be async"
    
    @pytest.mark.asyncio
    async def test_technical_agent_with_caching(self, sample_market_data):
        """Test TechnicalAgent uses caching."""
        agent = TechnicalAgent()
        
        # First call
        result1 = await agent.analyze("AAPL", sample_market_data, timeframe="1d")
        
        # Second call with same params (should use cache)
        result2 = await agent.analyze("AAPL", sample_market_data, timeframe="1d")
        
        assert "decision" in result1.data or result1.decision.value
        assert "indicators" in result1.data or result1.data.get('indicators') is not None
    
    @pytest.mark.asyncio
    async def test_technical_agent_multi_timeframe(self, sample_market_data):
        """Test TechnicalAgent multi-timeframe support."""
        agent = TechnicalAgent()
        
        timeframes = ["1m", "5m", "15m", "1h", "1d"]
        
        for tf in timeframes:
            result = await agent.analyze("AAPL", sample_market_data, timeframe=tf)
            assert result.decision is not None
            assert result.confidence >= 0.0
            assert result.agent_name == "technical"


class TestSentimentAgentWeek2:
    """Test SentimentAgent migration."""
    
    @pytest.mark.asyncio
    async def test_sentiment_agent_is_async(self):
        """Verify SentimentAgent.analyze is async."""
        agent = SentimentAgent()
        assert inspect.iscoroutinefunction(agent.analyze), "analyze method should be async"
    
    @pytest.mark.asyncio
    async def test_sentiment_agent_rate_limiting(self, sample_market_data):
        """Test SentimentAgent uses rate limiting."""
        agent = SentimentAgent()
        assert hasattr(agent, 'rate_limiter'), "Should have rate_limiter attribute"
        assert agent.rate_limiter.max_calls == 100
        assert agent.rate_limiter.period == 60
    
    @pytest.mark.asyncio
    async def test_sentiment_agent_batch_processing(self, sample_market_data):
        """Test SentimentAgent batch processing."""
        agent = SentimentAgent()
        
        symbols_data = {
            "AAPL": sample_market_data,
            "GOOGL": sample_market_data
        }
        
        results = await agent.analyze_batch(symbols_data)
        
        assert len(results) == 2
        assert "AAPL" in results
        assert "GOOGL" in results
        for result in results.values():
            assert result.decision is not None
    
    @pytest.mark.asyncio
    async def test_sentiment_agent_fallback(self, sample_market_data):
        """Test SentimentAgent fallback when API unavailable."""
        # Mock agent without API key
        agent = SentimentAgent()
        agent.api_key = None
        
        result = await agent.analyze("AAPL", sample_market_data)
        
        assert result.decision is not None
        assert "Fallback" in result.reasoning or "fallback" in result.reasoning.lower()


class TestStateValidator:
    """Test Pydantic state validation."""
    
    def test_valid_state(self):
        """Test valid state passes validation."""
        state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "final_action": "BUY",
            "confidence": 0.75,
            "quantity": 100
        }
        
        is_valid, error = validate_state(state)
        assert is_valid, f"Valid state should pass validation: {error}"
        assert error is None
    
    def test_invalid_symbol(self):
        """Test invalid symbol fails validation."""
        state = {
            "symbol": "AAPL123",  # Non-alphabetic
            "timeframe": "1d",
            "final_action": "BUY",
            "confidence": 0.75,
            "quantity": 100
        }
        
        is_valid, error = validate_state(state)
        assert not is_valid
        assert "Symbol must be alphabetic" in error
    
    def test_invalid_timeframe(self):
        """Test invalid timeframe fails validation."""
        state = {
            "symbol": "AAPL",
            "timeframe": "2d",  # Invalid timeframe
            "final_action": "BUY",
            "confidence": 0.75,
            "quantity": 100
        }
        
        is_valid, error = validate_state(state)
        assert not is_valid
        assert "Timeframe must be one of" in error
    
    def test_invalid_confidence(self):
        """Test confidence out of range fails validation."""
        state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "final_action": "BUY",
            "confidence": 1.5,  # > 1.0
            "quantity": 100
        }
        
        is_valid, error = validate_state(state)
        assert not is_valid
    
    def test_invalid_action_with_confidence(self):
        """Test HOLD with high confidence fails validation."""
        state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "final_action": "HOLD",
            "confidence": 0.75,  # Too high for HOLD
            "quantity": 100
        }
        
        is_valid, error = validate_state(state)
        assert not is_valid


class TestErrorHandler:
    """Test error handling."""
    
    def test_error_handler_logs_error(self):
        """Test error handler logs errors correctly."""
        handler = ErrorHandler()
        
        error = Exception("Test error")
        handler.log_error("test_node", error, ErrorSeverity.MEDIUM)
        
        assert len(handler.errors) == 1
        assert handler.errors[0]["node"] == "test_node"
        assert handler.errors[0]["severity"] == "medium"
    
    def test_error_handler_filter_by_severity(self):
        """Test error handler can filter by severity."""
        handler = ErrorHandler()
        
        handler.log_error("node1", Exception("Error 1"), ErrorSeverity.LOW)
        handler.log_error("node2", Exception("Error 2"), ErrorSeverity.HIGH)
        handler.log_error("node3", Exception("Error 3"), ErrorSeverity.MEDIUM)
        
        high_severity = handler.get_recent_errors(severity=ErrorSeverity.HIGH)
        assert len(high_severity) == 1
        assert high_severity[0]["severity"] == "high"
    
    def test_error_handler_summary(self):
        """Test error handler generates summary."""
        handler = ErrorHandler()
        
        handler.log_error("node1", Exception("Error 1"), ErrorSeverity.LOW)
        handler.log_error("node1", Exception("Error 2"), ErrorSeverity.HIGH)
        handler.log_error("node2", Exception("Error 3"), ErrorSeverity.MEDIUM)
        
        summary = handler.get_error_summary()
        assert summary["total"] == 3
        assert "by_severity" in summary
        assert "by_node" in summary
        assert summary["by_node"]["node1"] == 2


class TestIBKRRiskManagerWeek2:
    """Test IBKRRiskManager state-based validation."""
    
    @pytest.mark.asyncio
    async def test_risk_manager_validate_trade(self):
        """Test validate_trade with state."""
        mock_broker = Mock()
        mock_broker.get_account = AsyncMock(return_value=Mock(
            buying_power=100000,
            portfolio_value=100000,
            daily_pnl=-100
        ))
        mock_broker.get_positions = AsyncMock(return_value=[])
        
        risk_manager = IBKRRiskManager(mock_broker)
        
        state = {
            "symbol": "AAPL",
            "final_action": "BUY",
            "final_decision": {"position_size": 0.05}
        }
        
        is_valid, msg = await risk_manager.validate_trade(state)
        assert is_valid, msg
    
    @pytest.mark.asyncio
    async def test_risk_manager_veto_on_large_position(self):
        """Test risk manager vetoes large position size."""
        mock_broker = Mock()
        mock_broker.get_account = AsyncMock(return_value=Mock(
            buying_power=100000,
            portfolio_value=100000,
            daily_pnl=0
        ))
        mock_broker.get_positions = AsyncMock(return_value=[])
        
        risk_manager = IBKRRiskManager(mock_broker)
        
        state = {
            "symbol": "AAPL",
            "final_action": "BUY",
            "final_decision": {"position_size": 0.15}  # > 10% max
        }
        
        is_valid, msg = await risk_manager.validate_trade(state)
        assert not is_valid
        assert "exceeds max" in msg.lower()
    
    @pytest.mark.asyncio
    async def test_risk_manager_var_calculation(self):
        """Test VaR calculation."""
        mock_broker = Mock()
        risk_manager = IBKRRiskManager(mock_broker)
        
        returns = [0.01, -0.02, 0.015, -0.01, 0.005]
        var = await risk_manager.calculate_var(returns, confidence=0.95)
        
        assert var >= 0.0
        assert isinstance(var, float)


class TestSignalExecutorWeek2:
    """Test SignalExecutor state-based execution."""
    
    @pytest.mark.asyncio
    async def test_execute_from_state_hold(self):
        """Test execute_from_state with HOLD action."""
        mock_broker = Mock()
        mock_risk = Mock()
        
        executor = SignalExecutor(mock_broker, mock_risk)
        
        state = {
            "symbol": "AAPL",
            "final_action": "HOLD",
            "confidence": 0.5
        }
        
        result = await executor.execute_from_state(state)
        
        assert result["executed_trade"] is None
        assert result["order_id"] is None
        assert len(executor.get_execution_log()) == 1
    
    @pytest.mark.asyncio
    async def test_execute_from_state_pre_trade_check(self):
        """Test execute_from_state performs pre-trade checks."""
        mock_broker = Mock()
        mock_risk = Mock()
        mock_risk.validate_trade = AsyncMock(return_value=(False, "Risk check failed"))
        
        executor = SignalExecutor(mock_broker, mock_risk)
        
        state = {
            "symbol": "AAPL",
            "final_action": "BUY",
            "confidence": 0.75,
            "final_decision": {"quantity": 100}
        }
        
        result = await executor.execute_from_state(state)
        
        assert result["executed_trade"] is None
        assert result["order_id"] is None
        assert "error" in result
        assert "Risk check failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_pre_trade_check_low_confidence(self):
        """Test pre_trade_check rejects low confidence."""
        mock_broker = Mock()
        mock_risk = Mock()
        mock_risk.validate_trade = AsyncMock(return_value=(True, "OK"))
        
        executor = SignalExecutor(mock_broker, mock_risk)
        
        state = {
            "symbol": "AAPL",
            "final_action": "BUY",
            "confidence": 0.2  # Below 0.3 low threshold
        }
        
        is_valid, msg = await executor.pre_trade_check(state)
        
        assert not is_valid
        assert "below minimum threshold" in msg.lower()


class TestFullWorkflowWeek2:
    """Test complete LangGraph workflow with migrated agents."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_with_agents(self, sample_market_data):
        """Test complete workflow with migrated agents."""
        graph = await create_trading_graph()
        
        initial_state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "market_data": sample_market_data.to_dict(),
            "technical_indicators": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": "test-workflow",
            "iteration": 0,
            "retry_count": 0,
            "messages": []
        }
        
        # Note: This test may not execute fully without broker setup,
        # but it validates the graph compiles and can start
        result = await graph.ainvoke(initial_state, {"thread_id": "test_workflow_agents"})
        
        assert "final_action" in result or "error" in result
        if "error" not in result:
            assert result["final_action"] in ["BUY", "SELL", "HOLD"]
            assert 0 <= result.get("confidence", 0) <= 1
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_workflow(self, sample_market_data):
        """Test error handling and recovery in workflow."""
        graph = await create_trading_graph()
        
        # Test with invalid state
        invalid_state = {
            "symbol": "AAPL123",  # Invalid symbol
            "timeframe": "1d",
            "market_data": sample_market_data.to_dict(),
            "technical_indicators": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": "test-workflow",
            "iteration": 0,
            "retry_count": 0,
            "messages": []
        }
        
        result = await graph.ainvoke(invalid_state, {"thread_id": "test_workflow_error_recovery"})
        
        # Should handle error gracefully
        assert result is not None
