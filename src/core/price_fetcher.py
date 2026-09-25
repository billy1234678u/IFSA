"""
Price Fetcher - Multi-provider market data aggregator
Supports: Binance (crypto), Yahoo Finance (forex, commodities, XAUUSD), TwelveData fallback
Senior DevOps: resilient, retry, circuit-breaker pattern
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import httpx
import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models import PriceData, OHLCV
from ..config import settings

logger = logging.getLogger(__name__)

class PriceFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.binance_base = "https://api.binance.com"
        self.coingecko_base = "https://api.coingecko.com/api/v3"

    async def close(self):
        await self.client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_binance_price(self, symbol: str) -> Optional[PriceData]:
        """Fetch spot price from Binance public API"""
        try:
            # Normalize symbol e.g. BTCUSDT
            url = f"{self.binance_base}/api/v3/ticker/24hr"
            params = {"symbol": symbol.upper()}
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            return PriceData(
                symbol=symbol.upper(),
                price=float(data['lastPrice']),
                open=float(data['openPrice']),
                high=float(data['highPrice']),
                low=float(data['lowPrice']),
                close=float(data['lastPrice']),
                volume=float(data['volume']),
                source="binance",
                timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.warning(f"Binance fetch failed for {symbol}: {e}")
            return None

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    async def fetch_binance_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> List[OHLCV]:
        """Fetch historical klines for indicator calculation"""
        try:
            url = f"{self.binance_base}/api/v3/klines"
            params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            raw = resp.json()
            result = []
            for k in raw:
                # [openTime, open, high, low, close, volume, closeTime...]
                result.append(OHLCV(
                    timestamp=datetime.fromtimestamp(k[0]/1000),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5])
                ))
            return result
        except Exception as e:
            logger.warning(f"Binance klines failed for {symbol}: {e}")
            return []

    def fetch_yahoo_price_sync(self, yahoo_symbol: str, original_symbol: str) -> Optional[PriceData]:
        """Sync Yahoo fetch (yfinance is sync)"""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            # Fast info
            info = ticker.fast_info
            last_price = info.last_price if hasattr(info, 'last_price') else None

            if last_price is None:
                # Fallback to history
                hist = ticker.history(period="1d", interval="1m")
                if hist.empty:
                    hist = ticker.history(period="5d", interval="1d")
                if not hist.empty:
                    last_price = float(hist['Close'].iloc[-1])
                else:
                    return None

            # Get OHLC from recent history
            hist = ticker.history(period="5d", interval="1d")
            if not hist.empty:
                last_row = hist.iloc[-1]
                return PriceData(
                    symbol=original_symbol,
                    price=float(last_price),
                    open=float(last_row['Open']),
                    high=float(last_row['High']),
                    low=float(last_row['Low']),
                    close=float(last_row['Close']),
                    volume=float(last_row['Volume']) if 'Volume' in last_row else 0,
                    source=f"yahoo:{yahoo_symbol}",
                    timestamp=datetime.utcnow()
                )
            else:
                return PriceData(
                    symbol=original_symbol,
                    price=float(last_price),
                    source=f"yahoo:{yahoo_symbol}",
                    timestamp=datetime.utcnow()
                )
        except Exception as e:
            logger.warning(f"Yahoo fetch failed for {yahoo_symbol} ({original_symbol}): {e}")
            return None

    def fetch_yahoo_history_sync(self, yahoo_symbol: str, period: str = "3mo", interval: str = "1d") -> List[OHLCV]:
        """Fetch Yahoo history for indicators"""
        try:
            ticker = yf.Ticker(yahoo_symbol)
            hist = ticker.history(period=period, interval=interval)
            result = []
            for idx, row in hist.iterrows():
                # idx is Timestamp
                result.append(OHLCV(
                    timestamp=idx.to_pydatetime() if hasattr(idx, 'to_pydatetime') else datetime.utcnow(),
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume']) if 'Volume' in row else 0
                ))
            return result
        except Exception as e:
            logger.warning(f"Yahoo history failed for {yahoo_symbol}: {e}")
            return []

    async def fetch_price(self, asset_config: Dict) -> Optional[PriceData]:
        """Unified fetch based on asset config"""
        symbol = asset_config.get('symbol')
        provider = asset_config.get('provider', 'binance').lower()

        if provider == 'binance':
            binance_symbol = asset_config.get('binance_symbol') or symbol
            return await self.fetch_binance_price(binance_symbol)

        elif provider in ('yahoo', 'yfinance'):
            yahoo_symbol = asset_config.get('yahoo_symbol') or f"{symbol}=X"
            # Run sync in thread pool to not block
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.fetch_yahoo_price_sync, yahoo_symbol, symbol)

        else:
            # Fallback: try binance first, then yahoo
            data = await self.fetch_binance_price(symbol)
            if data:
                return data
            yahoo_symbol = asset_config.get('yahoo_symbol') or f"{symbol}=X"
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.fetch_yahoo_price_sync, yahoo_symbol, symbol)

    async def fetch_history(self, asset_config: Dict, interval: str = "1d", limit: int = 200) -> List[OHLCV]:
        """Fetch history for indicator calc"""
        symbol = asset_config.get('symbol')
        provider = asset_config.get('provider', 'binance').lower()

        if provider == 'binance':
            binance_symbol = asset_config.get('binance_symbol') or symbol
            # Map interval: 1d -> 1d, 1h -> 1h
            binance_interval = interval if interval in ["1m","5m","15m","1h","4h","1d"] else "1d"
            return await self.fetch_binance_klines(binance_symbol, binance_interval, limit)
        else:
            yahoo_symbol = asset_config.get('yahoo_symbol') or f"{symbol}=X"
            # Map interval
            yahoo_interval = "1d" if interval == "1d" else "1h" if interval == "1h" else "1d"
            period = "1y" if limit > 200 else "6mo"
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.fetch_yahoo_history_sync, yahoo_symbol, period, yahoo_interval)

    async def fetch_all(self, assets: List[Dict]) -> Dict[str, PriceData]:
        """Fetch all assets concurrently"""
        tasks = [self.fetch_price(asset) for asset in assets if asset.get('enabled', True)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        prices = {}
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Fetch exception: {res}")
                continue
            if res:
                prices[res.symbol] = res

        logger.info(f"Fetched {len(prices)}/{len(assets)} assets")
        return prices

# Singleton for convenience
_fetcher_instance = None

def get_price_fetcher() -> PriceFetcher:
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = PriceFetcher()
    return _fetcher_instance
