# LangGraph Quick Start Guide

This guide helps you get started with the LangGraph migration for TradeMind AI.

## Prerequisites

```bash
# Install LangGraph and dependencies
pip install -U langgraph>=1.0.8 langchain-core langchain-community
```

## Basic Usage

### Running a Simple Analysis

```python
from src.langgraph.graph import trading_graph

# Initial state
initial_state = {
    "symbol": "AAPL",
    "timeframe": "1d",
    "confidence": 0.0,
    "workflow_id": "demo_001",
    "iteration": 0,
    "messages": []
}

# Configuration for persistence
config = {
    "thread_id": "demo_001",
    "recursion_limit": 10
}

# Execute graph
result = trading_graph.invoke(initial_state, config)

print(result)
```

### Streaming Execution

```python
# Stream updates in real-time
for event in trading_graph.stream(initial_state, config, stream_mode="values"):
    print(f"[{event.get('timestamp', '')}] Node: {event.get('current_node', '')}")
```

### Resume from Checkpoint

```python
from langgraph.types import Command

# Resume after human approval
result = trading_graph.invoke(
    Command(resume={
        "human_approved": True,
        "human_feedback": "User approved the trade"
    }),
    config
)
```

## Architecture Overview

```
START → Fetch Data → Technical Analysis → Sentiment Analysis
                                        ↓
                                 (if conflicting)
                                        ↓
                                  Debate Protocol
                                        ↓
                                  Risk Assessment
                                        ↓
                                   Make Decision
                                        ↓
                                  (if low confidence)
                                        ↓
                                  Human Review
                                        ↓
                                   Execute Trade → END
```

## Next Steps

1. Implement remaining nodes in `src/langgraph/nodes/`
2. Add tests in `tests/langgraph/`
3. Integrate with FastAPI endpoints
4. Enable LangSmith tracing for debugging
5. Run end-to-end tests

## Configuration

### Environment Variables

```bash
# LangSmith (optional, for tracing)
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="your-api-key"

# LangGraph Checkpoints
export CHECKPOINT_DB="data/checkpoints/trading_agent_checkpoints.db"
```

### Feature Flags

```python
# Enable/disable LangGraph mode
USE_LANGGRAPH = os.getenv("USE_LANGGRAPH", "false").lower() == "true"

if USE_LANGGRAPH:
    from src.langgraph.graph import trading_graph
else:
    # Use original orchestrator
    from src.agents.orchestrator import Orchestrator
```

## Testing

```bash
# Run LangGraph tests
pytest tests/langgraph/ -v

# Run specific test
pytest tests/langgraph/test_graph.py::test_fetch_data -v
```

## Troubleshooting

### Common Issues

**Issue:** Graph execution stalls
- Check: All edges are properly connected
- Check: No unreachable nodes
- Solution: Use `graph.get_graph().print_ascii()` to visualize

**Issue:** State not persisting
- Check: Checkpointer is initialized
- Check: Database file permissions
- Solution: Verify `CHECKPOINT_DB` path is writable

**Issue:** Human interrupt not triggering
- Check: Confidence threshold in `should_review()`
- Check: Node calling `interrupt()`
- Solution: Add logging to verify condition

## Documentation

- Full Migration Plan: `LANGGRAPH_MIGRATION_PLAN.md`
- LangGraph Docs: https://python.langchain.com/docs/langgraph/
- LangSmith: https://smith.langchain.com/

## Support

- Issues: Create GitHub issue
- Questions: LangChain Forum - https://forum.langchain.com/
