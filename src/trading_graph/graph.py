"""LangGraph construction for TradeMind AI trading workflow."""

from typing import Literal, Dict, Any
import sys
import importlib

# Import from system langgraph package (avoid shadowing by src.langgraph)
def _import_langgraph_module(module_path: str):
    """Import from langgraph, avoiding src.langgraph shadowing."""
    # Temporarily remove src.langgraph from sys.modules
    modules_to_restore = []
    for key in list(sys.modules.keys()):
        if key.startswith('src.langgraph'):
            modules_to_restore.append((key, sys.modules[key]))
            del sys.modules[key]
    
    try:
        # Import from langgraph using importlib
        module = importlib.import_module(module_path)
        return module
    finally:
        # Restore src.langgraph modules
        for key, val in modules_to_restore:
            sys.modules[key] = val

# Import StateGraph, START, END from system langgraph
StateGraph = _import_langgraph_module('langgraph.graph.state').StateGraph
START = _import_langgraph_module('langgraph.constants').START
END = _import_langgraph_module('langgraph.constants').END

from src.trading_graph.state import TradingState
from src.trading_graph.persistence import get_checkpointer
from src.trading_graph.nodes.data_nodes import fetch_market_data
from src.trading_graph.nodes.analysis_nodes import technical_analysis, sentiment_analysis, make_decision
from src.trading_graph.nodes.execution_nodes import risk_assessment, execute_trade, retry_node
from src.trading_graph.nodes.market_mood_node import market_mood_analysis
from src.trading_graph.nodes.debate_nodes import debate_protocol
from src.trading_graph.nodes.human_review_nodes import human_review
from src.trading_graph.validation import get_utc_now
from src.trading_graph.state_validator import validate_state, get_error_handler, ErrorSeverity, create_error_state
from src.config import settings

# ============ CONDITIONAL EDGE FUNCTIONS ============


def end_node(state: TradingState) -> Dict[str, Any]:
    """Terminal node - clean up and finalize."""
    return {
        "current_node": "end",
        "timestamp": get_utc_now()
    }


def route_error(state: TradingState) -> Literal["continue", "retry", "end"]:
    """
    Route based on error state.

    Returns:
        - "continue": No error, proceed normally
        - "retry": Error occurred, retry if under limit
        - "end": Error occurred, max retries reached
    """
    error = state.get("error")
    retry_count = state.get("retry_count", 0)

    if error:
        # Log error using structured error handler
        error_handler = get_error_handler()
        error_handler.log_error(
            node=state.get("current_node") or "unknown",
            error=Exception(error),
            severity=ErrorSeverity.MEDIUM,
            state=dict(state)
        )
        
        if retry_count < 3:
            return "retry"
        return "end"
    return "continue"

def should_debate(state: TradingState) -> Literal["debate", "skip_debate"]:
    """
    Determine if debate protocol should run.

    Triggers debate when technical and sentiment signals conflict.
    """
    tech = state.get("technical_signals", {})
    sent = state.get("sentiment_signals", {})

    if tech and sent and tech.get("decision") != sent.get("decision"):
        return "debate"
    return "skip_debate"

def should_review(state: TradingState) -> Literal["review", "auto_approve"]:
    """
    Determine if human review is needed.

    Human review triggered when confidence < threshold.
    """
    confidence = state.get("confidence", 0.0)
    threshold = settings.confidence_threshold_high

    return "review" if confidence < threshold else "auto_approve"

def should_execute(state: TradingState) -> Literal["execute", "hold"]:
    """
    Determine if trade should execute or be held.

    Only execute for BUY/SELL decisions.
    """
    action = state.get("final_action", "HOLD")
    return "execute" if action in ["BUY", "SELL"] else "hold"

def should_retry(state: TradingState) -> Literal["retry", "end"]:
    """
    Determine if workflow should retry or end.

    Retry if confidence is too low after full cycle.
    """
    confidence = state.get("confidence", 0.0)
    retry_count = state.get("retry_count", 0)

    if confidence < 0.60 and retry_count < 3:
        return "retry"
    return "end"

# ============ GRAPH CONSTRUCTION ============


async def create_trading_graph() -> Any:
    """
    Create and compile the complete trading workflow graph.

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    graph = StateGraph(TradingState)

    # ========== ADD NODES ==========
    graph.add_node("fetch_data", fetch_market_data)
    graph.add_node("market_mood", market_mood_analysis)
    graph.add_node("technical", technical_analysis)
    graph.add_node("sentiment", sentiment_analysis)
    graph.add_node("debate", debate_protocol)
    graph.add_node("risk", risk_assessment)
    graph.add_node("decision", make_decision)
    graph.add_node("human_review", human_review)
    graph.add_node("execute", execute_trade)
    graph.add_node("retry", retry_node)
    graph.add_node("end", end_node)

    # ========== ADD EDGES ==========

    # Linear flow: START → fetch_data
    graph.add_edge(START, "fetch_data")

    # Error handling after fetch_data
    graph.add_conditional_edges(
        "fetch_data",
        route_error,
        {
            "continue": "market_mood",  # Start parallel analysis
            "retry": "retry",        # Retry via retry node
            "end": END                # Give up
        }
    )

    # Parallel analysis: fetch_data → market_mood, technical & sentiment (all run concurrently)
    graph.add_edge("fetch_data", "sentiment")
    graph.add_edge("fetch_data", "technical")

    # Flow: market_mood → conditional: debate or skip
    graph.add_conditional_edges(
        "market_mood",
        should_debate,
        {
            "debate": "debate",
            "skip_debate": "risk"
        }
    )

    # Flow: technical & sentiment → conditional: debate or skip
    graph.add_conditional_edges(
        "technical",
        should_debate,
        {
            "debate": "debate",
            "skip_debate": "risk"
        }
    )

    # Flow: sentiment → conditional: debate or skip
    graph.add_conditional_edges(
        "sentiment",
        should_debate,
        {
            "debate": "debate",
            "skip_debate": "risk"
        }
    )

    # Flow: debate → risk (after debate concludes)
    graph.add_edge("debate", "risk")

    # Flow: risk → decision
    graph.add_edge("risk", "decision")

    # Conditional: human review or skip
    graph.add_conditional_edges(
        "decision",
        should_review,
        {
            "review": "human_review",
            "auto_approve": "execute"
        }
    )

    # Conditional: execute or hold (after human review)
    graph.add_conditional_edges(
        "human_review",
        should_execute,
        {
            "execute": "execute",
            "hold": "end"
        }
    )

    # Flow: execute → end
    graph.add_edge("execute", "end")

    # Flow: retry → fetch_data (loop back)
    graph.add_edge("retry", "fetch_data")

    # ========== COMPILE GRAPH ==========

    # Get checkpointer for persistence
    checkpointer = await get_checkpointer()

    # Compile with optional debug mode for LangSmith tracing
    compiled = graph.compile(
        checkpointer=checkpointer,
        debug=False  # Set to True to enable LangSmith tracing
    )

    return compiled

# ========== GRAPH FACTORY ==========


async def get_trading_graph() -> Any:
    """
    Get or create the trading workflow graph.

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    return await create_trading_graph()
