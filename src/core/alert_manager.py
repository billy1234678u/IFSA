"""
Alert Manager - Dispatches alerts via multiple channels with retry & cooldown
"""
import logging
import asyncio
from typing import List
from datetime import datetime

from ..models import Alert
from ..notifiers.telegram import TelegramNotifier
from ..notifiers.discord import DiscordNotifier
from ..notifiers.base import BaseNotifier
from .state_store import StateStore
from ..config import settings, yaml_config

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store
        self.notifiers: List[BaseNotifier] = []
        self._init_notifiers()

    def _init_notifiers(self):
        # Console always
        from ..notifiers.base import ConsoleNotifier
        self.notifiers.append(ConsoleNotifier())

        # Telegram
        if settings.telegram_enabled and settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                self.notifiers.append(TelegramNotifier(
                    bot_token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id
                ))
                logger.info("Telegram notifier enabled")
            except Exception as e:
                logger.error(f"Failed to init Telegram notifier: {e}")
        else:
            # Check yaml
            tg_cfg = yaml_config.get('alerts', {}).get('channels', {}).get('telegram', {})
            if tg_cfg.get('enabled'):
                logger.warning("Telegram enabled in yaml but missing ENV credentials")

        # Discord
        if settings.discord_enabled and settings.discord_webhook_url:
            try:
                self.notifiers.append(DiscordNotifier(webhook_url=settings.discord_webhook_url))
                logger.info("Discord notifier enabled")
            except Exception as e:
                logger.error(f"Failed to init Discord notifier: {e}")

    async def dispatch(self, alerts: List[Alert]) -> int:
        """Dispatch alerts respecting cooldown, returns count sent"""
        if not alerts:
            return 0

        sent_count = 0
        cooldown_seconds = yaml_config.get('alerts', {}).get('cooldown_seconds', settings.alert_cooldown_seconds)

        for alert in alerts:
            cooldown_key = alert.cooldown_key or f"{alert.symbol}_{alert.type.value}"

            # Check cooldown
            if not self.state_store.should_alert(cooldown_key, cooldown_seconds):
                logger.info(f"Cooldown active for {cooldown_key}, skipping alert")
                continue

            # Send via all notifiers
            success = await self._send_to_all(alert)

            if success:
                self.state_store.record_alert(cooldown_key)
                self.state_store.append_history(alert.model_dump(mode='json'))
                sent_count += 1
                logger.info(f"Alert sent: {alert.title} for {alert.symbol}")
            else:
                logger.error(f"Failed to send alert: {alert.title}")

        return sent_count

    async def _send_to_all(self, alert: Alert) -> bool:
        """Send alert to all configured notifiers, at least one must succeed"""
        tasks = [notifier.send(alert) for notifier in self.notifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = 0
        for i, res in enumerate(results):
            notifier_name = self.notifiers[i].__class__.__name__
            if isinstance(res, Exception):
                logger.error(f"{notifier_name} failed: {res}")
            elif res:
                success_count += 1
            else:
                logger.warning(f"{notifier_name} returned False")

        # Consider success if at least one notifier succeeded (console always succeeds)
        return success_count > 0

    async def send_test_alert(self, symbol: str = "BTCUSDT"):
        """Send a test alert to verify notifiers"""
        test_alert = Alert(
            symbol=symbol,
            type="PRICE_ABOVE_THRESHOLD",
            title=f"Test Alert for {symbol}",
            message="This is a test alert from IFSA Market Monitor Bot. If you receive this, your notifications are configured correctly! ✅",
            price=0.0,
            severity="info",
            cooldown_key=f"test_{symbol}"
        )
        # Bypass cooldown for test
        return await self._send_to_all(test_alert)
