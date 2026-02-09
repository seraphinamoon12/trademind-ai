"""Streaming execution helper for LangGraph trading workflows."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from src.trading_graph.graph import get_trading_graph
from src.config import settings

logger = logging.getLogger(__name__)


async def run_with_streaming(
    symbol: str,
    timeframe: str = "1d",
    stream_mode: str = "values"
):
    """
    Run trading workflow with real-time streaming updates.
    
    Args:
        symbol: Stock symbol to analyze
        timeframe: Timeframe for analysis (e.g., "1d", "1h")
        stream_mode: Streaming mode - "values" (state updates) or "updates" (node outputs)
        
    Yields:
        Events from graph execution in real-time
    """
    graph = await get_trading_graph()
    
    initial_state = {
        "symbol": symbol,
        "timeframe": timeframe,
        "iteration": 0,
        "retry_count": 0,
        "messages": []
    }
    
    config = {
        "configurable": {
            "thread_id": f"trading-{symbol}-{asyncio.get_event_loop().time()}"
        }
    }
    
    logger.info(f"Starting streaming execution for {symbol} (mode: {stream_mode})")
    
    try:
        async for event in graph.astream(initial_state, config=config, stream_mode=stream_mode):
            # Extract node information from event
            if stream_mode == "values":
                # Full state updates
                node = event.get("current_node") or "unknown"
                logger.info(f"Streaming event from node: {node}")
            elif stream_mode == "updates":
                # Node-specific updates
                node = list(event.keys())[0] if event else "unknown"
                logger.info(f"Streaming update from node: {node}")
            
            yield event
            
    except Exception as e:
        logger.error(f"Streaming execution failed for {symbol}: {e}")
        raise


async def run_with_events(
    symbol: str,
    timeframe: str = "1d"
):
    """
    Run trading workflow with detailed event streaming.
    
    Uses astream_events to get detailed execution events including
    task execution, state changes, and debug information.
    
    Args:
        symbol: Stock symbol to analyze
        timeframe: Timeframe for analysis
        
    Yields:
        Detailed events from graph execution
    """
    graph = await get_trading_graph()
    
    initial_state = {
        "symbol": symbol,
        "timeframe": timeframe,
        "iteration": 0,
        "retry_count": 0,
        "messages": []
    }
    
    config = {
        "configurable": {
            "thread_id": f"trading-{symbol}-{asyncio.get_event_loop().time()}"
        }
    }
    
    logger.info(f"Starting event streaming for {symbol}")
    
    try:
        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            yield event
            
    except Exception as e:
        logger.error(f"Event streaming failed for {symbol}: {e}")
        raise


async def run_analysis_with_progress(
    symbol: str,
    timeframe: str = "1d",
    progress_callback=None
):
    """
    Run trading workflow with progress callbacks.
    
    Args:
        symbol: Stock symbol to analyze
        timeframe: Timeframe for analysis
        progress_callback: Optional callback function called with progress updates
                         Callback signature: (node: str, state: dict) -> None
        
    Returns:
        Final state after execution
    """
    final_state = None
    
    async for event in run_with_streaming(symbol, timeframe, stream_mode="values"):
        final_state = event
        
        # Call progress callback if provided
        if progress_callback:
            node = event.get("current_node") or "unknown"
            try:
                await progress_callback(node, event)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    return final_state


class ProgressTracker:
    """Helper class to track and report progress of trading workflow execution."""

    def __init__(self, max_queue_size: int = 100):
        self.nodes_completed: list = []
        self.current_node: Optional[str] = None
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_duration: Optional[float] = None
        self.max_queue_size = max_queue_size
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.dropped_events: int = 0

    async def track_progress(self, node: str, state: dict):
        """Track progress with backpressure handling."""
        event = {
            'node': node,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'progress': self._calculate_progress(state)
        }

        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                self.event_queue.get_nowait()
                self.dropped_events += 1
                self.event_queue.put_nowait(event)
            except asyncio.QueueEmpty:
                pass

            if self.dropped_events % 10 == 0:
                logger.warning(f"Backpressure: dropped {self.dropped_events} events")

    def _calculate_progress(self, state: dict) -> float:
        """Calculate progress percentage."""
        if not state or 'current_node' not in state:
            return 0.0
        return 0.5

    async def consume_events(self, websocket):
        """Consume events with flow control."""
        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await websocket.send_json(event)
                await asyncio.sleep(0.01)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error sending event: {e}")
                break

    async def track(self, node: str, state: dict):
        """Track progress update."""
        if node not in self.nodes_completed:
            self.nodes_completed.append(node)

        self.current_node = node

        await self.track_progress(node, state)

        logger.info(f"Progress: {self.nodes_completed} | Current: {node}")

    def get_summary(self) -> dict:
        """Get execution summary."""
        return {
            "nodes_completed": self.nodes_completed,
            "current_node": self.current_node,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_duration": self.total_duration,
            "node_count": len(self.nodes_completed),
            "dropped_events": self.dropped_events
        }

    def reset(self):
        """Reset progress tracker."""
        self.nodes_completed = []
        self.current_node = None
        self.start_time = None
        self.end_time = None
        self.total_duration = None
        self.dropped_events = 0


async def execute_with_tracking(
    symbol: str,
    timeframe: str = "1d",
    tracker: Optional[ProgressTracker] = None
):
    """
    Execute trading workflow with progress tracking.
    
    Args:
        symbol: Stock symbol to analyze
        timeframe: Timeframe for analysis
        tracker: Optional ProgressTracker instance
        
    Returns:
        Final state and progress summary
    """
    if tracker is None:
        tracker = ProgressTracker()
    
    import time
    tracker.start_time = time.time()
    
    final_state = await run_analysis_with_progress(
        symbol,
        timeframe,
        progress_callback=tracker.track
    )
    
    tracker.end_time = time.time()
    tracker.total_duration = tracker.end_time - tracker.start_time
    
    logger.info(
        f"Execution completed for {symbol} in {tracker.total_duration:.2f}s "
        f"({len(tracker.nodes_completed)} nodes)"
    )
    
    return {
        "state": final_state,
        "summary": tracker.get_summary()
    }


# WebSocket progress broadcaster for real-time updates
class WebSocketProgressBroadcaster:
    """Broadcast progress updates to WebSocket clients."""
    
    def __init__(self):
        from src.api.routes.human_review import active_connections
        self.connections = active_connections
    
    async def broadcast(self, node: str, state: dict):
        """Broadcast progress update to all connected clients."""
        message = {
            "type": "progress_update",
            "node": node,
            "symbol": state.get("symbol"),
            "confidence": state.get("confidence"),
            "current_action": state.get("final_action")
        }
        
        disconnected = set()
        for connection in self.connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        self.connections -= disconnected
