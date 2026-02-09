"""Technical Analysis Agent."""
import pandas as pd
from typing import Optional, Dict, Any
import time
import asyncio
from datetime import datetime, timezone
import pandas_ta as ta

from src.agents.base import BaseAgent, AgentSignal, AgentDecision
from src.data.indicators import TechnicalIndicators
from src.strategies.rsi_reversion import RSIMeanReversionStrategy
from src.strategies.ma_crossover import MACrossoverStrategy
from src.config import settings
from src.core.cache import generate_symbol_key


class TechnicalAgent(BaseAgent):
    """
    Technical Analysis Agent.
    
    Uses rule-based strategies (RSI, MA Crossover) to generate signals.
    No LLM - pure technical analysis.
    
    Features:
    - Multi-timeframe support (1m, 5m, 15m, 1h, 1d)
    - Indicator result caching (5 min TTL)
    - Concurrent signal generation
    """
    
    name = "technical"
    weight = settings.technical_weight
    
    def __init__(self, **kwargs):
        """
        Initialize TechnicalAgent with strategies and caching.

        Args:
            **kwargs: Additional keyword arguments passed to BaseAgent
        """
        super().__init__(**kwargs)
        self.rsi_strategy = RSIMeanReversionStrategy()
        self.ma_strategy = MACrossoverStrategy()
        self._indicator_cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def _get_cached_indicators(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached indicator results if available and not expired."""
        if cache_key not in self._indicator_cache:
            return None
        
        cached_data = self._indicator_cache[cache_key]
        timestamp = cached_data['timestamp']
        
        if time.time() - timestamp > self._cache_ttl:
            del self._indicator_cache[cache_key]
            return None
        
        return cached_data['indicators']
    
    def _cache_indicators(self, cache_key: str, indicators: Dict[str, Any]):
        """Store indicator results in cache."""
        self._indicator_cache[cache_key] = {
            'indicators': indicators,
            'timestamp': time.time()
        }
    
    @staticmethod
    def _calculate_rsi(data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate RSI indicator."""
        try:
            close = data['close']
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            rsi_series = ta.rsi(close, length=period)  # type: ignore[arg-type]
            return float(rsi_series.iloc[-1]) if not rsi_series.empty else None
        except Exception:
            return None

    @staticmethod
    def _calculate_macd(data: pd.DataFrame) -> Optional[Dict[str, float]]:
        """Calculate MACD indicator."""
        try:
            close = data['close']
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            macd_result = ta.macd(close, fast=12, slow=26, signal=9)  # type: ignore[arg-type]
            if macd_result is None or macd_result.empty:
                return None
            return {
                'macd': float(macd_result.iloc[-1]['MACD_12_26_9']),
                'signal': float(macd_result.iloc[-1]['MACDs_12_26_9']),
                'histogram': float(macd_result.iloc[-1]['MACDh_12_26_9'])
            }
        except Exception:
            return None

    @staticmethod
    def _calculate_sma(data: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate SMA indicator."""
        try:
            close = data['close']
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            sma_series = ta.sma(close, length=period)  # type: ignore[arg-type]
            return float(sma_series.iloc[-1]) if not sma_series.empty else None
        except Exception:
            return None

    @staticmethod
    def _calculate_ema(data: pd.DataFrame, period: int) -> Optional[float]:
        """Calculate EMA indicator."""
        try:
            close = data['close']
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            ema_series = ta.ema(close, length=period)  # type: ignore[arg-type]
            return float(ema_series.iloc[-1]) if not ema_series.empty else None
        except Exception:
            return None

    @staticmethod
    def _calculate_bollinger_bands(data: pd.DataFrame, period: int = 20) -> Optional[Dict[str, Optional[float]]]:
        """Calculate Bollinger Bands indicator."""
        try:
            close = data['close']
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            bb_result = ta.bbands(close, length=period, std=2)  # type: ignore[arg-type]
            if bb_result is None or bb_result.empty:
                return None
            cols = bb_result.columns.tolist()
            upper_col = [c for c in cols if 'BBU' in c][0] if any('BBU' in c for c in cols) else None
            lower_col = [c for c in cols if 'BBL' in c][0] if any('BBL' in c for c in cols) else None
            middle_col = [c for c in cols if 'BBM' in c][0] if any('BBM' in c for c in cols) else None

            return {
                'upper': float(bb_result.iloc[-1][upper_col]) if upper_col else None,
                'middle': float(bb_result.iloc[-1][middle_col]) if middle_col else None,
                'lower': float(bb_result.iloc[-1][lower_col]) if lower_col else None
            }
        except Exception:
            return None

    @staticmethod
    def _calculate_atr(data: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate ATR indicator."""
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            if not isinstance(high, pd.Series):
                high = pd.Series(high)
            if not isinstance(low, pd.Series):
                low = pd.Series(low)
            if not isinstance(close, pd.Series):
                close = pd.Series(close)
            atr_series = ta.atr(high, low, close, length=period)  # type: ignore[arg-type]
            return float(atr_series.iloc[-1]) if not atr_series.empty else None
        except Exception:
            return None
    
    async def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators concurrently."""
        if data is None or data.empty:
            return {}
        
        try:
            tasks = [
                asyncio.to_thread(self._calculate_rsi, data, 14),
                asyncio.to_thread(self._calculate_macd, data),
                asyncio.to_thread(self._calculate_sma, data, 50),
                asyncio.to_thread(self._calculate_sma, data, 200),
                asyncio.to_thread(self._calculate_ema, data, 20),
                asyncio.to_thread(self._calculate_bollinger_bands, data, 20),
                asyncio.to_thread(self._calculate_atr, data, 14)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            indicator_dict = {
                'rsi': results[0] if not isinstance(results[0], Exception) else None,
                'macd': results[1] if not isinstance(results[1], Exception) else None,
                'sma_50': results[2] if not isinstance(results[2], Exception) else None,
                'sma_200': results[3] if not isinstance(results[3], Exception) else None,
                'ema_20': results[4] if not isinstance(results[4], Exception) else None,
                'bollinger': results[5] if not isinstance(results[5], Exception) else None,
                'atr': results[6] if not isinstance(results[6], Exception) else None
            }
            
            return indicator_dict
        except Exception as e:
            return {}
    
    async def _analyze_timeframe(self, symbol: str, data: pd.DataFrame, timeframe: str) -> Dict[str, Any]:
        """Analyze a specific timeframe."""
        cache_key = generate_symbol_key(symbol, timeframe, 'indicators')
        cached = self._get_cached_indicators(cache_key)
        if cached:
            return cached
        
        indicators = await self._calculate_indicators(data)
        self._cache_indicators(cache_key, indicators)
        
        return indicators
    
    async def analyze(self, symbol: str, data: pd.DataFrame, **context) -> AgentSignal:
        """
        Analyze technical indicators and generate trading signals.

        Args:
            symbol: Stock symbol to analyze
            data: OHLCV DataFrame with historical data
            **context: Additional context parameters
                - timeframe: Timeframe for analysis (e.g., '1d', '1h', '5m')

        Returns:
            AgentSignal with:
                - decision: AgentDecision (BUY, SELL, or HOLD)
                - confidence: Float between 0 and 1
                - reasoning: String explanation of the decision
                - data: Dict containing indicators_summary and timeframe
        """
        timeframe = context.get('timeframe', '1d')
        
        if data is None or data.empty:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.0,
                reasoning="No data available"
            )
        
        # Get indicators with caching and multi-timeframe support
        indicators = await self._analyze_timeframe(symbol, data, timeframe)
        
        # Generate signals from both strategies
        signals = []
        
        if settings.rsi_enabled:
            rsi_signal = self.rsi_strategy.generate_signal(data, symbol)
            if rsi_signal:
                signals.append(rsi_signal)
        
        if settings.ma_enabled:
            ma_signal = self.ma_strategy.generate_signal(data, symbol)
            if ma_signal:
                signals.append(ma_signal)
        
        if not signals:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.5,
                reasoning="No clear technical signals",
                data={'indicators': indicators, 'timeframe': timeframe}
            )
        
        # Combine signals - take the one with highest confidence
        best_signal = max(signals, key=lambda s: s.confidence)
        
        # Map SignalType to AgentDecision
        decision_map = {
            "BUY": AgentDecision.BUY,
            "SELL": AgentDecision.SELL,
            "HOLD": AgentDecision.HOLD
        }
        
        # Build reasoning
        reasoning_parts = []
        for sig in signals:
            reasoning_parts.append(
                f"{sig.strategy}: {sig.signal.value} "
                f"(confidence: {sig.confidence})"
            )
        
        # Enhance reasoning with indicator data
        if indicators:
            indicator_summary = []
            if indicators.get('rsi') is not None:
                indicator_summary.append(f"RSI={indicators['rsi']:.1f}")
            if indicators.get('macd') and indicators['macd'].get('histogram') is not None:
                indicator_summary.append(f"MACD={indicators['macd']['histogram']:.3f}")
            if indicator_summary:
                reasoning_parts.append(f"Indicators: {', '.join(indicator_summary)}")
        
        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            decision=decision_map.get(best_signal.signal.value, AgentDecision.HOLD),
            confidence=best_signal.confidence,
            reasoning=f"[{timeframe}] Selected {best_signal.strategy}. " + "; ".join(reasoning_parts),
            data={
                'selected_strategy': best_signal.strategy,
                'all_signals': [
                    {
                        'strategy': s.strategy,
                        'signal': s.signal.value,
                        'confidence': s.confidence,
                        'metadata': s.metadata
                    }
                    for s in signals
                ],
                'indicators': indicators,
                'timeframe': timeframe
            }
        )
