"""
Technical Indicators Engine
Implements RSI, SMA, EMA, MACD, Bollinger Bands from scratch + pandas
No external TA-lib dependency for portability (Netlify friendly)
"""
import math
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from ..models import OHLCV, IndicatorValues

class TechnicalIndicators:

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI - Relative Strength Index"""
        if len(prices) < period + 1:
            return None

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # First average gain/loss
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        if avg_loss == 0:
            return 100.0

        # Wilder's smoothing
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return float(np.mean(prices[-period:]))

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        # EMA calculation
        k = 2 / (period + 1)
        ema = np.mean(prices[:period])  # SMA for first
        for price in prices[period:]:
            ema = price * k + ema * (1 - k)
        return float(ema)

    @staticmethod
    def calculate_ema_series(prices: List[float], period: int) -> List[Optional[float]]:
        """Return full EMA series"""
        if len(prices) < period:
            return [None] * len(prices)
        k = 2 / (period + 1)
        ema_series = []
        sma = np.mean(prices[:period])
        ema = sma
        for i, price in enumerate(prices):
            if i < period - 1:
                ema_series.append(None)
            elif i == period - 1:
                ema_series.append(ema)
            else:
                ema = price * k + ema * (1 - k)
                ema_series.append(ema)
        return ema_series

    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """MACD, Signal, Histogram"""
        if len(prices) < slow + signal:
            return None, None, None

        ema_fast_series = TechnicalIndicators.calculate_ema_series(prices, fast)
        ema_slow_series = TechnicalIndicators.calculate_ema_series(prices, slow)

        # Align series, filter None
        macd_line = []
        for f, s in zip(ema_fast_series, ema_slow_series):
            if f is None or s is None:
                macd_line.append(None)
            else:
                macd_line.append(f - s)

        # Filter Nones for signal
        macd_valid = [x for x in macd_line if x is not None]
        if len(macd_valid) < signal:
            return None, None, None

        signal_series = TechnicalIndicators.calculate_ema_series(macd_valid, signal)
        # Last values
        macd_last = macd_valid[-1] if macd_valid else None
        signal_last = signal_series[-1] if signal_series and signal_series[-1] is not None else None

        hist = None
        if macd_last is not None and signal_last is not None:
            hist = macd_last - signal_last

        return macd_last, signal_last, hist

    @staticmethod
    def calculate_bollinger(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Upper, Middle, Lower"""
        if len(prices) < period:
            return None, None, None
        recent = prices[-period:]
        middle = float(np.mean(recent))
        std = float(np.std(recent))
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        return upper, middle, lower

    @staticmethod
    def calculate_percent_change(current: float, previous: float) -> float:
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100

    @classmethod
    def analyze(cls, ohlcv: List[OHLCV], current_price: float, config: dict = None) -> IndicatorValues:
        """Full analysis from OHLCV list"""
        from datetime import datetime

        if config is None:
            config = {}

        closes = [c.close for c in ohlcv]

        # If not enough history, use current price to extend
        if not closes:
            closes = [current_price]
        else:
            # Ensure current price is considered
            if closes[-1] != current_price:
                closes.append(current_price)

        symbol = config.get('symbol', 'UNKNOWN')

        # RSI
        rsi_period = config.get('rsi', {}).get('period', 14) if isinstance(config.get('rsi'), dict) else config.get('rsi_period', 14)
        rsi = cls.calculate_rsi(closes, rsi_period)

        # MA
        sma_fast_period = config.get('moving_averages', {}).get('sma_fast', 50) if isinstance(config.get('moving_averages'), dict) else 50
        sma_slow_period = config.get('moving_averages', {}).get('sma_slow', 200) if isinstance(config.get('moving_averages'), dict) else 200
        ema_fast_period = config.get('moving_averages', {}).get('ema_fast', 9) if isinstance(config.get('moving_averages'), dict) else 9
        ema_slow_period = config.get('moving_averages', {}).get('ema_slow', 21) if isinstance(config.get('moving_averages'), dict) else 21

        sma_fast = cls.calculate_sma(closes, sma_fast_period)
        sma_slow = cls.calculate_sma(closes, sma_slow_period)
        ema_fast = cls.calculate_ema(closes, ema_fast_period)
        ema_slow = cls.calculate_ema(closes, ema_slow_period)

        # MACD
        macd_cfg = config.get('macd', {})
        macd_fast = macd_cfg.get('fast', 12) if isinstance(macd_cfg, dict) else 12
        macd_slow = macd_cfg.get('slow', 26) if isinstance(macd_cfg, dict) else 26
        macd_signal = macd_cfg.get('signal', 9) if isinstance(macd_cfg, dict) else 9
        macd, macd_sig, macd_hist = cls.calculate_macd(closes, macd_fast, macd_slow, macd_signal)

        # Bollinger
        bb_cfg = config.get('bollinger', {})
        bb_period = bb_cfg.get('period', 20) if isinstance(bb_cfg, dict) else 20
        bb_std = bb_cfg.get('std_dev', 2) if isinstance(bb_cfg, dict) else 2
        bb_upper, bb_middle, bb_lower = cls.calculate_bollinger(closes, bb_period, bb_std)

        # Percent changes
        pct_1h = None
        pct_24h = None
        if len(closes) >= 2:
            pct_24h = cls.calculate_percent_change(closes[-1], closes[-2])
        if len(closes) >= 24:
            # Approx if hourly data, else last 24 periods
            pct_1h = cls.calculate_percent_change(closes[-1], closes[-2])

        return IndicatorValues(
            symbol=symbol,
            price=current_price,
            rsi=rsi,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            macd=macd,
            macd_signal=macd_sig,
            macd_histogram=macd_hist,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            percent_change_1h=pct_1h,
            percent_change_24h=pct_24h,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def detect_crossovers(prev: Optional[IndicatorValues], curr: IndicatorValues) -> List[str]:
        """Detect crossover events between previous and current indicator values"""
        events = []
        if not prev:
            return events

        # SMA Crossover - Golden Cross / Death Cross
        if prev.sma_fast and prev.sma_slow and curr.sma_fast and curr.sma_slow:
            prev_diff = prev.sma_fast - prev.sma_slow
            curr_diff = curr.sma_fast - curr.sma_slow
            if prev_diff < 0 and curr_diff > 0:
                events.append("GOLDEN_CROSS")
            elif prev_diff > 0 and curr_diff < 0:
                events.append("DEATH_CROSS")

        # EMA Crossover
        if prev.ema_fast and prev.ema_slow and curr.ema_fast and curr.ema_slow:
            prev_diff = prev.ema_fast - prev.ema_slow
            curr_diff = curr.ema_fast - curr.ema_slow
            if prev_diff < 0 and curr_diff > 0:
                events.append("EMA_BULLISH_CROSS")
            elif prev_diff > 0 and curr_diff < 0:
                events.append("EMA_BEARISH_CROSS")

        # MACD Crossover
        if prev.macd and prev.macd_signal and curr.macd and curr.macd_signal:
            prev_diff = prev.macd - prev.macd_signal
            curr_diff = curr.macd - curr.macd_signal
            if prev_diff < 0 and curr_diff > 0:
                events.append("MACD_BULLISH_CROSS")
            elif prev_diff > 0 and curr_diff < 0:
                events.append("MACD_BEARISH_CROSS")

        # RSI threshold crosses
        if prev.rsi and curr.rsi:
            # Overbought 70
            if prev.rsi < 70 and curr.rsi >= 70:
                events.append("RSI_OVERBOUGHT_CROSS")
            if prev.rsi >= 70 and curr.rsi < 70:
                events.append("RSI_EXIT_OVERBOUGHT")
            # Oversold 30
            if prev.rsi > 30 and curr.rsi <= 30:
                events.append("RSI_OVERSOLD_CROSS")
            if prev.rsi <= 30 and curr.rsi > 30:
                events.append("RSI_EXIT_OVERSOLD")

        return events
