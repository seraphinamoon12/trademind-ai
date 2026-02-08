"""Sentiment Analysis Agent using ZAI GLM-4.7."""
from typing import Optional, Dict, Any, Callable
import pandas as pd
import os
import httpx
import json
import logging
import re
import asyncio
import time
from functools import wraps
from datetime import datetime

from src.agents.base import BaseAgent, AgentSignal, AgentDecision
from src.config import settings

logger = logging.getLogger(__name__)


def async_retry(max_attempts: int = 3, base_wait: float = 1.0, max_wait: float = 10.0):
    """
    Decorator for async retry with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = Exception("Unknown error")
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = min(base_wait * (2 ** attempt), max_wait)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


class SentimentAgent(BaseAgent):
    """
    Sentiment analysis agent using ZAI GLM-4.7 model.
    
    Analyzes recent price action and market data to determine
    market sentiment (bullish, bearish, or neutral).
    """
    
    name = "sentiment"
    weight = 0.30  # 30% weight in orchestrator
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_key = settings.zai_api_key or os.getenv('ZAI_API_KEY')
        self.base_url = "https://api.z.ai/api/paas/v4"
        self.model = settings.zai_model
        self.temperature = settings.zai_temperature
        self.timeout = settings.zai_timeout
        self._sentiment_cache = {}
        self._cache_ttl = 1800  # 30 minutes cache TTL
        
        if not self.api_key:
            logger.warning("ZAI_API_KEY not set - sentiment agent will use fallback logic")
    
    def _get_cache_key(self, symbol: str) -> str:
        """Generate cache key based on symbol + date (not time)."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{symbol}:{today}"
    
    def _get_cached_result(self, cache_key: str) -> Optional[AgentSignal]:
        """Get cached result if available and not expired."""
        if cache_key not in self._sentiment_cache:
            return None
        
        cached_data = self._sentiment_cache[cache_key]
        timestamp = cached_data['timestamp']
        
        # Check if cache is still valid
        if time.time() - timestamp > self._cache_ttl:
            # Cache expired, remove it
            del self._sentiment_cache[cache_key]
            return None
        
        return cached_data['signal']
    
    def _cache_result(self, cache_key: str, signal: AgentSignal):
        """Store sentiment result in cache."""
        self._sentiment_cache[cache_key] = {
            'signal': signal,
            'timestamp': time.time()
        }
    
    async def analyze(self, symbol: str, data: pd.DataFrame, **context) -> AgentSignal:
        """
        Analyze sentiment using ZAI GLM-4.7 model.
        
        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame
            context: Additional context
            
        Returns:
            AgentSignal with sentiment-based decision
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(symbol)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"Using cached sentiment for {symbol}")
                return cached_result
            
            # Prepare market data summary
            market_summary = self._prepare_market_summary(data)
            logger.debug(f"Market summary for {symbol}: {market_summary}")
            
            # If no API key, use fallback logic
            if not self.api_key:
                signal = self._fallback_analysis(symbol, data)
                self._cache_result(cache_key, signal)
                logger.debug(f"Fallback sentiment for {symbol}: {signal.decision} (confidence: {signal.confidence:.2f})")
                return signal
            
            # Call ZAI API for sentiment analysis
            sentiment = await self._analyze_with_zai(symbol, market_summary)
            
            # Convert sentiment to trading signal
            signal = self._sentiment_to_signal(symbol, sentiment, market_summary)
            
            # Cache the result
            self._cache_result(cache_key, signal)
            
            logger.debug(f"Final sentiment for {symbol}: {signal.decision} (confidence: {signal.confidence:.2f})")
            return signal
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for {symbol}: {e}")
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.0,
                reasoning=f"Sentiment analysis error: {str(e)}"
            )
    
    def _prepare_market_summary(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Prepare market data summary for LLM analysis."""
        if data.empty:
            return {}
        
        # Get last 5 days of data
        recent = data.tail(5)
        
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest
        
        # Calculate metrics
        price_change = ((latest['close'] - prev['close']) / prev['close']) * 100
        volume_avg = data['volume'].tail(20).mean()
        volume_latest = latest['volume']
        
        return {
            'current_price': round(latest['close'], 2),
            'previous_close': round(prev['close'], 2),
            'price_change_pct': round(price_change, 2),
            'volume': int(volume_latest),
            'volume_avg_20d': int(volume_avg),
            'volume_ratio': round(volume_latest / volume_avg, 2) if volume_avg > 0 else 1.0,
            'high_5d': round(recent['high'].max(), 2),
            'low_5d': round(recent['low'].min(), 2),
            'price_range_pct': round(((recent['high'].max() - recent['low'].min()) / recent['low'].min()) * 100, 2)
        }
    
    @async_retry(max_attempts=3, base_wait=1.0, max_wait=10.0)
    async def _analyze_with_zai(self, symbol: str, market_summary: Dict) -> Dict[str, Any]:
        """Call ZAI GLM-4.7 API for sentiment analysis."""
        
        prompt = f"""Analyze the market sentiment for {symbol} based on the following recent data:

Current Price: ${market_summary['current_price']}
Previous Close: ${market_summary['previous_close']}
Price Change: {market_summary['price_change_pct']}%
Volume: {market_summary['volume']:,} (avg: {market_summary['volume_avg_20d']:,})
Volume Ratio: {market_summary['volume_ratio']}x (indicates trading intensity)
5-Day High: ${market_summary['high_5d']}
5-Day Low: ${market_summary['low_5d']}
Price Range (5d): {market_summary['price_range_pct']}%

Consider these factors:
- Price momentum direction and strength
- Volume patterns (high volume on price moves confirms trend)
- Price position within recent range
- Overall market structure

Example analyses:
Example 1: Stock up 3.5% with volume 2.1x average, trading near 5-day high
→ Sentiment: bullish (strong upward momentum with conviction)

Example 2: Stock down 1.2% with volume 0.6x average, near middle of 5-day range
→ Sentiment: neutral (moderate decline on low volume, lack of conviction)

Provide a sentiment analysis with:
1. Overall sentiment (bullish/bearish/neutral)
2. Confidence score (0.0 to 1.0)
3. Key reasoning (identify 2-3 main factors driving sentiment)

Respond in JSON format:
{{
    "sentiment": "bullish|bearish|neutral",
    "confidence": 0.85,
    "reasoning": "Brief explanation of the sentiment with key factors"
}}"""

        try:
            logger.debug(f"Sending sentiment analysis request to ZAI API for {symbol}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a financial market sentiment analyst. Analyze price and volume data to determine market sentiment."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": self.temperature,
                        "max_tokens": 200
                    },
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
            
            # Parse the response
            content = result['choices'][0]['message']['content']
            logger.debug(f"ZAI API response for {symbol}: {content}")
            
            # Try to parse JSON from content
            try:
                # Find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    sentiment_data = json.loads(json_str)
                else:
                    # Fallback parsing
                    sentiment_data = self._parse_sentiment_text(content)
                
                return sentiment_data
                
            except json.JSONDecodeError:
                # Fallback to text parsing
                return self._parse_sentiment_text(content)
                
        except Exception as e:
            logger.error(f"ZAI API error: {e}")
            raise
    
    def _parse_sentiment_text(self, text: str) -> Dict[str, Any]:
        """Parse sentiment from text response when JSON parsing fails."""
        text_lower = text.lower()
        
        # Determine sentiment
        if 'bullish' in text_lower:
            sentiment = "bullish"
        elif 'bearish' in text_lower:
            sentiment = "bearish"
        else:
            sentiment = "neutral"
        
        # Extract confidence (look for a number between 0 and 1)
        confidence_match = re.search(r'(\d+\.?\d*)', text)
        confidence = float(confidence_match.group(1)) if confidence_match else 0.5
        if confidence > 1:
            confidence = confidence / 100  # Handle percentage format
        
        return {
            "sentiment": sentiment,
            "confidence": min(max(confidence, 0.0), 1.0),
            "reasoning": text[:200]  # First 200 chars as reasoning
        }
    
    def _sentiment_to_signal(
        self,
        symbol: str,
        sentiment: Dict[str, Any],
        market_summary: Dict
    ) -> AgentSignal:
        """Convert sentiment analysis to trading signal."""
        
        sentiment_label = sentiment.get('sentiment', 'neutral').lower()
        confidence = float(sentiment.get('confidence', 0.5))
        reasoning = sentiment.get('reasoning', 'No reasoning provided')
        
        # Validate confidence is within 0-1 range
        if confidence < 0 or confidence > 1:
            logger.warning(
                f"Invalid confidence {confidence:.3f} for {symbol}, clamping to [0, 1] range"
            )
            confidence = max(0.0, min(1.0, confidence))
        
        # Map sentiment to decision
        if sentiment_label == 'bullish':
            decision = AgentDecision.BUY
        elif sentiment_label == 'bearish':
            decision = AgentDecision.SELL
        else:
            decision = AgentDecision.HOLD
        
        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            decision=decision,
            confidence=confidence,
            reasoning=f"Sentiment: {sentiment_label} (confidence: {confidence:.2f}) - {reasoning}",
            data={
                'sentiment': sentiment_label,
                'market_summary': market_summary
            }
        )
    
    def _fallback_analysis(self, symbol: str, data: pd.DataFrame) -> AgentSignal:
        """Fallback analysis when ZAI API is not available."""
        if data.empty or len(data) < 2:
            return AgentSignal(
                agent_name=self.name,
                symbol=symbol,
                decision=AgentDecision.HOLD,
                confidence=0.0,
                reasoning="Insufficient data for sentiment analysis"
            )
        
        # Price momentum
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        price_change = ((latest['close'] - prev['close']) / prev['close']) * 100
        
        # Volume trend analysis
        volume_avg_20d = data['volume'].tail(20).mean()
        volume_avg_5d = data['volume'].tail(5).mean()
        volume_latest = latest['volume']
        volume_ratio = volume_latest / volume_avg_20d if volume_avg_20d > 0 else 1.0
        volume_trend = "increasing" if volume_avg_5d > volume_avg_20d * 1.1 else "decreasing" if volume_avg_5d < volume_avg_20d * 0.9 else "stable"
        
        # RSI calculation (if enough data)
        rsi_value = None
        if len(data) >= 15:
            rsi_value = self._calculate_rsi(data['close'], period=14)
        
        # Calculate confidence from price momentum magnitude, capped at 0.8
        confidence = min(abs(price_change) / 5.0, 0.8)
        
        # Enhance confidence with volume ratio
        if volume_ratio > 1.5:
            confidence = min(confidence * 1.2, 0.8)
        
        # Determine sentiment with enhanced factors
        bullish_factors = []
        bearish_factors = []
        
        if price_change > 2:
            bullish_factors.append(f"price momentum +{price_change:.2f}%")
        elif price_change < -2:
            bearish_factors.append(f"price momentum {price_change:.2f}%")
        
        if volume_ratio > 1.5:
            bullish_factors.append(f"high volume {volume_ratio:.1f}x")
        elif volume_ratio < 0.7:
            bearish_factors.append(f"low volume {volume_ratio:.1f}x")
        
        if rsi_value is not None:
            if rsi_value < 30:
                bullish_factors.append(f"oversold RSI {rsi_value:.1f}")
            elif rsi_value > 70:
                bearish_factors.append(f"overbought RSI {rsi_value:.1f}")
        
        # Make decision based on factors
        bullish_score = len(bullish_factors)
        bearish_score = len(bearish_factors)
        
        if bullish_score > bearish_score:
            decision = AgentDecision.BUY
            reasoning = ", ".join(bullish_factors)
        elif bearish_score > bullish_score:
            decision = AgentDecision.SELL
            reasoning = ", ".join(bearish_factors)
        else:
            decision = AgentDecision.HOLD
            if bullish_factors or bearish_factors:
                reasoning = "mixed signals: " + ", ".join(bullish_factors + bearish_factors)
            else:
                reasoning = f"neutral price action ({price_change:.2f}%)"
        
        return AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            decision=decision,
            confidence=confidence,
            reasoning=f"[Fallback] {reasoning}"
        )
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])
