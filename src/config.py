"""Configuration management for Trading Agent."""
import os
from typing import List, Optional
import yaml
from pathlib import Path
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

    # IBKR Configuration
    ibkr_enabled: bool = Field(default=False)
    ibkr_host: str = Field(default="127.0.0.1")
    ibkr_port: int = Field(default=7497)
    ibkr_client_id: int = Field(default=1)
    ibkr_account: Optional[str] = Field(default=None)
    ibkr_paper_trading: bool = Field(default=True)
    ibkr_order_timeout: int = Field(default=30)
    ibkr_max_order_value: float = Field(default=10000.0)
    ibkr_retry_attempts: int = Field(default=3)
    ibkr_retry_delay_seconds: int = Field(default=1)
    ibkr_max_daily_orders: int = Field(default=100)
    ibkr_position_size_limit_pct: float = Field(default=0.10)
    ibkr_enable_market_data: bool = Field(default=True)
    ibkr_snapshot_data: bool = Field(default=False)
    ibkr_real_time_bars: bool = Field(default=False)
    ibkr_delayed_data: bool = Field(default=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def load_ibkr_config(config_path: Optional[str] = None) -> dict:
    """
    Load IBKR configuration from YAML file.

    Args:
        config_path: Path to config file. If None, uses default path.

    Returns:
        Dictionary with IBKR configuration
    """
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "config" / "ibkr_config.yaml")

    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        raise RuntimeError(f"Failed to load IBKR config: {e}")


settings = Settings()

# Load IBKR config into environment variables
ibkr_config = load_ibkr_config()
if ibkr_config and 'ibkr' in ibkr_config:
    ibkr_cfg = ibkr_config['ibkr']
    settings.ibkr_enabled = ibkr_cfg.get('enabled', settings.ibkr_enabled)
    settings.ibkr_host = ibkr_cfg.get('host', settings.ibkr_host)
    settings.ibkr_port = ibkr_cfg.get('port', settings.ibkr_port)
    settings.ibkr_client_id = ibkr_cfg.get('client_id', settings.ibkr_client_id)
    settings.ibkr_account = ibkr_cfg.get('account', settings.ibkr_account)
    settings.ibkr_paper_trading = ibkr_cfg.get('paper_trading', settings.ibkr_paper_trading)

if ibkr_config and 'order' in ibkr_config:
    order_cfg = ibkr_config['order']
    settings.ibkr_order_timeout = order_cfg.get('timeout_seconds', settings.ibkr_order_timeout)
    settings.ibkr_retry_attempts = order_cfg.get('retry_attempts', settings.ibkr_retry_attempts)
    settings.ibkr_retry_delay_seconds = order_cfg.get('retry_delay_seconds', settings.ibkr_retry_delay_seconds)

if ibkr_config and 'risk' in ibkr_config:
    risk_cfg = ibkr_config['risk']
    settings.ibkr_max_order_value = risk_cfg.get('max_order_value', settings.ibkr_max_order_value)
    settings.ibkr_max_daily_orders = risk_cfg.get('max_daily_orders', settings.ibkr_max_daily_orders)
    settings.ibkr_position_size_limit_pct = risk_cfg.get('position_size_limit_pct', settings.ibkr_position_size_limit_pct)

if ibkr_config and 'market_data' in ibkr_config:
    market_data_cfg = ibkr_config['market_data']
    settings.ibkr_enable_market_data = market_data_cfg.get('enable', settings.ibkr_enable_market_data)
    settings.ibkr_snapshot_data = market_data_cfg.get('snapshot_data', settings.ibkr_snapshot_data)
    settings.ibkr_real_time_bars = market_data_cfg.get('real_time_bars', settings.ibkr_real_time_bars)
    settings.ibkr_delayed_data = market_data_cfg.get('delayed_data', settings.ibkr_delayed_data)
