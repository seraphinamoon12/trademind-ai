"""Base class for debate agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any
import httpx
import json
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class BaseDebateAgent(ABC):
    """Base class for BullAgent and BearAgent."""

    def __init__(self, perspective: str):
        """
        Initialize base debate agent.

        Args:
            perspective: "bullish" or "bearish"
        """
        self.perspective = perspective
        self.api_key = settings.zai_api_key
        self.base_url = "https://api.z.ai/api/paas/v4"
        self.model = "glm-4.7"

    def _build_prompt(
        self,
        symbol: str,
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> str:
        """Build prompt - shared logic."""
        rsi = technical_signals.get('data', {}).get('rsi', 'N/A')
        macd = technical_signals.get('data', {}).get('macd', 'N/A')
        trend = technical_signals.get('data', {}).get('trend', 'N/A')

        sentiment = sentiment_signals.get('data', {}).get('sentiment', 'N/A')
        sentiment_confidence = sentiment_signals.get('confidence', 'N/A')

        price = market_data.get('close', {}).get('current', 'N/A')
        change_5d = 'N/A'
        volume_ratio = 'N/A'

        if price != 'N/A' and len(market_data.get('close', {})) > 5:
            closes = list(market_data['close'].values())[-6:]
            change_5d = ((closes[-1] - closes[0]) / closes[0]) * 100

        if 'volume' in market_data:
            volumes = list(market_data['volume'].values())
            volume_avg = sum(volumes[-20:]) / min(20, len(volumes))
            volume_ratio = volumes[-1] / volume_avg if volume_avg > 0 else 1.0

        return f"""
You are a {self.perspective} stock analyst. Present the strongest {self.perspective} case for {symbol}.

Technical Analysis:
- RSI: {rsi}
- MACD: {macd}
- Trend: {trend}

Sentiment Analysis:
- Sentiment: {sentiment}
- Confidence: {sentiment_confidence}

Market Data:
- Current Price: ${price}
- 5-Day Change: {change_5d:.2f}%
- Volume vs Avg: {volume_ratio:.2f}x

Provide:
1. 3-5 strongest {self.perspective} arguments
2. Overall confidence score (0-1)
3. Key {self.perspective} factors (2-3 items)
4. Brief investment thesis (1-2 sentences)

Respond in JSON format:
{{
    "arguments": ["argument1", "argument2", ...],
    "confidence": 0.85,
    "key_factors": ["factor1", "factor2", ...],
    "thesis": "Brief investment thesis"
}}
"""

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call LLM - shared logic."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": f"You are an expert {self.perspective} stock analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=30
            )

            result = response.json()
            content = result['choices'][0]['message']['content']
            return json.loads(content)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallback handling."""
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")

        return {
            "arguments": [f"Technical indicators suggest {self.perspective} momentum"],
            "confidence": 0.5,
            "key_factors": ["Technical setup"],
            "thesis": f"Cautiously {self.perspective} based on technicals"
        }

    @abstractmethod
    async def generate_arguments(
        self,
        symbol: str,
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate arguments - implemented by subclasses."""
        pass

    def _validate_inputs(
        self,
        symbol: str,
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> None:
        """Validate input parameters."""
        if not symbol or not isinstance(symbol, str) or len(symbol) > 5:
            raise ValueError(f"Invalid symbol: {symbol}")

        if not technical_signals:
            raise ValueError("technical_signals required")

        if not sentiment_signals:
            raise ValueError("sentiment_signals required")

        if not market_data:
            raise ValueError("market_data required")
