"""
Configuration loader - supports YAML + ENV overrides
Senior DevOps pattern: 12-factor config
"""
import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # General
    environment: str = Field(default="production", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    poll_interval_seconds: int = Field(default=60, alias="POLL_INTERVAL_SECONDS")

    # Market Data
    twelvedata_api_key: Optional[str] = Field(default=None, alias="TWELVEDATA_API_KEY")
    alphavantage_api_key: Optional[str] = Field(default=None, alias="ALPHAVANTAGE_API_KEY")
    binance_api_key: Optional[str] = Field(default=None, alias="BINANCE_API_KEY")
    binance_api_secret: Optional[str] = Field(default=None, alias="BINANCE_API_SECRET")

    # Indicators
    rsi_period: int = Field(default=14, alias="RSI_PERIOD")
    rsi_overbought: int = Field(default=70, alias="RSI_OVERBOUGHT")
    rsi_oversold: int = Field(default=30, alias="RSI_OVERSOLD")
    sma_fast_period: int = Field(default=50, alias="SMA_FAST_PERIOD")
    sma_slow_period: int = Field(default=200, alias="SMA_SLOW_PERIOD")
    ema_fast_period: int = Field(default=9, alias="EMA_FAST_PERIOD")
    ema_slow_period: int = Field(default=21, alias="EMA_SLOW_PERIOD")
    price_change_alert_percent: float = Field(default=2.0, alias="PRICE_CHANGE_ALERT_PERCENT")

    alert_cooldown_seconds: int = Field(default=900, alias="ALERT_COOLDOWN_SECONDS")

    # Telegram
    telegram_enabled: bool = Field(default=False, alias="TELEGRAM_ENABLED")
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Discord
    discord_enabled: bool = Field(default=False, alias="DISCORD_ENABLED")
    discord_webhook_url: Optional[str] = Field(default=None, alias="DISCORD_WEBHOOK_URL")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(default="change-me", alias="API_SECRET_KEY")

    # Persistence
    state_file_path: str = Field(default="./data/state.json", alias="STATE_FILE_PATH")
    alert_history_file: str = Field(default="./data/alert_history.json", alias="ALERT_HISTORY_FILE")

    # Monitored assets override
    monitored_assets: Optional[str] = Field(default=None, alias="MONITORED_ASSETS")

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()

def load_yaml_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Load YAML config with fallback"""
    config_path = Path(path)
    if not config_path.exists():
        # Try alternative locations
        for alt in ["./config.yaml", "../config.yaml", "/app/config.yaml"]:
            if Path(alt).exists():
                config_path = Path(alt)
                break
    if not config_path.exists():
        return {}

    with open(config_path, 'r') as f:
        return yaml.safe_load(f) or {}

# Global YAML config
yaml_config = load_yaml_config()

def get_assets_config() -> List[Dict[str, Any]]:
    """Merge YAML assets with ENV override"""
    assets = yaml_config.get('assets', [])

    # ENV override: MONITORED_ASSETS=XAUUSD:FOREX, BTCUSDT:CRYPTO:BINANCE
    if settings.monitored_assets:
        env_assets = []
        for item in settings.monitored_assets.split(','):
            item = item.strip()
            if not item:
                continue
            parts = item.split(':')
            symbol = parts[0].upper()
            asset_type = parts[1] if len(parts) > 1 else "CRYPTO"
            provider = parts[2].lower() if len(parts) > 2 else "binance" if asset_type == "CRYPTO" else "yahoo"

            # Map to yahoo symbols for forex/commodities
            yahoo_map = {
                "XAUUSD": "GC=F",
                "XAGUSD": "SI=F",
                "EURUSD": "EURUSD=X",
                "GBPUSD": "GBPUSD=X",
                "USDJPY": "JPY=X",
            }

            env_assets.append({
                "symbol": symbol,
                "name": symbol,
                "type": asset_type,
                "provider": provider,
                "yahoo_symbol": yahoo_map.get(symbol, f"{symbol}=X") if asset_type != "CRYPTO" else None,
                "binance_symbol": symbol if asset_type == "CRYPTO" else None,
                "enabled": True,
                "alerts": {"percent_change": settings.price_change_alert_percent}
            })
        if env_assets:
            return env_assets

    return assets

def get_indicator_config() -> Dict[str, Any]:
    """Get indicator config merged with ENV"""
    indicators = yaml_config.get('indicators', {})

    # ENV overrides
    if 'rsi' in indicators:
        indicators['rsi']['period'] = settings.rsi_period
        indicators['rsi']['overbought'] = settings.rsi_overbought
        indicators['rsi']['oversold'] = settings.rsi_oversold

    if 'moving_averages' in indicators:
        indicators['moving_averages']['sma_fast'] = settings.sma_fast_period
        indicators['moving_averages']['sma_slow'] = settings.sma_slow_period
        indicators['moving_averages']['ema_fast'] = settings.ema_fast_period
        indicators['moving_averages']['ema_slow'] = settings.ema_slow_period

    if 'price_action' in indicators:
        indicators['price_action']['percent_change_threshold'] = settings.price_change_alert_percent

    return indicators

def is_telegram_configured() -> bool:
    return bool(settings.telegram_enabled and settings.telegram_bot_token and settings.telegram_chat_id)

def is_discord_configured() -> bool:
    return bool(settings.discord_enabled and settings.discord_webhook_url)
