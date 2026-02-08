# LangGraph Migration Plan for TradeMind AI

*Created: 2026-02-08*
*LangGraph Version: 1.0.8 (Latest)*

## Executive Summary

This document outlines a comprehensive plan to migrate TradeMind AI from its current linear multi-agent architecture to a LangGraph-based stateful agent orchestration framework. This migration will enable advanced features like human-in-the-loop, persistence, complex workflows with conditional branching, and durable execution.

---

## Part 1: LangGraph Research Summary

### 1.1 Latest Version & Features

**LangGraph 1.0.8** (Released: Feb 6, 2026)
- Production-ready, stable release
- Python 3.10+ support
- MIT License
- 24.4k GitHub stars, actively maintained

### 1.2 Core Concepts

#### StateGraph
```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class State(TypedDict):
    text: str

graph = StateGraph(State)
graph.add_node("node_name", node_function)
graph.add_edge(START, "node_name")
graph.add_edge("node_name", END)

compiled_graph = graph.compile()
```

**Key Features:**
- **TypedDict-based state schema** - Type-safe state management
- **Nodes** - Functions that receive state and return state updates
- **Edges** - Define flow between nodes (deterministic or conditional)
- **Compilation** - Converts graph to executable workflow

#### Nodes
Functions that process state:
```python
def my_node(state: State) -> dict:
    return {"key": value}  # Update state
```

**Characteristics:**
- Pure functions (receive state, return dict)
- Async-friendly
- Can have side effects (API calls, DB writes)
- Return partial state updates

#### Edges
**Normal Edges:** Unconditional flow
```python
graph.add_edge("node_a", "node_b")
```

**Conditional Edges:** Branching logic
```python
def route_decision(state: State) -> str:
    if state["confidence"] > 0.7:
        return "execute"
    else:
        return "retry"

graph.add_conditional_edges(
    "decision_node",
    route_decision,
    {
        "execute": "execute_trade",
        "retry": "fetch_more_data"
    }
)
```

#### Persistence (Checkpointer)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string(":memory:")
graph = graph.compile(checkpointer=checkpointer)
```

**Benefits:**
- Resume from interruptions
- State snapshots
- Time travel debugging
- Multi-threaded execution safety

#### Human-in-the-Loop
```python
from langgraph.types import Command, interrupt

def human_review_node(state: State):
    # Ask for human input
    response = interrupt({"question": "Approve this trade?"})
    return {"human_approved": response}

# Resume with: graph.invoke(Command(resume="yes"), config)
```

#### Streaming
```python
for event in graph.stream(initial_state):
    print(event)  # Real-time updates
```

### 1.3 LangGraph vs Current TradeMind

| Feature | Current TradeMind | LangGraph Migrated |
|----------|------------------|-------------------|
| Architecture | Linear pipeline | Graph-based orchestration |
| State Management | Manual, scattered | Centralized, typed |
| Persistence | Database only | Native checkpointing |
| Human-in-the-loop | None | Built-in interrupts |
| Debugging | Basic logging | LangSmith traces |
| Error Recovery | Manual | Automatic resume |
| Complex Flows | Limited | Conditional edges, loops |
| Multi-agent | Parallel execution | Structured workflows |

---

## Part 2: Current TradeMind Architecture Analysis

### 2.1 Existing Components

**Agents:**
- `TechnicalAgent` - RSI, MACD strategies (rule-based)
- `SentimentAgent` - ZAI GLM-4.7 LLM analysis
- `RiskAgent` - Position sizing, limits, veto
- `Orchestrator` - Weighted voting, final decision

**Execution:**
- `SignalExecutor` - IBKR order placement
- `IBKRRiskManager` - Pre-trade validation
- `ExecutionRouter` - Broker factory

**Current Flow:**
```
Market Data → Technical Agent → Sentiment Agent → Risk Manager
                                    ↓
                              Orchestrator (weighted voting)
                                    ↓
                              Signal Executor → IBKR
```

### 2.2 Limitations

1. **Linear Pipeline** - No feedback loops or debate mechanisms
2. **No Shared State** - Each agent operates independently
3. **No Human Oversight** - All trades automatic
4. **No Persistence** - State lost on failure
5. **Limited Debugging** - Hard to trace decision flow
6. **No Streaming** - Block until complete

---

## Part 3: LangGraph Architecture Design

### 3.1 Trading State Schema

```python
from typing_extensions import TypedDict, Annotated
from typing import Optional, List, Dict, Any, Literal
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class TradingState(TypedDict):
    """Shared state for all trading agents."""

    # Input
    symbol: str
    timeframe: str

    # Market Data
    market_data: Dict[str, Any]
    technical_indicators: Dict[str, Any]

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

    # Messages (for LLM interactions)
    messages: Annotated[List[BaseMessage], add_messages]

    # Metadata
    timestamp: str
    workflow_id: str
    iteration: int
```

### 3.2 Graph Structure

```
                    ┌──────────────┐
                    │    START     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Fetch Data   │
                    │ (yfinance)   │
                    └──────┬───────┘
                           │
                           ▼
              ┌──────────────────────┐
              │  Technical Analysis   │◄─────┐
              │  (RSI, MACD, MA)   │      │
              └────────┬─────────────┘      │
                       │                    │ Loop
                       ▼                    │ back
              ┌──────────────────────┐      │
              │  Sentiment Analysis  │      │
              │  (ZAI GLM-4.7)    │      │
              └────────┬─────────────┘      │
                       │                    │
                       ▼                    │
              ┌──────────────────────┐      │
              │  Debate Protocol   │──────┘
              │  (Bull vs Bear)   │
              └────────┬─────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │  Risk Assessment   │◄─────┐
              │  (Position sizing,  │      │ Loop
              │   limits, veto)    │      │ back
              └────────┬─────────────┘      │
                       │                    │
                       ▼                    │
              ┌──────────────────────┐      │
              │ Human Review       │──────┘
              │ (Interrupts)       │
              └────────┬─────────────┘
                       │
                       ▼
              ┌──────────────────────┐
              │ Decision Node      │
              │ (Weighted voting)  │
              └────────┬─────────────┘
                       │
           ┌───────────┴───────────┐
           │                       │
           ▼                       ▼
    ┌────────────┐         ┌────────────┐
    │  Execute   │         │  HOLD/END  │
    │  Trade     │         └────────────┘
    │  (IBKR)    │
    └────┬───────┘
         │
         ▼
    ┌────────────┐
    │    END     │
    └────────────┘
```

### 3.3 Node Definitions

#### Node 1: Fetch Market Data
```python
async def fetch_market_data(state: TradingState) -> Dict[str, Any]:
    """Fetch market data from yfinance."""

    from src.data.providers import yfinance_provider

    symbol = state["symbol"]
    timeframe = state["timeframe"]

    data = await yfinance_provider.fetch_data(symbol, timeframe)

    indicators = TechnicalIndicators.calculate_all(data)

    return {
        "market_data": data.to_dict(),
        "technical_indicators": indicators,
        "timestamp": datetime.utcnow().isoformat(),
        "workflow_id": state.get("workflow_id", generate_id())
    }
```

#### Node 2: Technical Analysis
```python
async def technical_analysis(state: TradingState) -> Dict[str, Any]:
    """Run technical analysis agent."""

    from src.agents.technical import TechnicalAgent

    agent = TechnicalAgent()
    data = pd.DataFrame(state["market_data"])

    signal = await agent.analyze(state["symbol"], data)

    return {
        "technical_signals": {
            "decision": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "data": signal.data
        }
    }
```

#### Node 3: Sentiment Analysis
```python
async def sentiment_analysis(state: TradingState) -> Dict[str, Any]:
    """Run sentiment analysis agent."""

    from src.agents.sentiment import SentimentAgent

    agent = SentimentAgent()
    data = pd.DataFrame(state["market_data"])

    signal = await agent.analyze(state["symbol"], data)

    return {
        "sentiment_signals": {
            "decision": signal.decision.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "data": signal.data
        }
    }
```

#### Node 4: Debate Protocol
```python
async def debate_protocol(state: TradingState) -> Dict[str, Any]:
    """Run bull/bear debate between agents."""

    from src.agents.debate import BullAgent, BearAgent, JudgeAgent

    bull = BullAgent()
    bear = BearAgent()
    judge = JudgeAgent()

    # Bull presents case
    bull_args = await bull.present_case(
        symbol=state["symbol"],
        market_data=state["market_data"],
        signals=state["technical_signals"]
    )

    # Bear presents case
    bear_args = await bear.present_case(
        symbol=state["symbol"],
        market_data=state["market_data"],
        signals=state["technical_signals"]
    )

    # Cross-examination
    bull_critique = await bull.critique(bear_args)
    bear_critique = await bear.critique(bull_args)

    # Final rebuttals
    bull_final = await bull.rebuttal(bear_critique)
    bear_final = await bear.rebuttal(bull_critique)

    # Judge decides
    verdict = await judge.decide(
        symbol=state["symbol"],
        bull_case=bull_final,
        bear_case=bear_final
    )

    return {
        "debate_result": {
            "bull_case": bull_args,
            "bear_case": bear_args,
            "verdict": verdict["decision"],
            "confidence": verdict["confidence"],
            "reasoning": verdict["reasoning"]
        }
    }
```

#### Node 5: Risk Assessment
```python
async def risk_assessment(state: TradingState) -> Dict[str, Any]:
    """Run risk assessment agent."""

    from src.brokers.ibkr.risk_manager import IBKRRiskManager
    from src.portfolio.manager import PortfolioManager

    risk_mgr = IBKRRiskManager(broker=broker)
    portfolio_mgr = PortfolioManager()

    # Get portfolio context
    portfolio = await portfolio_mgr.get_portfolio()
    holdings = await portfolio_mgr.get_holdings()
    daily_pnl = portfolio.get("daily_pnl", 0)

    # Assess risk for proposed trade
    risk_assessment = await risk_mgr.check_portfolio_risk()

    # Check if veto needed
    if risk_assessment.get("risk_level") == "HIGH":
        return {
            "risk_signals": {
                "decision": "VETO",
                "confidence": 1.0,
                "reasoning": f"Risk too high: {risk_assessment.get('warnings')}",
                "veto": True
            },
            "final_decision": {
                "decision": "HOLD",
                "confidence": 0.0,
                "reasoning": "Risk veto applied"
            }
        }

    # Calculate position size
    sizing = risk_mgr.get_position_sizing(
        symbol=state["symbol"],
        entry_price=state["market_data"]["close"],
        portfolio_value=portfolio["total_value"]
    )

    return {
        "risk_signals": {
            "decision": "APPROVE",
            "confidence": 1.0,
            "position_size": sizing["shares"],
            "reasoning": "Risk within limits",
            "sizing": sizing
        }
    }
```

#### Node 6: Human Review (Interrupt)
```python
from langgraph.types import interrupt

async def human_review(state: TradingState) -> Dict[str, Any]:
    """Pause for human approval if confidence < threshold."""

    confidence = state.get("confidence", 0)
    min_confidence = 0.75  # Configurable

    if confidence < min_confidence:
        # Interrupt execution and wait for human input
        decision = interrupt({
            "question": f"Confidence is {confidence:.2f}. Approve trade for {state['symbol']}?",
            "options": ["APPROVE", "REJECT", "MODIFY"],
            "details": state
        })

        return {
            "human_approved": decision == "APPROVE",
            "human_feedback": decision
        }
    else:
        # Auto-approve if high confidence
        return {
            "human_approved": True,
            "human_feedback": "Auto-approved (high confidence)"
        }
```

#### Node 7: Decision Node
```python
async def make_decision(state: TradingState) -> Dict[str, Any]:
    """Combine all signals into final decision."""

    weights = {
        "technical": 0.40,
        "sentiment": 0.30,
        "debate": 0.20,
        "risk": 0.10
    }

    # Calculate weighted scores
    buy_score = 0.0
    sell_score = 0.0

    for signal_type, signal in [
        ("technical", state["technical_signals"]),
        ("sentiment", state["sentiment_signals"]),
        ("debate", state["debate_result"])
    ]:
        if signal is None:
            continue

        weight = weights.get(signal_type, 0)
        decision = signal.get("decision", "HOLD")
        confidence = signal.get("confidence", 0)

        if decision == "BUY":
            buy_score += confidence * weight
        elif decision == "SELL":
            sell_score += confidence * weight

    # Determine final decision
    min_confidence = 0.60

    if buy_score > sell_score and buy_score >= min_confidence:
        final_decision = "BUY"
        confidence = buy_score
    elif sell_score > buy_score and sell_score >= min_confidence:
        final_decision = "SELL"
        confidence = sell_score
    else:
        final_decision = "HOLD"
        confidence = max(buy_score, sell_score)

    reasoning = f"BUY score: {buy_score:.2f}, SELL score: {sell_score:.2f}"

    return {
        "final_decision": final_decision,
        "final_action": final_decision,
        "confidence": confidence,
        "decision_details": {
            "buy_score": buy_score,
            "sell_score": sell_score,
            "reasoning": reasoning
        }
    }
```

#### Node 8: Execute Trade
```python
async def execute_trade(state: TradingState) -> Dict[str, Any]:
    """Execute the trade via IBKR."""

    from src.execution.signal_executor import SignalExecutor
    from src.brokers.ibkr.client import IBKRBroker

    broker = IBKRBroker()
    await broker.connect()

    executor = SignalExecutor(broker, risk_manager)

    result = await executor.execute_signal(
        symbol=state["symbol"],
        signal_type=state["final_action"],
        quantity=state["risk_signals"]["position_size"],
        order_type="MARKET"
    )

    return {
        "executed_trade": result,
        "order_id": result.get("order_id")
    }
```

### 3.4 Edge Definitions

```python
def should_debate(state: TradingState) -> Literal["debate", "skip_debate"]:
    """Conditional edge: Run debate if signals conflict."""
    tech = state["technical_signals"]
    sent = state["sentiment_signals"]

    if tech["decision"] != sent["decision"]:
        return "debate"
    else:
        return "skip_debate"

def should_review(state: TradingState) -> Literal["review", "auto_approve"]:
    """Conditional edge: Human review if low confidence."""
    if state["confidence"] < 0.75:
        return "review"
    else:
        return "auto_approve"

def should_execute(state: TradingState) -> Literal["execute", "hold"]:
    """Conditional edge: Execute if BUY/SELL, else HOLD."""
    if state["final_action"] in ["BUY", "SELL"]:
        return "execute"
    else:
        return "hold"

def should_retry(state: TradingState) -> Literal["retry", "end"]:
    """Conditional edge: Retry if insufficient confidence."""
    if state["confidence"] < 0.60:
        return "retry"
    else:
        return "end"
```

### 3.5 Complete Graph Construction

```python
from langgraph.graph import StateGraph, START, END

# Create graph
graph = StateGraph(TradingState)

# Add nodes
graph.add_node("fetch_data", fetch_market_data)
graph.add_node("technical", technical_analysis)
graph.add_node("sentiment", sentiment_analysis)
graph.add_node("debate", debate_protocol)
graph.add_node("risk", risk_assessment)
graph.add_node("human_review", human_review)
graph.add_node("decision", make_decision)
graph.add_node("execute", execute_trade)
graph.add_node("end", lambda state: {})  # Terminal node

# Add edges
graph.add_edge(START, "fetch_data")
graph.add_edge("fetch_data", "technical")
graph.add_edge("fetch_data", "sentiment")

# Conditional: Debate if conflicting signals
graph.add_conditional_edges(
    "technical",
    lambda state: "debate" if should_debate(state) == "debate" else "risk",
    {
        "debate": "debate",
        "risk": "risk"
    }
)

graph.add_conditional_edges(
    "sentiment",
    lambda state: "debate" if should_debate(state) == "debate" else "risk",
    {
        "debate": "debate",
        "risk": "risk"
    }
)

graph.add_edge("debate", "risk")
graph.add_edge("risk", "decision")

# Conditional: Human review if low confidence
graph.add_conditional_edges(
    "decision",
    should_review,
    {
        "review": "human_review",
        "auto_approve": "execute"
    }
)

graph.add_edge("human_review", "execute")

# Conditional: Execute or HOLD
graph.add_conditional_edges(
    "execute",
    should_execute,
    {
        "execute": "execute_trade",
        "hold": "end"
    }
)

graph.add_edge("execute_trade", "end")

# Compile with persistence
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("trading_agent.db")

compiled_graph = graph.compile(checkpointer=checkpointer)
```

---

## Part 4: Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal:** Set up LangGraph infrastructure

**Tasks:**
- [ ] Install dependencies
  ```bash
  pip install -U langgraph>=1.0.8
  pip install -U langchain-core
  pip install -U langchain-community
  ```
- [ ] Create `src/langgraph/` directory structure
  ```
  src/langgraph/
  ├── __init__.py
  ├── state.py              # TradingState schema
  ├── graph.py              # Graph construction
  ├── nodes/                # Node implementations
  │   ├── __init__.py
  │   ├── data_nodes.py
  │   ├── analysis_nodes.py
  │   ├── debate_nodes.py
  │   └── execution_nodes.py
  └── persistence.py         # Checkpointer config
  ```
- [ ] Define TradingState in `src/langgraph/state.py`
- [ ] Create basic graph skeleton in `src/langgraph/graph.py`
- [ ] Add persistence layer (SqliteSaver)
- [ ] Create tests for state management
- [ ] Set up LangSmith integration (optional)
  ```python
  import os
  os.environ["LANGSMITH_TRACING"] = "true"
  os.environ["LANGSMITH_API_KEY"] = "your-key"
  ```

**Deliverables:**
- LangGraph installed and configured
- TradingState schema defined
- Basic graph structure created
- Persistence layer working

---

### Phase 2: Agent Migration (Week 2)
**Goal:** Migrate existing agents to LangGraph nodes

**Tasks:**

#### Technical Agent Migration
- [ ] Create `src/langgraph/nodes/analysis_nodes.py`
- [ ] Implement `technical_analysis()` node
- [ ] Keep existing TechnicalAgent logic
- [ ] Return TradingState updates
- [ ] Add tests

#### Sentiment Agent Migration
- [ ] Implement `sentiment_analysis()` node
- [ ] Preserve caching logic
- [ ] Add retry with LangGraph's built-in resilience
- [ ] Tests

#### Risk Manager Migration
- [ ] Implement `risk_assessment()` node
- [ ] Integrate IBKRRiskManager
- [ ] Add veto logic
- [ ] Position sizing calculations
- [ ] Tests

#### Orchestrator Migration
- [ ] Implement `make_decision()` node
- [ ] Weighted voting logic
- [ ] Confidence aggregation
- [ ] Decision routing
- [ ] Tests

**Deliverables:**
- All agents migrated to nodes
- Tests passing
- No functionality lost

---

### Phase 3: Advanced Features (Week 3)
**Goal:** Add debate, human-in-the-loop, conditional edges

**Tasks:**

#### Debate Protocol
- [ ] Create `src/agents/debate.py`
  - BullAgent
  - BearAgent
  - JudgeAgent
- [ ] Implement `debate_protocol()` node
  - Present cases
  - Cross-examine
  - Final verdict
- [ ] Add LLM-based argument generation
- [ ] Track debate history
- [ ] Tests

#### Conditional Edges
- [ ] Implement routing functions
  - `should_debate()`
  - `should_review()`
  - `should_execute()`
  - `should_retry()`
- [ ] Add edge conditions to graph
- [ ] Test all paths

#### Human-in-the-Loop
- [ ] Implement `human_review()` node
  - Interrupt logic
  - Resume mechanism
- [ ] Create API endpoint for approvals
  ```python
  @app.post("/api/langgraph/approve")
  async def approve_trade(workflow_id: str, approved: bool):
       graph.invoke(Command(resume=approved), config={"thread_id": workflow_id})
  ```
- [ ] Add notification hooks (Slack, email)
- [ ] Tests

#### Memory & History
- [ ] Add short-term memory (conversation history)
- [ ] Add long-term memory (decisions in TimescaleDB)
- [ ] Implement state versioning
- [ ] Tests

**Deliverables:**
- Debate system working
- Human-in-the-loop functional
- Conditional edges tested
- Memory layer implemented

---

### Phase 4: Integration & Testing (Week 4)
**Goal:** Connect to IBKR, test end-to-end

**Tasks:**

#### IBKR Integration
- [ ] Implement `execute_trade()` node
- [ ] Connect to existing SignalExecutor
- [ ] Error handling
- [ ] Order status tracking
- [ ] Tests

#### End-to-End Tests
- [ ] Full workflow test (BUY scenario)
- [ ] Full workflow test (SELL scenario)
- [ ] Full workflow test (HOLD scenario)
- [ ] Test debate flow
- [ ] Test human approval flow
- [ ] Test veto flow
- [ ] Test retry/loop flow
- [ ] Performance tests

#### LangSmith Integration
- [ ] Enable tracing
- [ ] Create traces for all workflows
- [ ] Set up evaluations
- [ ] Dashboard setup

#### Backtesting
- [ ] Run backtest with LangGraph
- [ ] Compare to original system
- [ ] Performance benchmarks
- [ ] A/B testing

#### Documentation
- [ ] Update README with LangGraph
- [ ] Create migration guide
- [ ] API documentation
- [ ] Architecture diagrams

**Deliverables:**
- Full system integrated with IBKR
- All tests passing
- LangSmith traces visible
- Documentation complete
- Backtest results

---

## Part 5: Code Examples

### Example 1: Complete Graph Setup

```python
# src/langgraph/graph.py

from typing_extensions import TypedDict, Annotated
from typing import Optional, Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

# State definition
class TradingState(TypedDict):
    symbol: str
    timeframe: str
    market_data: Optional[Dict[str, Any]]
    technical_signals: Optional[Dict[str, Any]]
    sentiment_signals: Optional[Dict[str, Any]]
    risk_signals: Optional[Dict[str, Any]]
    debate_result: Optional[Dict[str, Any]]
    final_decision: Optional[Dict[str, Any]]
    final_action: Optional[Literal["BUY", "SELL", "HOLD"]]
    confidence: float
    executed_trade: Optional[Dict[str, Any]]
    order_id: Optional[str]
    human_approved: Optional[bool]
    human_feedback: Optional[str]
    messages: Annotated[list[BaseMessage], add_messages]
    timestamp: str
    workflow_id: str
    iteration: int

# Import nodes
from src.langgraph.nodes.data_nodes import fetch_market_data
from src.langgraph.nodes.analysis_nodes import (
    technical_analysis,
    sentiment_analysis,
    make_decision
)
from src.langgraph.nodes.debate_nodes import debate_protocol
from src.langgraph.nodes.execution_nodes import (
    risk_assessment,
    human_review,
    execute_trade
)

# Conditional edge functions
def should_debate(state: TradingState) -> Literal["debate", "skip_debate"]:
    tech = state.get("technical_signals", {})
    sent = state.get("sentiment_signals", {})

    if tech.get("decision") != sent.get("decision"):
        return "debate"
    return "skip_debate"

def should_review(state: TradingState) -> Literal["review", "auto_approve"]:
    return "review" if state["confidence"] < 0.75 else "auto_approve"

def should_execute(state: TradingState) -> Literal["execute", "hold"]:
    action = state.get("final_action", "HOLD")
    return "execute" if action in ["BUY", "SELL"] else "hold"

# Build graph
def create_trading_graph():
    """Create and compile the trading graph."""

    graph = StateGraph(TradingState)

    # Add nodes
    graph.add_node("fetch_data", fetch_market_data)
    graph.add_node("technical", technical_analysis)
    graph.add_node("sentiment", sentiment_analysis)
    graph.add_node("debate", debate_protocol)
    graph.add_node("risk", risk_assessment)
    graph.add_node("decision", make_decision)
    graph.add_node("human_review", human_review)
    graph.add_node("execute", execute_trade)
    graph.add_node("end", lambda state: {})

    # Linear edges
    graph.add_edge(START, "fetch_data")
    graph.add_edge("fetch_data", "technical")
    graph.add_edge("fetch_data", "sentiment")

    # Conditional: debate or skip
    graph.add_conditional_edges(
        "technical",
        should_debate,
        {
            "debate": "debate",
            "skip_debate": "risk"
        }
    )

    graph.add_conditional_edges(
        "sentiment",
        should_debate,
        {
            "debate": "debate",
            "skip_debate": "risk"
        }
    )

    graph.add_edge("debate", "risk")
    graph.add_edge("risk", "decision")

    # Conditional: human review
    graph.add_conditional_edges(
        "decision",
        should_review,
        {
            "review": "human_review",
            "auto_approve": "execute"
        }
    )

    graph.add_edge("human_review", "execute")

    # Conditional: execute or hold
    graph.add_conditional_edges(
        "execute",
        should_execute,
        {
            "execute": "execute_trade",
            "hold": "end"
        }
    )

    graph.add_edge("execute_trade", "end")

    # Compile with persistence
    checkpointer = SqliteSaver.from_conn_string(
        "trading_agent_checkpoints.db"
    )

    return graph.compile(
        checkpointer=checkpointer,
        debug=True  # Enable LangSmith tracing
    )

# Singleton instance
trading_graph = create_trading_graph()
```

### Example 2: Running the Graph

```python
# src/main.py - Updated FastAPI integration

from fastapi import FastAPI, HTTPException
from src.langgraph.graph import trading_graph
from langgraph.types import Command

app = FastAPI()

@app.post("/api/langgraph/analyze")
async def analyze_symbol(symbol: str, timeframe: str = "1d"):
    """Run full LangGraph workflow for a symbol."""

    initial_state = {
        "symbol": symbol,
        "timeframe": timeframe,
        "confidence": 0.0,
        "workflow_id": f"{symbol}_{datetime.utcnow().timestamp()}",
        "iteration": 0,
        "messages": []
    }

    config = {
        "thread_id": initial_state["workflow_id"],
        "recursion_limit": 100  # Prevent infinite loops
    }

    try:
        # Run graph with streaming
        events = []
        for event in trading_graph.stream(
            initial_state,
            config,
            stream_mode="values"
        ):
            events.append(event)
            print(f"[{event.get('timestamp', '')}] {event.get('current_node', '')}")

        # Get final state
        final_state = trading_graph.get_state(config)

        return {
            "workflow_id": initial_state["workflow_id"],
            "final_state": final_state.values,
            "events": events,
            "order_id": final_state.values.get("order_id"),
            "executed": final_state.values.get("executed_trade")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/langgraph/approve")
async def approve_workflow(workflow_id: str, approved: bool, feedback: str = None):
    """Resume interrupted workflow with human approval."""

    config = {"thread_id": workflow_id}

    # Resume graph execution
    result = trading_graph.invoke(
        Command(resume={
            "human_approved": approved,
            "human_feedback": feedback or f"Approved: {approved}"
        }),
        config=config
    )

    return result
```

### Example 3: Streaming with UI Updates

```python
# src/api/websocket_updates.py

from fastapi import WebSocket
import json

@app.websocket("/ws/langgraph/stream")
async def stream_workflow(websocket: WebSocket):
    """Stream graph execution updates to WebSocket client."""

    await websocket.accept()

    initial_state = await websocket.receive_json()

    config = {
        "thread_id": initial_state["workflow_id"]
    }

    # Stream and send updates
    for event in trading_graph.stream(
        {k: v for k, v in initial_state.items() if k != "workflow_id"},
        config,
        stream_mode="updates"
    ):
        await websocket.send_json({
            "event_type": "graph_update",
            "data": event
        })

    await websocket.close()
```

### Example 4: Testing with LangSmith

```python
# tests/test_langgraph_integration.py

import pytest
from src.langgraph.graph import trading_graph

@pytest.mark.asyncio
async def test_full_buy_workflow():
    """Test complete workflow for BUY signal."""

    initial_state = {
        "symbol": "AAPL",
        "timeframe": "1d",
        "confidence": 0.0,
        "workflow_id": "test_001",
        "iteration": 0,
        "messages": []
    }

    config = {"thread_id": "test_001"}

    # Run graph
    result = trading_graph.invoke(initial_state, config)

    # Assertions
    assert result["final_action"] in ["BUY", "SELL", "HOLD"]
    assert "technical_signals" in result
    assert "sentiment_signals" in result
    assert result["workflow_id"] == "test_001"

    # Check LangSmith trace
    # (Will be visible in LangSmith dashboard)

@pytest.mark.asyncio
async def test_human_in_the_loop():
    """Test human interrupt and resume."""

    # Configure mock market data for low confidence
    initial_state = {
        "symbol": "TSLA",
        "timeframe": "1d",
        "confidence": 0.5,  # Low confidence triggers human review
        "workflow_id": "test_002",
        "iteration": 0
    }

    config = {"thread_id": "test_002"}

    # Run until interrupt
    try:
        trading_graph.invoke(initial_state, config)
        assert False, "Should have interrupted"
    except Exception:
        pass  # Expected interrupt

    # Get interrupted state
    state = trading_graph.get_state(config)
    assert state.next == ["human_review"]

    # Resume with approval
    from langgraph.types import Command
    result = trading_graph.invoke(
        Command(resume={"human_approved": True}),
        config
    )

    assert result["final_action"] is not None
```

---

## Part 6: Risk Mitigation

### 6.1 Migration Risks

| Risk | Mitigation |
|-------|-----------|
| **Breaking existing functionality** | Keep original agents as fallback, gradual migration |
| **Performance degradation** | Benchmark before/after, optimize hot paths |
| **Learning curve** | Team training, pair programming, documentation |
| **LangGraph bugs** | Use stable 1.0.8, monitor issues |
| **Data loss during migration** | Full backups, test on dev first |
| **IBKR integration issues** | Extensive testing with paper trading |
| **State corruption** | Validate state schema, add sanity checks |

### 6.2 Rollback Plan

If migration fails:
1. Keep original `src/agents/` code untouched
2. Feature flag: `USE_LANGGRAPH=false` disables new system
3. Gradual rollout: 10% → 50% → 100% traffic
4. 24-hour monitoring window for each phase
5. Quick rollback by toggling flag

---

## Part 7: Success Metrics

### 7.1 Technical Metrics
- Graph execution time < 2 seconds
- 99.9% success rate for normal flows
- < 1 second latency for human interrupt handling
- Zero data loss during checkpoint/resume
- State size < 1 MB per workflow

### 7.2 Business Metrics
- Improved trade accuracy (vs baseline)
- Reduced manual interventions
- Better risk-adjusted returns
- Fewer failed trades
- Faster decision cycles

### 7.3 Developer Experience
- Faster iteration cycles (visible traces)
- Easier debugging (LangSmith)
- Better code organization
- Clear state flow visualization

---

## Part 8: Next Steps

1. **Review and approve this plan** with team
2. **Set up development environment** for LangGraph
3. **Start Phase 1** (Foundation)
4. **Weekly sync** to review progress
5. **Adjust plan** based on learnings

---

## Appendix: Additional Resources

### LangGraph Documentation
- [Official Docs](https://python.langchain.com/docs/langgraph/)
- [GitHub Repository](https://github.com/langchain-ai/langgraph)
- [LangSmith](https://smith.langchain.com/)
- [Community Forum](https://forum.langchain.com/)

### Related Projects
- [LangChain Agents](https://python.langchain.com/docs/langchain/agents/)
- [CrewAI](https://www.crewai.com/) - Alternative multi-agent framework
- [AutoGen](https://github.com/microsoft/autogen) - Microsoft's agent framework

### TradeMind Context
- Original architecture: `/src/agents/`, `/src/brokers/`
- Current workflows: Linear pipeline
- Existing agents: Technical, Sentiment, Risk, Orchestrator
- Broker: IBKR via ib_insync

---

*Document prepared by: OpenCode Research Agent*
*Date: 2026-02-08*
*LangGraph Version: 1.0.8*
