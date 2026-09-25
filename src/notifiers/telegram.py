"""
Telegram Notifier - Sends alerts via Telegram Bot API
Setup:
1. Talk to @BotFather on Telegram, create bot, get token
2. Get your chat ID via @userinfobot or by calling getUpdates
"""
import logging
import httpx
from ..models import Alert
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    def __init__(self, bot_token: str, chat_id: str, parse_mode: str = "Markdown"):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.parse_mode = parse_mode
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: Alert) -> bool:
        try:
            # Use simple formatting - Markdown can be tricky, fallback to plain if needed
            text = alert.to_telegram()

            # Telegram has 4096 char limit
            if len(text) > 4000:
                text = text[:4000] + "..."

            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": True
            }

            resp = await self.client.post(f"{self.base_url}/sendMessage", json=payload)
            resp.raise_for_status()
            data = resp.json()

            if not data.get('ok'):
                logger.error(f"Telegram API error: {data}")
                # Try without parse_mode as fallback
                payload.pop('parse_mode', None)
                resp = await self.client.post(f"{self.base_url}/sendMessage", json=payload)
                resp.raise_for_status()
                data = resp.json()
                if not data.get('ok'):
                    return False

            logger.info(f"Telegram alert sent: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            # Try plain text fallback
            try:
                plain_text = f"🔔 {alert.title}\nSymbol: {alert.symbol}\nPrice: ${alert.price:,.4f}\n{alert.message}\nTime: {alert.timestamp}"
                payload = {
                    "chat_id": self.chat_id,
                    "text": plain_text
                }
                resp = await self.client.post(f"{self.base_url}/sendMessage", json=payload)
                resp.raise_for_status()
                return True
            except Exception as e2:
                logger.error(f"Telegram fallback also failed: {e2}")
                return False

    async def close(self):
        await self.client.aclose()
