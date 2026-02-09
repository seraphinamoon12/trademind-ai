"""Nodes for data fetching in the LangGraph workflow."""

import time
import numpy as np
from datetime import datetime, timezone
from src.trading_graph.state import TradingState
from src.trading_graph.types import FetchMarketDataOutput
from src.data.providers import YahooFinanceProvider
from src.data.indicators import TechnicalIndicators


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for serialization."""
    if isinstance(obj, dict):
        return {str(k): convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(v) for v in obj)
    elif isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


async def fetch_market_data(state: TradingState) -> FetchMarketDataOutput:
    """
    Fetch market data from yfinance and calculate technical indicators.

    Args:
        state: Current trading state with symbol and timeframe

    Returns:
        State updates with market_data and technical_indicators
    """
    start_time = time.time()

    try:
        symbol = state["symbol"]
        timeframe = state["timeframe"]

        provider = YahooFinanceProvider()
        data = provider.get_historical(symbol, period="1y", interval=timeframe)

        indicators = TechnicalIndicators.get_latest_signals(TechnicalIndicators.add_all_indicators(data))

        elapsed = time.time() - start_time

        return {
            "market_data": convert_numpy_types(data.to_dict()),
            "technical_indicators": convert_numpy_types(indicators),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": state.get("workflow_id", f"{symbol}_{int(datetime.now(timezone.utc).timestamp())}"),
            "iteration": state.get("iteration", 0),
            "current_node": "fetch_market_data",
            "execution_time": elapsed
        }

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "error": f"Failed to fetch market data: {str(e)}",
            "current_node": "fetch_market_data",
            "execution_time": elapsed
        }
