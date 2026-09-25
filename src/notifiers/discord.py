"""
Discord Notifier - Sends alerts via Discord Webhook
Setup:
1. In Discord channel: Edit Channel -> Integrations -> Webhooks -> New Webhook
2. Copy webhook URL
"""
import logging
import httpx
from ..models import Alert
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class DiscordNotifier(BaseNotifier):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: Alert) -> bool:
        try:
            payload = alert.to_discord()

            # Add content for critical alerts to ping
            if alert.severity == "critical":
                payload["content"] = f"🚨 Critical alert for {alert.symbol}!"

            resp = await self.client.post(self.webhook_url, json=payload)
            # Discord returns 204 on success
            if resp.status_code in (200, 204):
                logger.info(f"Discord alert sent: {alert.title}")
                return True
            else:
                logger.error(f"Discord webhook failed: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False

    async def close(self):
        await self.client.aclose()
