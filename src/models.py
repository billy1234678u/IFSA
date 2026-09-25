"""
Data models for market monitoring bot
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AssetType(str, Enum):
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    COMMODITY = "COMMODITY"
    STOCK = "STOCK"

class AlertType(str, Enum):
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    RSI_CROSS_OVERBOUGHT = "RSI_CROSS_OVERBOUGHT"
    RSI_CROSS_OVERSOLD = "RSI_CROSS_OVERSOLD"
    MA_GOLDEN_CROSS = "MA_GOLDEN_CROSS"
    MA_DEATH_CROSS = "MA_DEATH_CROSS"
    EMA_BULLISH_CROSS = "EMA_BULLISH_CROSS"
    EMA_BEARISH_CROSS = "EMA_BEARISH_CROSS"
    MACD_BULLISH_CROSS = "MACD_BULLISH_CROSS"
    MACD_BEARISH_CROSS = "MACD_BEARISH_CROSS"
    PRICE_ABOVE_THRESHOLD = "PRICE_ABOVE_THRESHOLD"
    PRICE_BELOW_THRESHOLD = "PRICE_BELOW_THRESHOLD"
    PRICE_PERCENT_UP = "PRICE_PERCENT_UP"
    PRICE_PERCENT_DOWN = "PRICE_PERCENT_DOWN"
    BOLLINGER_BREAKOUT_UP = "BOLLINGER_BREAKOUT_UP"
    BOLLINGER_BREAKOUT_DOWN = "BOLLINGER_BREAKOUT_DOWN"
    BREAKOUT_HIGH = "BREAKOUT_HIGH"
    BREAKOUT_LOW = "BREAKOUT_LOW"

class PriceData(BaseModel):
    symbol: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    source: str = "unknown"

class OHLCV(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class IndicatorValues(BaseModel):
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    price: float
    rsi: Optional[float] = None
    sma_fast: Optional[float] = None
    sma_slow: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    percent_change_1h: Optional[float] = None
    percent_change_24h: Optional[float] = None

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: __import__('uuid').uuid4().hex[:8])
    symbol: str
    type: AlertType
    title: str
    message: str
    price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    indicator_data: Optional[Dict[str, Any]] = None
    severity: str = "info"  # info, warning, critical
    cooldown_key: Optional[str] = None

    def to_telegram(self) -> str:
        """Format for Telegram Markdown"""
        emoji_map = {
            AlertType.RSI_OVERBOUGHT: "🔴",
            AlertType.RSI_OVERSOLD: "🟢",
            AlertType.MA_GOLDEN_CROSS: "✨",
            AlertType.MA_DEATH_CROSS: "💀",
            AlertType.PRICE_ABOVE_THRESHOLD: "📈",
            AlertType.PRICE_BELOW_THRESHOLD: "📉",
            AlertType.PRICE_PERCENT_UP: "🚀",
            AlertType.PRICE_PERCENT_DOWN: "🔻",
        }
        emoji = emoji_map.get(self.type, "🔔")
        # Escape for MarkdownV2 if needed - simplified for now
        return (
            f"{emoji} *{self.title}*\n"
            f"Symbol: `{self.symbol}`\n"
            f"Price: `${self.price:,.2f}`\n"
            f"Type: `{self.type.value}`\n"
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"{self.message}"
        )

    def to_discord(self) -> Dict[str, Any]:
        """Format for Discord webhook embed"""
        color_map = {
            "info": 0x3498db,
            "warning": 0xf1c40f,
            "critical": 0xe74c3c,
        }
        return {
            "embeds": [{
                "title": self.title,
                "description": self.message,
                "color": color_map.get(self.severity, 0x3498db),
                "fields": [
                    {"name": "Symbol", "value": self.symbol, "inline": True},
                    {"name": "Price", "value": f"${self.price:,.4f}", "inline": True},
                    {"name": "Type", "value": self.type.value, "inline": True},
                ],
                "timestamp": self.timestamp.isoformat(),
                "footer": {"text": "IFSA Market Monitor"}
            }]
        }

class AssetConfig(BaseModel):
    symbol: str
    name: str = ""
    type: AssetType = AssetType.CRYPTO
    provider: str = "binance"
    yahoo_symbol: Optional[str] = None
    binance_symbol: Optional[str] = None
    enabled: bool = True
    alerts: Dict[str, Any] = Field(default_factory=dict)

class BotState(BaseModel):
    last_prices: Dict[str, float] = Field(default_factory=dict)
    last_indicators: Dict[str, IndicatorValues] = Field(default_factory=dict)
    last_alerts: Dict[str, datetime] = Field(default_factory=dict)  # cooldown_key -> timestamp
    last_update: datetime = Field(default_factory=datetime.utcnow)
    total_alerts_sent: int = 0
    uptime_start: datetime = Field(default_factory=datetime.utcnow)
