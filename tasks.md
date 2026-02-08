# TradeMind AI - Development Tasks

## Sentiment Agent Improvements (From Code Review)

### 🔴 Critical Priority

#### 1. Fix Config Naming Inconsistency ✅
- **Issue:** `zai_api_key` vs `zai_api_token` naming mismatch between config and agent
- **Impact:** May break in production
- **Files:** `src/config.py`, `src/agents/sentiment.py`
- **Action:** Align naming convention across codebase

#### 2. Refactor to Async HTTP Client ✅
- **Issue:** Using sync `httpx.post` instead of async `httpx.AsyncClient`
- **Impact:** Performance bottleneck, blocks event loop
- **File:** `src/agents/sentiment.py`
- **Action:** Replace with `async with httpx.AsyncClient() as client:`

#### 3. Move Imports to Top of File ✅
- **Issue:** `import re` inside method `_parse_sentiment_text`
- **Impact:** Code smell, repeated import overhead
- **File:** `src/agents/sentiment.py`
- **Action:** Move all imports to top of file

---

### 🟡 Medium Priority

#### 4. Add Retry Logic with Exponential Backoff ✅
- **Issue:** No retry mechanism for API failures
- **Impact:** Temporary API issues cause complete failure
- **File:** `src/agents/sentiment.py`
- **Action:** Add `@retry` decorator or manual retry loop
- **Example:**
  ```python
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
  async def _analyze_with_zai(self, ...)
  ```

#### 5. Move Hardcoded Values to Config ✅
- **Issue:** Hardcoded `temperature=0.3`, model name, timeouts
- **Impact:** Difficult to tune without code changes
- **Files:** `src/agents/sentiment.py`, `src/config.py`
- **Action:** Add to Settings class:
  - `zai_model: str = "glm-4.7"`
  - `zai_temperature: float = 0.3`
  - `zai_timeout: int = 30`

#### 6. Add Confidence Validation
- **Issue:** No validation that confidence is within 0-1 range
- **Impact:** Invalid values could propagate
- **File:** `src/agents/sentiment.py`
- **Action:** Add validation in `_sentiment_to_signal` method

#### 7. Improve Fallback Confidence Calculation
- **Issue:** Fallback uses hardcoded confidence (0.5, 0.8)
- **Impact:** Not proportional to actual momentum
- **File:** `src/agents/sentiment.py`
- **Action:** Calculate confidence from price momentum magnitude

#### 8. Add Sentiment Caching
- **Issue:** Re-analyzing same symbol multiple times
- **Impact:** Unnecessary API calls and latency
- **File:** `src/agents/sentiment.py`
- **Action:** Cache results for 15-30 minutes per symbol
- **Implementation:** Use Redis or in-memory cache with TTL

#### 9. Enhance Fallback Logic
- **Issue:** Simple momentum-based fallback
- **Impact:** Misses volume and other signals
- **File:** `src/agents/sentiment.py`
- **Action:** Add volume trend, RSI, MACD to fallback analysis

---

### 🟢 Low Priority / Nice to Have

#### 10. Add Debug Logging for API Calls
- **File:** `src/agents/sentiment.py`
- **Action:** Log API requests/responses at DEBUG level
- **Benefit:** Easier troubleshooting

#### 11. Add Unit/Integration Tests
- **Files:** `tests/test_sentiment_agent.py`
- **Coverage:**
  - API success/failure scenarios
  - JSON parsing
  - Text parsing fallback
  - Fallback logic
  - Config loading

#### 12. Add Circuit Breaker Pattern
- **File:** `src/agents/sentiment.py`
- **Action:** Stop calling API after N consecutive failures
- **Benefit:** Prevent cascading failures

#### 13. Multi-Timeframe Analysis
- **File:** `src/agents/sentiment.py`
- **Action:** Analyze 1d, 1w, 1m timeframes
- **Benefit:** More robust sentiment signal

#### 14. Store Sentiment History
- **Files:** `src/agents/sentiment.py`, `src/core/database.py`
- **Action:** Save sentiment results to database
- **Benefit:** Track sentiment trends over time

#### 15. Weight Confidence by Volatility
- **File:** `src/agents/sentiment.py`
- **Action:** Reduce confidence in high-volatility periods
- **Benefit:** More reliable signals

---

## Prompt Engineering Improvements

#### 16. Add Few-Shot Examples
- **File:** `src/agents/sentiment.py`
- **Action:** Include 2-3 examples in the prompt
- **Benefit:** Better formatted, consistent responses

#### 17. Include Market Context
- **File:** `src/agents/sentiment.py`
- **Action:** Add recent market events/news context
- **Benefit:** More informed sentiment analysis

#### 18. Ask for Key Factors
- **File:** `src/agents/sentiment.py`
- **Action:** Request key factors driving sentiment
- **Benefit:** Better explainability

#### 19. Chain-of-Thought Reasoning
- **File:** `src/agents/sentiment.py`
- **Action:** Ask LLM to reason step-by-step
- **Benefit:** More accurate sentiment classification

---

## Implementation Priority Order

1. Fix critical issues (1-3) - **Before production**
2. Add retry logic (4) - **Before production**
3. Move hardcoded values to config (5)
4. Add caching (8)
5. Improve fallback logic (9)
6. Add tests (11)
7. Add circuit breaker (12)
8. Implement prompt improvements (16-19)
9. Multi-timeframe and history (13-14)

---

## Notes

- Overall code structure is solid
- These improvements will improve reliability and maintainability
- Consider A/B testing sentiment signals before full deployment
- Monitor API costs with ZAI GLM-4.7

*Created: 2026-02-07*  
*Based on: OpenCode code review of sentiment agent implementation*
