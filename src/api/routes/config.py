"""Configuration API routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import yaml
from io import StringIO

from src.config import settings

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdate(BaseModel):
    """Config update request."""
    key: str
    value: Any


class ConfigResponse(BaseModel):
    """Config response."""
    key: str
    value: Any


@router.get("")
async def get_all_config():
    """Get all configuration settings."""
    return {
        "app_name": settings.app_name,
        "app_mode": settings.app_mode,
        "timezone": settings.timezone,
        "debug": settings.debug,
        
        "starting_capital": settings.starting_capital,
        "max_position_pct": settings.max_position_pct,
        "max_daily_loss_pct": settings.max_daily_loss_pct,
        "stop_loss_pct": settings.stop_loss_pct,
        "take_profit_pct": settings.take_profit_pct,
        "check_interval_minutes": settings.check_interval_minutes,
        "trading_start": settings.trading_start,
        "trading_end": settings.trading_end,
        
        "circuit_breaker_daily_loss_pct": settings.circuit_breaker_daily_loss_pct,
        "circuit_breaker_warning_drawdown_pct": settings.circuit_breaker_warning_drawdown_pct,
        "circuit_breaker_max_drawdown_pct": settings.circuit_breaker_max_drawdown_pct,
        "circuit_breaker_consecutive_loss_limit": settings.circuit_breaker_consecutive_loss_limit,
        "circuit_breaker_auto_liquidate": settings.circuit_breaker_auto_liquidate,
        
        "max_open_positions": settings.max_open_positions,
        "max_portfolio_heat_pct": settings.max_portfolio_heat_pct,
        "no_new_trades_after": settings.no_new_trades_after,
        
        "technical_weight": settings.technical_weight,
        "sentiment_weight": settings.sentiment_weight,
        "risk_weight": settings.risk_weight,
        "sentiment_enabled": settings.sentiment_enabled,
        
        "sentiment_source": settings.sentiment_source,
        "sentiment_cache_ttl": settings.sentiment_cache_ttl,
        "sentiment_confidence_threshold": settings.sentiment_confidence_threshold,
        "zai_api_key": "***" if settings.zai_api_key else None,
        "zai_model": settings.zai_model,
        
        "rsi_enabled": settings.rsi_enabled,
        "rsi_period": settings.rsi_period,
        "rsi_oversold": settings.rsi_oversold,
        "rsi_overbought": settings.rsi_overbought,
        "ma_enabled": settings.ma_enabled,
        "ma_fast": settings.ma_fast,
        "ma_slow": settings.ma_slow,
        
        "watchlist": settings.watchlist,
    }


@router.get("/{key}")
async def get_config_key(key: str):
    """Get a specific configuration value."""
    if hasattr(settings, key):
        value = getattr(settings, key)
        if "api_key" in key.lower() or "password" in key.lower():
            value = "***" if value else None
        return {"key": key, "value": value}
    raise HTTPException(status_code=404, detail=f"Config key not found: {key}")


@router.post("")
async def update_config(update: ConfigUpdate):
    """Update a configuration value.
    
    Note: This updates in-memory settings only.
    For permanent changes, modify the .env file.
    """
    if not hasattr(settings, update.key):
        raise HTTPException(status_code=404, detail=f"Config key not found: {update.key}")
    
    if update.key == "sentiment_source":
        if update.value not in ["llm", "technical", "auto"]:
            raise HTTPException(
                status_code=400, 
                detail="sentiment_source must be 'llm', 'technical', or 'auto'"
            )
    
    setattr(settings, update.key, update.value)
    
    return {
        "key": update.key,
        "value": update.value,
        "message": f"Updated {update.key}. Note: Changes are in-memory only."
    }


@router.post("/reset")
async def reset_config():
    """Reset configuration to defaults.
    
    Note: This reloads from environment/.env file.
    """
    global settings
    from src.config import Settings
    settings = Settings()
    return {"message": "Configuration reset to defaults"}


@router.get("/validate")
async def validate_config():
    """Validate current configuration."""
    errors = []
    
    if settings.sentiment_source not in ["llm", "technical", "auto"]:
        errors.append(f"Invalid sentiment_source: {settings.sentiment_source}")
    
    if settings.sentiment_source == "llm" and not settings.zai_api_key:
        errors.append("sentiment_source is 'llm' but ZAI_API_KEY is not set")
    
    if settings.trading_start >= settings.trading_end:
        errors.append("trading_start must be before trading_end")
    
    if settings.max_position_pct <= 0 or settings.max_position_pct > 1:
        errors.append("max_position_pct must be between 0 and 1")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    return {"valid": True, "message": "Configuration is valid"}


@router.get("/export")
async def export_config():
    """Export configuration as YAML."""
    config_dict = {
        "app_name": settings.app_name,
        "app_mode": settings.app_mode,
        "sentiment_source": settings.sentiment_source,
        "sentiment_enabled": settings.sentiment_enabled,
    }
    yaml_content = yaml.dump(config_dict, default_flow_style=False)
    return {"yaml": yaml_content}


@router.post("/import")
async def import_config(yaml_content: str):
    """Import configuration from YAML.
    
    Note: This updates in-memory settings only.
    """
    try:
        config_dict = yaml.safe_load(yaml_content)
        for key, value in config_dict.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        return {"message": "Configuration imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse YAML: {str(e)}")
