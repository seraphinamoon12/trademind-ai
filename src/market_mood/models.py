"""Data models for market mood indicators."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum


class IndicatorType(str, Enum):
    """Types of mood indicators."""
    VIX = "vix"
    MARKET_BREADTH = "market_breadth"
    PUT_CALL_RATIO = "put_call_ratio"
    MA_TRENDS = "ma_trends"
    FEAR_GREED = "fear_greed"
    DXY = "dxy"
    CREDIT_SPREADS = "credit_spreads"
    YIELD_CURVE = "yield_curve"


class IndicatorValue(BaseModel):
    """Represents a single indicator value with metadata."""
    
    indicator_type: IndicatorType
    value: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"IndicatorValue(type={self.indicator_type}, value={self.value}, source={self.source})"


class MoodScore(BaseModel):
    """Overall market mood score composite."""
    
    overall_score: float = Field(ge=0, le=100)  # 0-100 scale
    sentiment: Literal["extreme_fear", "fear", "neutral", "greed", "extreme_greed"]
    components: Dict[IndicatorType, float] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = Field(ge=0, le=1)  # Confidence score based on data availability
    
    @classmethod
    def from_components(cls, components: Dict[IndicatorType, float]) -> 'MoodScore':
        """Create a MoodScore from component values."""
        if not components:
            return cls(overall_score=50.0, sentiment="neutral", confidence=0.0)
        
        # Calculate weighted average (simplified)
        valid_values = {k: v for k, v in components.items() if v is not None}
        if not valid_values:
            return cls(overall_score=50.0, sentiment="neutral", confidence=0.0)
        
        # Equal weights for simplicity, can be refined
        weights = {k: 1.0 for k in valid_values.keys()}
        total_weight = sum(weights.values())
        
        weighted_score = sum(value * weights[k] for k, value in valid_values.items()) / total_weight
        
        # Determine sentiment
        if weighted_score <= 10:
            sentiment = "extreme_fear"
        elif weighted_score <= 30:
            sentiment = "fear"
        elif weighted_score <= 45:
            sentiment = "neutral"
        elif weighted_score <= 70:
            sentiment = "greed"
        else:
            sentiment = "extreme_greed"
        
        # Confidence based on data completeness
        confidence = len(valid_values) / len(components)
        
        return cls(
            overall_score=weighted_score,
            sentiment=sentiment,
            components=valid_values,
            confidence=confidence
        )


class CacheEntry(BaseModel):
    """Cache entry for indicator data."""
    
    key: str
    value: Any
    ttl: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    
    @property
    def expiration_time(self) -> Optional[datetime]:
        """Calculate expiration time."""
        return self.created_at + timedelta(seconds=self.ttl)


class MarketBreadthData(BaseModel):
    """Market breadth indicator data."""
    
    advance_decline_ratio: float
    new_highs: int
    new_lows: int
    advancing_volume: int
    declining_volume: int
    
    def get_breadth_score(self) -> float:
        """Calculate breadth score (0-100)."""
        if self.advancing_volume + self.declining_volume == 0:
            return 50.0
        
        adv_vol_pct = self.advancing_volume / (self.advancing_volume + self.declining_volume)
        
        if self.advance_decline_ratio >= 2:
            return 90.0
        elif self.advance_decline_ratio >= 1.5:
            return 75.0
        elif self.advance_decline_ratio >= 1:
            return 60.0
        elif self.advance_decline_ratio >= 0.67:
            return 50.0
        elif self.advance_decline_ratio >= 0.5:
            return 35.0
        elif self.advance_decline_ratio >= 0.33:
            return 20.0
        else:
            return 10.0


class MATrendData(BaseModel):
    """Moving average trend data."""
    
    symbol: str
    price_above_50ma: bool
    price_above_200ma: bool
    ma50_slope: float
    ma200_slope: float
    
    def get_trend_score(self) -> float:
        """Calculate MA trend score (0-100)."""
        score = 50.0
        
        if self.price_above_200ma:
            score += 20
        if self.price_above_50ma:
            score += 15
        if self.ma50_slope > 0:
            score += 10
        if self.ma200_slope > 0:
            score += 5
        
        return min(100.0, max(0.0, score))


class FearGreedComponents(BaseModel):
    """Fear & Greed indicator components from FRED data."""
    
    momentum: Optional[float] = None
    breadth: Optional[float] = None
    put_call: Optional[float] = None
    safe_haven: Optional[float] = None
    junk_bond: Optional[float] = None
    
    def get_composite_score(self) -> float:
        """Calculate composite Fear & Greed score (0-100)."""
        valid_values = [v for v in [
            self.momentum,
            self.breadth,
            self.put_call,
            self.safe_haven,
            self.junk_bond
        ] if v is not None]
        
        if not valid_values:
            return 50.0
        
        return sum(valid_values) / len(valid_values)


class YieldCurveData(BaseModel):
    """Yield curve data."""
    
    spread_10y_2y: float
    spread_10y_3m: float
    
    def get_yield_curve_score(self) -> float:
        """Calculate yield curve score (0-100, higher = steeper curve)."""
        if self.spread_10y_2y > 0.5:
            return 90.0
        elif self.spread_10y_2y > 0:
            return 75.0
        elif self.spread_10y_2y > -0.25:
            return 50.0
        elif self.spread_10y_2y > -0.5:
            return 25.0
        else:
            return 10.0


class CreditSpreadData(BaseModel):
    """Credit spread data."""
    
    spread_baa_aaa: float
    spread_high_yield_treasury: float
    
    def get_credit_score(self) -> float:
        """Calculate credit spread score (0-100, higher = tighter spreads)."""
        if self.spread_baa_aaa < 1.0:
            return 90.0
        elif self.spread_baa_aaa < 1.5:
            return 75.0
        elif self.spread_baa_aaa < 2.0:
            return 60.0
        elif self.spread_baa_aaa < 2.5:
            return 40.0
        elif self.spread_baa_aaa < 3.0:
            return 25.0
        else:
            return 10.0
