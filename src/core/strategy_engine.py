"""
Strategy Engine - Evaluates technical indicators and generates alerts
Event-driven core logic
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime

from ..models import Alert, AlertType, IndicatorValues, PriceData
from .indicators import TechnicalIndicators
from ..config import yaml_config, settings

logger = logging.getLogger(__name__)

class StrategyEngine:
    def __init__(self, indicator_config: Dict = None):
        self.config = indicator_config or yaml_config.get('indicators', {})
        self.tech = TechnicalIndicators()

    def evaluate(self, price: PriceData, indicator: IndicatorValues, prev_indicator: Optional[IndicatorValues], asset_config: Dict) -> List[Alert]:
        """Evaluate all strategies and return alerts"""
        alerts = []
        symbol = price.symbol

        # 1. RSI Alerts
        alerts.extend(self._check_rsi(indicator, prev_indicator, asset_config))

        # 2. MA Crossover Alerts
        alerts.extend(self._check_ma_crossovers(indicator, prev_indicator, asset_config))

        # 3. MACD Alerts
        alerts.extend(self._check_macd(indicator, prev_indicator, asset_config))

        # 4. Price Threshold Alerts
        alerts.extend(self._check_price_thresholds(price, asset_config))

        # 5. Percent Change Alerts
        alerts.extend(self._check_percent_change(price, prev_indicator, indicator, asset_config))

        # 6. Bollinger Bands
        alerts.extend(self._check_bollinger(indicator, asset_config))

        # 7. Generic crossover detection from indicator engine
        crossovers = TechnicalIndicators.detect_crossovers(prev_indicator, indicator)
        for cross in crossovers:
            # Already covered above but ensure no duplicates; this is for logging
            logger.debug(f"{symbol} crossover detected: {cross}")

        return alerts

    def _check_rsi(self, curr: IndicatorValues, prev: Optional[IndicatorValues], asset_config: Dict) -> List[Alert]:
        alerts = []
        if not curr.rsi:
            return alerts

        rsi_cfg = self.config.get('rsi', {})
        if not rsi_cfg.get('enabled', True):
            return alerts

        overbought = rsi_cfg.get('overbought', 70)
        oversold = rsi_cfg.get('oversold', 30)
        symbol = curr.symbol

        # Current level alerts
        if curr.rsi >= overbought:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.RSI_OVERBOUGHT,
                title=f"{symbol} RSI Overbought",
                message=f"RSI is at {curr.rsi:.2f} (overbought >{overbought}). Potential reversal or pullback incoming.",
                price=curr.price,
                severity="warning",
                cooldown_key=f"{symbol}_RSI_OVERBOUGHT",
                indicator_data={"rsi": curr.rsi, "threshold": overbought}
            ))
        elif curr.rsi <= oversold:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.RSI_OVERSOLD,
                title=f"{symbol} RSI Oversold",
                message=f"RSI is at {curr.rsi:.2f} (oversold <{oversold}). Potential bounce opportunity.",
                price=curr.price,
                severity="warning",
                cooldown_key=f"{symbol}_RSI_OVERSOLD",
                indicator_data={"rsi": curr.rsi, "threshold": oversold}
            ))

        # Cross detection for more precise timing
        if prev and prev.rsi:
            if prev.rsi < overbought and curr.rsi >= overbought:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.RSI_CROSS_OVERBOUGHT,
                    title=f"{symbol} RSI Crossed Overbought",
                    message=f"RSI crossed above {overbought}: {prev.rsi:.2f} → {curr.rsi:.2f}",
                    price=curr.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_RSI_CROSS_OB",
                    indicator_data={"rsi_prev": prev.rsi, "rsi_curr": curr.rsi}
                ))
            if prev.rsi > oversold and curr.rsi <= oversold:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.RSI_CROSS_OVERSOLD,
                    title=f"{symbol} RSI Crossed Oversold",
                    message=f"RSI crossed below {oversold}: {prev.rsi:.2f} → {curr.rsi:.2f}",
                    price=curr.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_RSI_CROSS_OS",
                    indicator_data={"rsi_prev": prev.rsi, "rsi_curr": curr.rsi}
                ))

        return alerts

    def _check_ma_crossovers(self, curr: IndicatorValues, prev: Optional[IndicatorValues], asset_config: Dict) -> List[Alert]:
        alerts = []
        ma_cfg = self.config.get('moving_averages', {})
        if not ma_cfg.get('enabled', True) or not prev:
            return alerts

        symbol = curr.symbol

        # SMA Golden/Death Cross
        if prev.sma_fast and prev.sma_slow and curr.sma_fast and curr.sma_slow:
            prev_diff = prev.sma_fast - prev.sma_slow
            curr_diff = curr.sma_fast - curr.sma_slow

            if prev_diff < 0 and curr_diff > 0:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.MA_GOLDEN_CROSS,
                    title=f"{symbol} Golden Cross ✨",
                    message=f"SMA{ma_cfg.get('sma_fast',50)} crossed ABOVE SMA{ma_cfg.get('sma_slow',200)}\nFast: {curr.sma_fast:.2f}, Slow: {curr.sma_slow:.2f}\nStrong bullish signal!",
                    price=curr.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_GOLDEN_CROSS",
                    indicator_data={"sma_fast": curr.sma_fast, "sma_slow": curr.sma_slow}
                ))
            elif prev_diff > 0 and curr_diff < 0:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.MA_DEATH_CROSS,
                    title=f"{symbol} Death Cross 💀",
                    message=f"SMA{ma_cfg.get('sma_fast',50)} crossed BELOW SMA{ma_cfg.get('sma_slow',200)}\nFast: {curr.sma_fast:.2f}, Slow: {curr.sma_slow:.2f}\nBearish warning!",
                    price=curr.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_DEATH_CROSS",
                    indicator_data={"sma_fast": curr.sma_fast, "sma_slow": curr.sma_slow}
                ))

        # EMA Cross
        if prev.ema_fast and prev.ema_slow and curr.ema_fast and curr.ema_slow:
            prev_diff = prev.ema_fast - prev.ema_slow
            curr_diff = curr.ema_fast - curr.ema_slow
            if prev_diff < 0 and curr_diff > 0:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.EMA_BULLISH_CROSS,
                    title=f"{symbol} EMA Bullish Cross",
                    message=f"EMA{ma_cfg.get('ema_fast',9)} crossed above EMA{ma_cfg.get('ema_slow',21)}\nFast: {curr.ema_fast:.2f}, Slow: {curr.ema_slow:.2f}",
                    price=curr.price,
                    severity="info",
                    cooldown_key=f"{symbol}_EMA_BULL",
                    indicator_data={"ema_fast": curr.ema_fast, "ema_slow": curr.ema_slow}
                ))
            elif prev_diff > 0 and curr_diff < 0:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.EMA_BEARISH_CROSS,
                    title=f"{symbol} EMA Bearish Cross",
                    message=f"EMA{ma_cfg.get('ema_fast',9)} crossed below EMA{ma_cfg.get('ema_slow',21)}\nFast: {curr.ema_fast:.2f}, Slow: {curr.ema_slow:.2f}",
                    price=curr.price,
                    severity="info",
                    cooldown_key=f"{symbol}_EMA_BEAR",
                    indicator_data={"ema_fast": curr.ema_fast, "ema_slow": curr.ema_slow}
                ))

        return alerts

    def _check_macd(self, curr: IndicatorValues, prev: Optional[IndicatorValues], asset_config: Dict) -> List[Alert]:
        alerts = []
        macd_cfg = self.config.get('macd', {})
        if not macd_cfg.get('enabled', True) or not prev:
            return alerts

        if not (prev.macd and prev.macd_signal and curr.macd and curr.macd_signal):
            return alerts

        symbol = curr.symbol
        prev_diff = prev.macd - prev.macd_signal
        curr_diff = curr.macd - curr.macd_signal

        if prev_diff < 0 and curr_diff > 0:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.MACD_BULLISH_CROSS,
                title=f"{symbol} MACD Bullish Crossover",
                message=f"MACD crossed above Signal line\nMACD: {curr.macd:.4f}, Signal: {curr.macd_signal:.4f}, Hist: {curr.macd_histogram:.4f}",
                price=curr.price,
                severity="info",
                cooldown_key=f"{symbol}_MACD_BULL",
                indicator_data={"macd": curr.macd, "signal": curr.macd_signal}
            ))
        elif prev_diff > 0 and curr_diff < 0:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.MACD_BEARISH_CROSS,
                title=f"{symbol} MACD Bearish Crossover",
                message=f"MACD crossed below Signal line\nMACD: {curr.macd:.4f}, Signal: {curr.macd_signal:.4f}, Hist: {curr.macd_histogram:.4f}",
                price=curr.price,
                severity="info",
                cooldown_key=f"{symbol}_MACD_BEAR",
                indicator_data={"macd": curr.macd, "signal": curr.macd_signal}
            ))

        return alerts

    def _check_price_thresholds(self, price: PriceData, asset_config: Dict) -> List[Alert]:
        alerts = []
        thresholds = asset_config.get('alerts', {}).get('price_thresholds', [])
        symbol = price.symbol

        for th in thresholds:
            level = th.get('level')
            direction = th.get('direction', 'above')
            msg = th.get('message', f"Price {direction} {level}")

            if level is None:
                continue

            if direction == 'above' and price.price >= level:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.PRICE_ABOVE_THRESHOLD,
                    title=f"{symbol} Above ${level}",
                    message=msg,
                    price=price.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_PRICE_ABOVE_{level}",
                    indicator_data={"threshold": level, "direction": direction}
                ))
            elif direction == 'below' and price.price <= level:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.PRICE_BELOW_THRESHOLD,
                    title=f"{symbol} Below ${level}",
                    message=msg,
                    price=price.price,
                    severity="critical",
                    cooldown_key=f"{symbol}_PRICE_BELOW_{level}",
                    indicator_data={"threshold": level, "direction": direction}
                ))

        return alerts

    def _check_percent_change(self, price: PriceData, prev_ind: Optional[IndicatorValues], curr_ind: IndicatorValues, asset_config: Dict) -> List[Alert]:
        alerts = []
        if not prev_ind:
            return alerts

        # Get threshold from asset config or global
        asset_pct = asset_config.get('alerts', {}).get('percent_change')
        global_pct = self.config.get('price_action', {}).get('percent_change_threshold', settings.price_change_alert_percent)
        threshold = asset_pct if asset_pct is not None else global_pct

        symbol = price.symbol
        prev_price = prev_ind.price
        if prev_price == 0:
            return alerts

        pct_change = ((price.price - prev_price) / prev_price) * 100

        if abs(pct_change) >= threshold:
            if pct_change > 0:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.PRICE_PERCENT_UP,
                    title=f"{symbol} Up {pct_change:.2f}% 🚀",
                    message=f"Price pumped {pct_change:.2f}%: ${prev_price:.2f} → ${price.price:.2f}",
                    price=price.price,
                    severity="warning" if pct_change < threshold*2 else "critical",
                    cooldown_key=f"{symbol}_PCT_UP",
                    indicator_data={"pct_change": pct_change, "prev_price": prev_price}
                ))
            else:
                alerts.append(Alert(
                    symbol=symbol,
                    type=AlertType.PRICE_PERCENT_DOWN,
                    title=f"{symbol} Down {pct_change:.2f}% 🔻",
                    message=f"Price dumped {pct_change:.2f}%: ${prev_price:.2f} → ${price.price:.2f}",
                    price=price.price,
                    severity="warning" if abs(pct_change) < threshold*2 else "critical",
                    cooldown_key=f"{symbol}_PCT_DOWN",
                    indicator_data={"pct_change": pct_change, "prev_price": prev_price}
                ))

        return alerts

    def _check_bollinger(self, curr: IndicatorValues, asset_config: Dict) -> List[Alert]:
        alerts = []
        bb_cfg = self.config.get('bollinger', {})
        if not bb_cfg.get('enabled', False):
            return alerts

        if not (curr.bb_upper and curr.bb_lower):
            return alerts

        symbol = curr.symbol
        if curr.price >= curr.bb_upper:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.BOLLINGER_BREAKOUT_UP,
                title=f"{symbol} Bollinger Upper Breakout",
                message=f"Price {curr.price:.2f} broke above upper BB {curr.bb_upper:.2f}",
                price=curr.price,
                severity="info",
                cooldown_key=f"{symbol}_BB_UP",
                indicator_data={"bb_upper": curr.bb_upper, "price": curr.price}
            ))
        elif curr.price <= curr.bb_lower:
            alerts.append(Alert(
                symbol=symbol,
                type=AlertType.BOLLINGER_BREAKOUT_DOWN,
                title=f"{symbol} Bollinger Lower Breakout",
                message=f"Price {curr.price:.2f} broke below lower BB {curr.bb_lower:.2f}",
                price=curr.price,
                severity="info",
                cooldown_key=f"{symbol}_BB_DOWN",
                indicator_data={"bb_lower": curr.bb_lower, "price": curr.price}
            ))

        return alerts
