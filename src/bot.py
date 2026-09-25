"""
Main Bot Engine - Event-driven market monitoring loop
"""
import asyncio
import logging
import signal
from datetime import datetime
from typing import Dict, List

from .config import settings, get_assets_config, get_indicator_config, yaml_config
from .core.price_fetcher import PriceFetcher
from .core.indicators import TechnicalIndicators
from .core.strategy_engine import StrategyEngine
from .core.state_store import StateStore
from .core.alert_manager import AlertManager
from .models import PriceData

# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class MarketMonitorBot:
    def __init__(self):
        self.assets = get_assets_config()
        self.indicator_config = get_indicator_config()
        self.price_fetcher = PriceFetcher()
        self.indicators = TechnicalIndicators()
        self.strategy = StrategyEngine(self.indicator_config)
        self.state_store = StateStore()
        self.alert_manager = AlertManager(self.state_store)
        self.running = False
        self.poll_interval = yaml_config.get('app', {}).get('poll_interval_seconds', settings.poll_interval_seconds)

        logger.info(f"Bot initialized with {len(self.assets)} assets, poll interval {self.poll_interval}s")

    async def process_asset(self, asset_config: Dict, price: PriceData):
        """Process single asset: calculate indicators, evaluate strategies, dispatch alerts"""
        symbol = price.symbol
        try:
            # Fetch historical data for indicators
            history = await self.price_fetcher.fetch_history(asset_config, interval="1d", limit=250)
            if not history:
                logger.warning(f"No history for {symbol}, using price only")
                history = []

            # Get previous indicator for crossover detection
            prev_indicator = self.state_store.get_last_indicator(symbol)

            # Calculate current indicators
            # Merge asset symbol into indicator config for context
            ind_cfg = {**self.indicator_config, "symbol": symbol}
            current_indicator = self.indicators.analyze(history, price.price, ind_cfg)

            # Evaluate strategies
            alerts = self.strategy.evaluate(price, current_indicator, prev_indicator, asset_config)

            # Update state
            self.state_store.update_indicator(symbol, current_indicator)

            # Dispatch alerts
            if alerts:
                logger.info(f"{symbol}: {len(alerts)} alert(s) generated")
                sent = await self.alert_manager.dispatch(alerts)
                logger.info(f"{symbol}: {sent}/{len(alerts)} alerts sent")
            else:
                logger.debug(f"{symbol}: No alerts, price=${price.price:.2f} RSI={current_indicator.rsi:.2f if current_indicator.rsi else 'N/A'}")

            return {
                "symbol": symbol,
                "price": price.price,
                "indicator": current_indicator.model_dump(),
                "alerts": len(alerts)
            }

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}", exc_info=True)
            return {"symbol": symbol, "error": str(e)}

    async def run_once(self) -> Dict:
        """Single monitoring cycle - used by scheduler, Netlify functions, API"""
        start_time = datetime.utcnow()
        logger.info(f"Starting monitoring cycle at {start_time}")

        try:
            # Fetch all prices concurrently
            prices = await self.price_fetcher.fetch_all(self.assets)

            if not prices:
                logger.warning("No prices fetched in this cycle")
                return {"status": "warning", "message": "No prices fetched", "timestamp": start_time.isoformat()}

            # Process each asset
            results = []
            for symbol, price_data in prices.items():
                asset_cfg = next((a for a in self.assets if a['symbol'] == symbol), None)
                if not asset_cfg:
                    # Find by binance symbol or yahoo symbol fallback
                    asset_cfg = next((a for a in self.assets if a.get('binance_symbol') == symbol or a.get('symbol') == symbol), {"symbol": symbol})

                result = await self.process_asset(asset_cfg, price_data)
                results.append(result)

            elapsed = (datetime.utcnow() - start_time).total_seconds()

            summary = {
                "status": "success",
                "timestamp": start_time.isoformat(),
                "duration_seconds": elapsed,
                "assets_processed": len(results),
                "assets": results,
                "stats": self.state_store.get_stats()
            }

            logger.info(f"Cycle completed in {elapsed:.2f}s, processed {len(results)} assets")
            return summary

        except Exception as e:
            logger.error(f"Run once failed: {e}", exc_info=True)
            return {"status": "error", "message": str(e), "timestamp": start_time.isoformat()}

    async def run_forever(self):
        """Continuous loop for VPS / Docker deployment"""
        self.running = True
        logger.info("🚀 Market Monitor Bot starting continuous loop...")

        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        cycle_count = 0
        while self.running:
            try:
                cycle_count += 1
                logger.info(f"=== Cycle #{cycle_count} ===")
                await self.run_once()

                # Sleep with interruption check
                for _ in range(self.poll_interval):
                    if not self.running:
                        break
                    await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info("Loop cancelled")
                break
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                await asyncio.sleep(10)  # Backoff on error

        await self.price_fetcher.close()
        logger.info("Bot stopped")

    async def shutdown(self):
        logger.info("Shutdown signal received...")
        self.running = False

# CLI entry point
async def main():
    bot = MarketMonitorBot()
    await bot.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
