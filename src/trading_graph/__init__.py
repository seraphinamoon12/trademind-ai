"""LangGraph-based trading agent orchestration for TradeMind AI."""

__all__ = ["create_trading_graph", "get_trading_graph"]

def __getattr__(name):
    if name in ["create_trading_graph", "get_trading_graph"]:
        from src.trading_graph.graph import create_trading_graph, get_trading_graph
        return create_trading_graph if name == "create_trading_graph" else get_trading_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
