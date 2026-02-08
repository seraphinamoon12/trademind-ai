"""Nodes for data fetching in the LangGraph workflow."""

from datetime import datetime, timezone
from src.langgraph.state import TradingState
from src.langgraph.types import FetchMarketDataOutput
from src.data.providers import yfinance_provider
from src.data.indicators import TechnicalIndicators


async def fetch_market_data(state: TradingState) -> FetchMarketDataOutput:
    """
    Fetch market data from yfinance and calculate technical indicators.

    Args:
        state: Current trading state with symbol and timeframe

    Returns:
        State updates with market_data and technical_indicators
    """
    try:
        symbol = state["symbol"]
        timeframe = state["timeframe"]

        # Fetch OHLCV data
        data = await yfinance_provider.fetch_data(symbol, timeframe)

        # Calculate technical indicators
        indicators = TechnicalIndicators.calculate_all(data)

        return {
            "market_data": data.to_dict(),
            "technical_indicators": indicators,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": state.get("workflow_id", f"{symbol}_{int(datetime.now(timezone.utc).timestamp())}"),
            "iteration": state.get("iteration", 0),
            "current_node": "fetch_market_data"
        }

    except Exception as e:
        return {
            "error": f"Failed to fetch market data: {str(e)}",
            "current_node": "fetch_market_data"
        }
