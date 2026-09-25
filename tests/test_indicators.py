"""Tests for technical indicators"""
import pytest
from src.core.indicators import TechnicalIndicators

def test_rsi_calculation():
    # Uptrend prices -> high RSI
    prices = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28]
    rsi = TechnicalIndicators.calculate_rsi(prices, 14)
    assert rsi is not None
    assert 0 <= rsi <= 100
    print(f"RSI: {rsi}")

def test_sma():
    prices = [1,2,3,4,5]
    sma = TechnicalIndicators.calculate_sma(prices, 3)
    assert sma == 4.0  # (3+4+5)/3

def test_ema():
    prices = [1,2,3,4,5,6,7,8,9,10]
    ema = TechnicalIndicators.calculate_ema(prices, 5)
    assert ema is not None
    assert ema > 0

def test_bollinger():
    prices = [20,21,22,23,24,25,26,27,28,29,30]*2
    upper, middle, lower = TechnicalIndicators.calculate_bollinger(prices, 20, 2)
    assert upper > middle > lower

def test_macd():
    prices = list(range(1, 50))
    macd, signal, hist = TechnicalIndicators.calculate_macd(prices)
    # With uptrend, MACD should be positive
    assert macd is not None

def test_crossover_detection():
    from src.models import IndicatorValues
    from datetime import datetime

    prev = IndicatorValues(
        symbol="BTCUSDT",
        price=60000,
        sma_fast=50000,
        sma_slow=51000,
        ema_fast=60000,
        ema_slow=61000,
        timestamp=datetime.utcnow()
    )
    curr = IndicatorValues(
        symbol="BTCUSDT",
        price=62000,
        sma_fast=52000,
        sma_slow=51000,
        ema_fast=62000,
        ema_slow=61000,
        timestamp=datetime.utcnow()
    )

    events = TechnicalIndicators.detect_crossovers(prev, curr)
    assert "GOLDEN_CROSS" in events
    assert "EMA_BULLISH_CROSS" in events
