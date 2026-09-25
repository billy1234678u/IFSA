"""
Base Notifier abstract class
"""
import logging
from abc import ABC, abstractmethod
from ..models import Alert

logger = logging.getLogger(__name__)

class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        pass

class ConsoleNotifier(BaseNotifier):
    """Always-on console notifier for logs & debugging"""

    async def send(self, alert: Alert) -> bool:
        try:
            # Colorful console output
            severity_icon = {
                "info": "ℹ️",
                "warning": "⚠️",
                "critical": "🚨"
            }.get(alert.severity, "🔔")

            print(f"\n{severity_icon} [{alert.timestamp.strftime('%H:%M:%S')}] {alert.title}")
            print(f"   Symbol: {alert.symbol} | Price: ${alert.price:,.4f} | Type: {alert.type}")
            print(f"   Message: {alert.message}")
            if alert.indicator_data:
                print(f"   Data: {alert.indicator_data}")
            print("-" * 60)

            logger.info(f"Console alert: {alert.title} - {alert.symbol} @ {alert.price}")
            return True
        except Exception as e:
            logger.error(f"Console notifier error: {e}")
            return False
