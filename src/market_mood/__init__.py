"""Market Mood Detection Module.

This module provides infrastructure for detecting market sentiment through various
indicators including VIX, market breadth, put/call ratios, yield curves, and more.
"""

from .config import MarketMoodConfig
from .models import IndicatorValue, MoodScore, CacheEntry
from .data_providers.base import BaseDataProvider
from .data_providers.yahoo_provider import YahooFinanceProvider
from .data_providers.fred_provider import FREDProvider
from .engine import MoodCalculationEngine
from .signals import SignalGenerator
from .trends import TrendDetector
from .detector import MarketMoodDetector

__all__ = [
    'MarketMoodConfig',
    'IndicatorValue',
    'MoodScore',
    'CacheEntry',
    'BaseDataProvider',
    'YahooFinanceProvider',
    'FREDProvider',
    'MoodCalculationEngine',
    'SignalGenerator',
    'TrendDetector',
    'MarketMoodDetector',
]
