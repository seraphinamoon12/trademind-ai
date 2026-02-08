"""LangGraph construction for TradeMind AI trading workflow."""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from src.langgraph.state import TradingState
from src.langgraph.persistence import get_checkpointer
from src.langgraph.nodes.data_nodes import fetch_market_data

# TODO: Import other nodes as they are created
# from src.langgraph.nodes.analysis_nodes import technical_analysis, sentiment_analysis, make_decision
# from src.langgraph.nodes.debate_nodes import debate_protocol
# from src.langgraph.nodes.execution_nodes import risk_assessment, human_review, execute_trade

# ============ CONDITIONAL EDGE FUNCTIONS ============

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
    threshold = 0.75

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

def create_trading_graph() -> StateGraph:
    """
    Create and compile the complete trading workflow graph.

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    graph = StateGraph(TradingState)

    # ========== ADD NODES ==========
    graph.add_node("fetch_data", fetch_market_data)
    # TODO: Add other nodes as they are implemented
    # graph.add_node("technical", technical_analysis)
    # graph.add_node("sentiment", sentiment_analysis)
    # graph.add_node("debate", debate_protocol)
    # graph.add_node("risk", risk_assessment)
    # graph.add_node("decision", make_decision)
    # graph.add_node("human_review", human_review)
    # graph.add_node("execute", execute_trade)
    # graph.add_node("end", lambda state: {})
    # graph.add_node("retry", lambda state: {"iteration": state.get("iteration", 0) + 1, "retry_count": state.get("retry_count", 0) + 1})

    # ========== ADD EDGES ==========

    # Linear flow: START → fetch_data
    graph.add_edge(START, "fetch_data")

    # Parallel analysis: fetch_data → technical & sentiment
    # graph.add_edge("fetch_data", "technical")
    # graph.add_edge("fetch_data", "sentiment")

    # Conditional: debate or skip to risk
    # graph.add_conditional_edges(
    #     "technical",
    #     should_debate,
    #     {
    #         "debate": "debate",
    #         "skip_debate": "risk"
    #     }
    # )

    # graph.add_conditional_edges(
    #     "sentiment",
    #     should_debate,
    #     {
    #         "debate": "debate",
    #         "skip_debate": "risk"
    #     }
    # )

    # Flow: debate → risk
    # graph.add_edge("debate", "risk")

    # Flow: risk → decision
    # graph.add_edge("risk", "decision")

    # Conditional: human review or auto-approve
    # graph.add_conditional_edges(
    #     "decision",
    #     should_review,
    #     {
    #         "review": "human_review",
    #         "auto_approve": "execute"
    #     }
    # )

    # Flow: human_review → execute
    # graph.add_edge("human_review", "execute")

    # Conditional: execute or hold
    # graph.add_conditional_edges(
    #     "execute",
    #     should_execute,
    #     {
    #         "execute": "execute_trade",
    #         "hold": "end"
    #     }
    # )

    # Flow: execute_trade → end
    # graph.add_edge("execute_trade", "end")

    # Conditional: retry or end (from end node)
    # graph.add_conditional_edges(
    #     "end",
    #     should_retry,
    #     {
    #         "retry": "retry",
    #         "end": "END"
    #     }
    # )

    # ========== COMPILE GRAPH ==========

    # Get checkpointer for persistence
    checkpointer = get_checkpointer()

    # Compile with optional debug mode for LangSmith tracing
    compiled = graph.compile(
        checkpointer=checkpointer,
        debug=False  # Set to True to enable LangSmith tracing
    )

    return compiled

# ========== SINGLETON INSTANCE ==========

trading_graph = create_trading_graph()
