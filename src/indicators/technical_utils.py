"""Shared technical indicator utilities."""
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, Optional

from src.config import settings


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Calculate RSI for a price series.

    Args:
        prices: Price series (typically closing prices)
        period: RSI period (default 14)

    Returns:
        RSI value (0-100)
    """
    if len(prices) < period:
        return 50.0  # Neutral if insufficient data

    rsi = ta.rsi(prices, length=period)
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
