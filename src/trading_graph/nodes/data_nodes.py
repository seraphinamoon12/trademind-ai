"""Nodes for data fetching in the LangGraph workflow."""

import time
from datetime import datetime, timezone
from src.trading_graph.state import TradingState
from src.trading_graph.types import FetchMarketDataOutput
from src.data.providers import YahooFinanceProvider
from src.data.indicators import TechnicalIndicators
from src.core.serialization import convert_numpy_types


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
        timeframe = state.get("timeframe", "1d")

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
