# LangGraph Integration for TradeMind AI

This directory contains the LangGraph-based agent orchestration system for TradeMind AI, replacing the linear multi-agent architecture with a stateful, graph-based workflow.

## Migration Status

**Phase:** 1 of 4 (Foundation)
**Progress:** Basic structure created, nodes pending migration

## Directory Structure

```
src/langgraph/
├── __init__.py              # Package exports
├── state.py                  # TradingState schema (TypedDict)
├── graph.py                  # Main graph construction
├── persistence.py             # Checkpointer configuration
├── nodes/                    # Node implementations
│   ├── __init__.py
│   ├── data_nodes.py          # Market data fetching
│   ├── analysis_nodes.py      # Technical/sentiment analysis (TODO)
│   ├── debate_nodes.py        # Bull/bear debate (TODO)
│   └── execution_nodes.py     # Risk, execution, human review (TODO)
└── README.md                 # This file
```

## Architecture

### Current vs Migrated

| Aspect | Current | LangGraph |
|--------|----------|-----------|
| Flow | Linear pipeline | Graph with conditional edges |
| State | Scattered | Centralized TypedDict |
| Persistence | Database only | Native checkpointing |
| Human Oversight | None | Built-in interrupts |
| Debugging | Logs only | LangSmith traces |

### Graph Structure

```
                    START
                      │
                      ▼
               Fetch Market Data
                      │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
    Technical Analysis    Sentiment Analysis
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
                (Should Debate?)
                   /          \
             Yes/              \No
                │                  │
                ▼                  │
            Debate Protocol          │
                │                  │
                └──────────┬───────┘
                           │
                           ▼
                    Risk Assessment
                           │
                           ▼
                    Make Decision
                           │
                 (Should Review?)
                    /          \
               Yes/              \No
                  │                  │
                  ▼                  │
             Human Review            │
                  │                  │
                  └──────────┬───────┘
                             │
                             ▼
                      (Execute or Hold?)
                      /                \
                Execute/                \Hold
                    │                       │
                    ▼                       ▼
               Execute Trade →            END
```

## State Schema

```python
class TradingState(TypedDict):
    # Input
    symbol: str
    timeframe: str

    # Market Data
    market_data: Optional[Dict]
    technical_indicators: Optional[Dict]

    # Agent Signals
    technical_signals: Optional[Dict]
    sentiment_signals: Optional[Dict]
    risk_signals: Optional[Dict]
    debate_result: Optional[Dict]

    # Decision
    final_decision: Optional[Dict]
    final_action: Optional[Literal["BUY", "SELL", "HOLD"]]
    confidence: float

    # Execution
    executed_trade: Optional[Dict]
    order_id: Optional[str]

    # Human Feedback
    human_approved: Optional[bool]
    human_feedback: Optional[str]

    # Messages (LLM)
    messages: Annotated[list[BaseMessage], add_messages]

    # Metadata
    timestamp: str
    workflow_id: str
    iteration: int
```

## Usage

### Basic Execution

```python
from src.langgraph.graph import trading_graph

initial_state = {
    "symbol": "AAPL",
    "timeframe": "1d",
    "confidence": 0.0,
    "workflow_id": "demo_001"
}

config = {"thread_id": "demo_001"}

result = trading_graph.invoke(initial_state, config)
```

### Streaming

```python
for event in trading_graph.stream(initial_state, config):
    print(event)
```

### Human-in-the-Loop

```python
from langgraph.types import Command

# Resume after approval
trading_graph.invoke(
    Command(resume={"human_approved": True}),
    config
)
```

## Migration Plan

See full migration plan: `../../LANGGRAPH_MIGRATION_PLAN.md`

### Phases

1. **Week 1:** Foundation (dependencies, structure, basic graph)
2. **Week 2:** Agent Migration (technical, sentiment, risk)
3. **Week 3:** Advanced Features (debate, human review, conditional edges)
4. **Week 4:** Integration & Testing (IBKR, end-to-end, backtesting)

## Quick Start

See `../../LANGGRAPH_QUICKSTART.md` for getting started guide.

## Configuration

### Environment Variables

```bash
# LangSmith (optional)
export LANGSMITH_TRACING="true"
export LANGSMITH_API_KEY="your-key"

# Feature Flag
export USE_LANGGRAPH="true"
```

### Persistence

Checkpoints stored at: `data/checkpoints/trading_agent_checkpoints.db`

## Testing

```bash
# Run LangGraph tests
pytest tests/langgraph/ -v

# With coverage
pytest tests/langgraph/ --cov=src/langgraph
```

## Benefits

- **Stateful:** All state in one place, easy to debug
- **Resumable:** Pick up from interruptions automatically
- **Observable:** Full trace visibility in LangSmith
- **Flexible:** Conditional edges, loops, parallel paths
- **Production-Ready:** Built-in persistence, error handling

## Next Steps

- [ ] Implement remaining nodes (Phase 2)
- [ ] Add debate agents (Phase 3)
- [ ] Integrate with FastAPI (Phase 4)
- [ ] End-to-end tests (Phase 4)
- [ ] Enable LangSmith tracing
- [ ] Gradual rollout with feature flag

## Resources

- [LangGraph Docs](https://python.langchain.com/docs/langgraph/)
- [LangSmith](https://smith.langchain.com/)
- [Migration Plan](../../LANGGRAPH_MIGRATION_PLAN.md)
- [Quick Start](../../LANGGRAPH_QUICKSTART.md)
