"""Multi-agent debate system for trading decisions."""

import httpx
import json
import logging
from typing import Dict, Any

from src.config import settings
from .base_debate_agent import BaseDebateAgent

logger = logging.getLogger(__name__)


class BullAgent(BaseDebateAgent):
    """
    Agent that generates bullish arguments for a stock.

    Uses LLM to analyze technical and fundamental factors
    and present the strongest bullish case.
    """

    def __init__(self):
        super().__init__("bullish")

    async def generate_arguments(
        self,
        symbol: str,
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate bullish arguments for a stock.

        Args:
            symbol: Stock symbol
            technical_signals: Technical analysis results
            sentiment_signals: Sentiment analysis results
            market_data: Current market data

        Returns:
            Dictionary with:
                - arguments: List of bullish arguments
                - confidence: Float 0-1
                - key_factors: List of key bullish factors
                - thesis: String summary of bull case
        """
        self._validate_inputs(symbol, technical_signals, sentiment_signals, market_data)

        if not self.api_key:
            logger.warning("ZAI_API_KEY not set - using fallback bull case")
            return self._fallback_bull_case(symbol)

        prompt = self._build_prompt(symbol, technical_signals, sentiment_signals, market_data)

        try:
            result = await self._call_llm(prompt)
            bull_case = self._parse_json_response(json.dumps(result))

            return {
                "arguments": bull_case.get("arguments", []),
                "confidence": float(bull_case.get("confidence", 0.5)),
                "key_factors": bull_case.get("key_factors", []),
                "thesis": bull_case.get("thesis", ""),
                "agent": "bull"
            }

        except Exception as e:
            logger.error(f"BullAgent failed for {symbol}: {e}")
            return self._fallback_bull_case(symbol)
    
    def _fallback_bull_case(self, symbol: str) -> Dict[str, Any]:
        """Fallback if LLM fails."""
        return {
            "arguments": ["Technical indicators suggest upward momentum"],
            "confidence": 0.5,
            "key_factors": ["Technical setup"],
            "thesis": f"Cautiously bullish on {symbol} based on technicals",
            "agent": "bull"
        }


class BearAgent(BaseDebateAgent):
    """
    Agent that generates bearish arguments for a stock.

    Uses LLM to analyze technical and fundamental factors
    and present the strongest bearish case.
    """

    def __init__(self):
        super().__init__("bearish")

    async def generate_arguments(
        self,
        symbol: str,
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate bearish arguments for a stock.

        Args:
            symbol: Stock symbol
            technical_signals: Technical analysis results
            sentiment_signals: Sentiment analysis results
            market_data: Current market data

        Returns:
            Dictionary with:
                - arguments: List of bearish arguments
                - confidence: Float 0-1
                - key_factors: List of key bearish factors
                - thesis: String summary of bear case
        """
        self._validate_inputs(symbol, technical_signals, sentiment_signals, market_data)

        if not self.api_key:
            logger.warning("ZAI_API_KEY not set - using fallback bear case")
            return self._fallback_bear_case(symbol)

        prompt = self._build_prompt(symbol, technical_signals, sentiment_signals, market_data)

        try:
            result = await self._call_llm(prompt)
            bear_case = self._parse_json_response(json.dumps(result))

            return {
                "arguments": bear_case.get("arguments", []),
                "confidence": float(bear_case.get("confidence", 0.5)),
                "key_factors": bear_case.get("key_factors", []),
                "thesis": bear_case.get("thesis", ""),
                "agent": "bear"
            }

        except Exception as e:
            logger.error(f"BearAgent failed for {symbol}: {e}")
            return self._fallback_bear_case(symbol)
    
    def _fallback_bear_case(self, symbol: str) -> Dict[str, Any]:
        """Fallback if LLM fails."""
        return {
            "arguments": ["Technical indicators suggest downward pressure"],
            "confidence": 0.5,
            "key_factors": ["Technical weakness"],
            "thesis": f"Cautiously bearish on {symbol} based on technicals",
            "agent": "bear"
        }


class JudgeAgent(BaseDebateAgent):
    """
    Agent that evaluates Bull vs Bear arguments and makes final decision.
    """

    def __init__(self):
        super().__init__("impartial judge")
    
    async def evaluate_debate(
        self,
        symbol: str,
        bull_case: Dict[str, Any],
        bear_case: Dict[str, Any],
        technical_signals: Dict[str, Any],
        sentiment_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate both sides and render a decision.
        
        Returns:
            Dictionary with:
                - winner: "bull" or "bear"
                - confidence: Float 0-1
                - reasoning: Explanation of decision
                - recommendation: "BUY", "SELL", or "HOLD"
                - key_points: List of decisive factors
        """
        if not self.api_key:
            logger.warning("ZAI_API_KEY not set - using fallback judge decision")
            return self._fallback_judge_decision(symbol, bull_case, bear_case)
        
        rsi = technical_signals.get('data', {}).get('rsi', 'N/A')
        macd = technical_signals.get('data', {}).get('macd', 'N/A')
        
        prompt = f"""
You are an impartial investment judge evaluating a debate about {symbol}.

BULL CASE:
- Confidence: {bull_case.get('confidence', 0)}
- Thesis: {bull_case.get('thesis', '')}
- Key Arguments: {bull_case.get('arguments', [])}

BEAR CASE:
- Confidence: {bear_case.get('confidence', 0)}
- Thesis: {bear_case.get('thesis', '')}
- Key Arguments: {bear_case.get('arguments', [])}

TECHNICAL CONTEXT:
- RSI: {rsi}
- MACD: {macd}

Evaluate both cases and provide:
1. Winner (bull or bear)
2. Confidence in decision (0-1)
3. Detailed reasoning
4. Trading recommendation (BUY, SELL, HOLD)
5. Key decisive factors

Respond in JSON format:
{{
    "winner": "bull",
    "confidence": 0.75,
    "reasoning": "Detailed explanation",
    "recommendation": "BUY",
    "key_points": ["factor1", "factor2", ...]
}}
"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an impartial investment judge."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 600
                    },
                    timeout=30
                )
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON response
                decision = self._parse_json_response(content)
                
                # Map winner to recommendation
                winner = decision.get("winner", "bull")
                if winner == "bull":
                    recommendation = "BUY"
                elif winner == "bear":
                    recommendation = "SELL"
                else:
                    recommendation = "HOLD"
                
                return {
                    "winner": winner,
                    "confidence": float(decision.get("confidence", 0.5)),
                    "reasoning": decision.get("reasoning", ""),
                    "recommendation": recommendation,
                    "key_points": decision.get("key_points", []),
                    "agent": "judge"
                }
                
        except Exception as e:
            logger.error(f"JudgeAgent failed for {symbol}: {e}")
            return self._fallback_judge_decision(symbol, bull_case, bear_case)
    
    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with fallback handling."""
        try:
            # Try to find JSON in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
        
        # Return default structure
        return {
            "winner": "bull",
            "confidence": 0.5,
            "reasoning": "Unable to determine winner due to analysis error",
            "recommendation": "HOLD",
            "key_points": ["Analysis error - holding"]
        }
    
    def _fallback_judge_decision(
        self,
        symbol: str,
        bull_case: Dict[str, Any],
        bear_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback if LLM fails."""
        bull_confidence = bull_case.get("confidence", 0.5)
        bear_confidence = bear_case.get("confidence", 0.5)
        
        if bull_confidence > bear_confidence:
            winner = "bull"
            recommendation = "BUY"
            confidence = bull_confidence
            reasoning = f"Bull case more confident ({bull_confidence:.2f} vs {bear_confidence:.2f})"
        elif bear_confidence > bull_confidence:
            winner = "bear"
            recommendation = "SELL"
            confidence = bear_confidence
            reasoning = f"Bear case more confident ({bear_confidence:.2f} vs {bull_confidence:.2f})"
        else:
            winner = "tie"
            recommendation = "HOLD"
            confidence = 0.5
            reasoning = "Both cases equally confident - hold position"
        
        return {
            "winner": winner,
            "confidence": confidence,
            "reasoning": reasoning,
            "recommendation": recommendation,
            "key_points": [reasoning],
            "agent": "judge"
        }
