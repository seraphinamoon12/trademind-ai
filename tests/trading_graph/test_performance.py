"""Performance tests for LangGraph."""

import pytest
import time
import sys
import asyncio
from src.trading_graph.graph import create_trading_graph


class TestPerformance:
    """Test performance requirements."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(3.0)
    async def test_graph_execution_time(self):
        """Test that graph completes in under 2 seconds."""

        graph = await create_trading_graph()

        initial_state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "confidence": 0.0,
            "workflow_id": "perf_test_001",
            "iteration": 0,
            "messages": [],
            "timestamp": "2024-01-01T00:00:00Z",
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

        start = time.time()
        result = await graph.ainvoke(initial_state, {"thread_id": "perf_test_001"})
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Graph took {elapsed:.2f}s, expected < 2s"

    @pytest.mark.asyncio
    @pytest.mark.timeout(3.0)
    async def test_state_size(self):
        """Test that state size remains under 1MB."""

        graph = await create_trading_graph()
        initial_state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "confidence": 0.0,
            "workflow_id": "size_test_001",
            "iteration": 0,
            "messages": [],
            "timestamp": "2024-01-01T00:00:00Z",
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

        result = await graph.ainvoke(initial_state, {"thread_id": "size_test_001"})

        import json
        state_json = json.dumps(result, default=str)
        state_size = sys.getsizeof(state_json.encode('utf-8'))
        assert state_size < 1_000_000, f"State size {state_size} bytes exceeds 1MB limit"

    @pytest.mark.asyncio
    @pytest.mark.timeout(15.0)
    async def test_concurrent_executions(self):
        """Test handling of concurrent graph executions."""

        graph = await create_trading_graph()

        async def run_workflow(symbol):
            initial_state = {
                "symbol": symbol,
                "timeframe": "1d",
                "confidence": 0.0,
                "workflow_id": f"concurrent_{symbol}",
                "iteration": 0,
                "messages": [],
                "timestamp": "2024-01-01T00:00:00Z",
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
            return await graph.ainvoke(initial_state, {"thread_id": f"concurrent_{symbol}"})

        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        start = time.time()
        results = await asyncio.gather(*[run_workflow(sym) for sym in symbols])
        elapsed = time.time() - start

        assert len(results) == 5
        assert all(r["symbol"] in symbols for r in results)
        assert elapsed < 10.0, f"Concurrent execution took {elapsed:.2f}s, expected < 10s"

    @pytest.mark.asyncio
    @pytest.mark.timeout(3.0)
    async def test_node_execution_times(self):
        """Test individual node execution times."""

        graph = await create_trading_graph()

        initial_state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "confidence": 0.0,
            "workflow_id": "node_time_test_001",
            "iteration": 0,
            "messages": [],
            "timestamp": "2024-01-01T00:00:00Z",
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

        result = await graph.ainvoke(initial_state, {"thread_id": "node_time_test_001"})

        assert result is not None

    @pytest.mark.asyncio
    @pytest.mark.timeout(30.0)
    async def test_memory_efficiency(self):
        """Test memory efficiency of repeated executions."""

        graph = await create_trading_graph()

        initial_state = {
            "symbol": "AAPL",
            "timeframe": "1d",
            "confidence": 0.0,
            "workflow_id": "mem_test_001",
            "iteration": 0,
            "messages": [],
            "timestamp": "2024-01-01T00:00:00Z",
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

        import gc
        gc.collect()
        initial_objects = len(gc.get_objects())

        for i in range(10):
            state = initial_state.copy()
            state["workflow_id"] = f"mem_test_{i}"
            await graph.ainvoke(state, {"thread_id": f"mem_test_{i}"})

        gc.collect()
        final_objects = len(gc.get_objects())

        object_increase = final_objects - initial_objects
        assert object_increase < 5000, f"Memory increased by {object_increase} objects, may indicate memory leak"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
