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


def calculate_macd(prices: pd.Series) -> Dict[str, Any]:
    """
    Calculate MACD and return signal.

    Args:
        prices: Price series (typically closing prices)

    Returns:
        Dictionary with:
            - signal: "bullish", "bearish", or "neutral"
            - value: MACD line - signal line difference
    """
    if len(prices) < 35:
        return {"signal": "neutral", "value": 0.0}

    macd = ta.macd(prices)
    if macd is None:
        return {"signal": "neutral", "value": 0.0}

    macd_line = macd.iloc[-1, 0]  # MACD line
    signal_line = macd.iloc[-1, 1]  # Signal line

    if pd.isna(macd_line) or pd.isna(signal_line):
        return {"signal": "neutral", "value": 0.0}

    diff = macd_line - signal_line

    if diff > settings.macd_signal_threshold:
        signal = "bullish"
    elif diff < -settings.macd_signal_threshold:
        signal = "bearish"
    else:
        signal = "neutral"

    return {"signal": signal, "value": float(diff)}


def get_technical_summary(prices: pd.Series) -> Dict[str, Any]:
    """
    Get complete technical summary for price series.

    Args:
        prices: Price series (typically closing prices)

    Returns:
        Dict with RSI, MACD, and trend direction:
            - rsi: RSI value (0-100)
            - macd: Dict with signal and value
            - trend: "up" or "down"
    """
    return {
        "rsi": calculate_rsi(prices),
        "macd": calculate_macd(prices),
        "trend": "up" if prices.iloc[-1] > prices.iloc[-20:].mean() else "down"
    }
