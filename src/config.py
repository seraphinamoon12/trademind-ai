"""Configuration management for Trading Agent."""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "TradeMind AI"
    app_mode: str = "paper"  # paper, backtest, live
    timezone: str = "America/New_York"
    debug: bool = False
    
    # Database - Updated for port 5433
    database_url: str = Field(
        default="postgresql://trading:trading123@localhost:5433/trading_agent"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # Trading
    starting_capital: float = 100000.00
    max_position_pct: float = 0.10
    max_daily_loss_pct: float = 0.03
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    check_interval_minutes: int = 15
    trading_start: str = "09:30"
    trading_end: str = "16:00"
    
    # Safety - Circuit Breakers
    circuit_breaker_daily_loss_pct: float = 0.03  # -3% halt
    circuit_breaker_warning_drawdown_pct: float = 0.10  # -10% warning
    circuit_breaker_max_drawdown_pct: float = 0.15  # -15% halt
    circuit_breaker_consecutive_loss_limit: int = 5
    circuit_breaker_auto_liquidate: bool = False
    
    # Safety - Position Limits
    max_open_positions: int = 5
    max_portfolio_heat_pct: float = 0.10  # 10% capital at risk
    
    # Safety - Time Restrictions
    no_new_trades_after: str = "15:30"
    avoid_earnings_days_before: int = 1
    
    # Safety - Liquidity Filters
    min_avg_daily_volume: int = 1_000_000  # $1M
    min_price: float = 5.00
    max_spread_pct: float = 0.002  # 0.2%
    min_market_cap: int = 1_000_000_000  # $1B
    
    # Safety - Transaction Costs
    commission_per_share: float = 0.005
    min_commission: float = 1.00
    max_commission_pct: float = 0.01
    slippage_pct: float = 0.001
    spread_pct: float = 0.0005
    
    # Safety - Strategy Performance
    strategy_min_win_rate: float = 0.30
    strategy_min_profit_factor: float = 1.2
    strategy_min_trades_for_eval: int = 20
    strategy_auto_disable: bool = True
    
    # Safety - Sector Limits
    max_sector_allocation_pct: float = 0.30  # 30% per sector
    
    # Data
    data_provider: str = "yahoo"
    cache_duration_minutes: int = 5
    
    # Agents
    technical_weight: float = 0.40
    sentiment_weight: float = 0.30
    risk_weight: float = 0.30
    sentiment_enabled: bool = True  # Enable sentiment analysis by default
    
    # ZAI (for sentiment agent)
    zai_api_key: Optional[str] = Field(default=None)
    zai_model: str = "glm-4.7"
    zai_temperature: float = 0.3
    zai_timeout: int = 30
    
    # Strategies
    rsi_enabled: bool = True
    rsi_period: int = 14
    rsi_oversold: float = 30
    rsi_overbought: float = 70
    
    ma_enabled: bool = True
    ma_fast: int = 50
    ma_slow: int = 200
    
    # Watchlist
    watchlist: List[str] = Field(default=[
        "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", 
        "NVDA", "META", "AMD", "NFLX", "CRM"
    ])
    
    # OpenAI (for sentiment agent)
    openai_api_key: Optional[str] = Field(default=None)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
