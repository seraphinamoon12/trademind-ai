# LangGraph Migration Guide

## Overview

This guide covers migrating from the legacy agent system to LangGraph for TradeMind AI.

## Key Changes

### State Management
- **Before**: Manual state passing between agents
- **After**: TypedDict-based TradingState with reducers

### Agent Execution
- **Before**: `await orchestrator.run(symbol)`
- **After**: `await graph.ainvoke(state, config)`

### Error Handling
- **Before**: Try/catch in each agent
- **After**: Native checkpoint/resume

## Migration Steps

1. Update imports
2. Replace agent calls with graph nodes
3. Add state management
4. Test with paper trading

## Testing

```bash
# Run all LangGraph tests
python -m pytest tests/trading_graph/ -v

# Run specific test
python -m pytest tests/trading_graph/test_end_to_end.py -v
```

## LangGraph Integration

TradeMind AI now uses LangGraph for advanced multi-agent orchestration.

### Architecture

```
┌─────────┐    ┌──────────────┐    ┌──────────────────┐
│  START  │───▶│  Fetch Data  │───▶│ Technical Analysis│
└─────────┘    └──────────────┘    └────────┬─────────┘
                                             │
                    ┌───────────────────────┘
                    ▼
          ┌──────────────────────┐
          │ Sentiment Analysis   │
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │  Debate Protocol    │ (if signals conflict)
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │  Risk Assessment    │
          └────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────────┐
          │   Decision Node     │
          └────────┬─────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                      ▼
┌───────────────┐      ┌───────────────┐
│ Human Review  │      │ Auto-Approve  │
│ (low conf)    │      │ (high conf)   │
└───────┬───────┘      └───────┬───────┘
        │                      │
        └──────────┬───────────┘
                   ▼
          ┌──────────────────────┐
          │  Execute Trade      │
          └────────┬─────────────┘
                   │
                   ▼
            ┌────────────┐
            │    END     │
            └────────────┘
```

### Features

- **Multi-Agent Debate**: Bull vs Bear agents debate when signals conflict
- **Human-in-the-Loop**: Automatic interrupts for low-confidence trades
- **Persistence**: Resume workflows from any point
- **Streaming**: Real-time progress updates
- **Observability**: Full LangSmith integration

### Configuration

```bash
# Enable LangSmith tracing
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-key
export LANGSMITH_PROJECT=trademind-ai
```

### Usage

```python
from src.trading_graph.graph import create_trading_graph

graph = await create_trading_graph()

result = await graph.ainvoke({
    "symbol": "AAPL",
    "timeframe": "1d"
}, {"thread_id": "workflow-001"})
```

### API Endpoints

- `POST /api/langgraph/analyze` - Run full workflow
- `POST /api/langgraph/approve` - Approve interrupted workflow
- `WS /ws/trades/{symbol}` - Real-time trade notifications

## New Files Created

### Day 1: Execute Trade Node
- `src/trading_graph/nodes/execution_nodes.py` - Updated with real IBKR integration

### Day 2: End-to-End Tests
- `tests/trading_graph/test_end_to_end.py` - Comprehensive workflow tests
- `tests/trading_graph/test_performance.py` - Performance benchmarks

### Day 3: LangSmith Integration
- `src/trading_graph/observability.py` - Enhanced tracing and monitoring
- `LangSmithManager` class for tracing management
- `CostTracker` for API cost monitoring

### Day 4: Backtesting
- `src/backtesting/langgraph_backtest.py` - Full backtesting system
- `BacktestResult` dataclass for results
- `LangGraphBacktester` for running backtests

## Verification Checklist

After Week 4 migration:

```bash
# 1. All tests pass
python3 -m pytest tests/trading_graph/ -v
# Should show: 30+ tests passing

# 2. End-to-end tests pass
python3 -m pytest tests/trading_graph/test_end_to_end.py -v

# 3. Performance tests pass
python3 -m pytest tests/trading_graph/test_performance.py -v

# 4. Graph execution time < 2 seconds
python3 -c "
import time
import asyncio
from src.trading_graph.graph import create_trading_graph

async def test():
    graph = await create_trading_graph()
    start = time.time()
    result = await graph.ainvoke({
        'symbol': 'AAPL',
        'timeframe': '1d',
        'workflow_id': 'perf_test',
        'confidence': 0.0
    }, {'thread_id': 'perf_test'})
    elapsed = time.time() - start
    print(f'Graph execution time: {elapsed:.2f}s')
    assert elapsed < 2.0, 'Too slow!'

asyncio.run(test())
"

# 5. LangSmith tracing works (if enabled)
python3 -c "
from src.trading_graph.observability import langsmith_manager
print(f'LangSmith enabled: {langsmith_manager.enabled}')
"

# 6. Backtesting works
python3 -c "
import asyncio
from src.backtesting.langgraph_backtest import LangGraphBacktester
from datetime import datetime

async def test():
    bt = LangGraphBacktester()
    result = await bt.run_backtest('AAPL', datetime(2024, 1, 1), datetime(2024, 1, 31))
    print(f'Backtest completed: {len(result.trades)} trades')

asyncio.run(test())
"

# 7. Documentation complete
ls docs/LANGGRAPH_MIGRATION_GUIDE.md

# 8. All imports work
python3 -c "
from src.trading_graph.graph import create_trading_graph
from src.trading_graph.state import TradingState
from src.trading_graph.observability import langsmith_manager
from src.backtesting.langgraph_backtest import LangGraphBacktester
print('✓ All imports successful')
"
```

## Deliverables

1. Complete execute_trade node with IBKR integration
2. Comprehensive end-to-end test suite (30+ tests)
3. Performance tests (< 2s execution, < 1MB state)
4. LangSmith integration with custom traces
5. Backtesting system with performance metrics
6. Updated README with LangGraph documentation
7. Migration guide for developers
8. All tests passing

## Troubleshooting

### LangSmith Not Working

If LangSmith tracing is not enabled:

```bash
# Check environment variables
echo $LANGSMITH_TRACING
echo $LANGSMITH_API_KEY

# Set them correctly
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=your-actual-api-key
```

### Tests Failing

If tests are failing:

```bash
# Update test dependencies
pip install -r requirements-test.txt

# Check for missing dependencies
python3 -m pytest tests/trading_graph/ --collect-only
```

### Backtest Errors

If backtesting fails:

```bash
# Check data provider
python3 -c "from src.data.providers import yahoo_provider; print(yahoo_provider.get_historical('AAPL'))"

# Verify date range is valid
python3 -c "from datetime import datetime; print(datetime(2023, 1, 1), datetime(2023, 12, 31))"
```

## Next Steps

After completing Week 4:

1. Run full test suite to verify everything works
2. Test with paper trading account
3. Monitor LangSmith traces for optimization
4. Run backtests on historical data
5. Deploy to production with confidence
