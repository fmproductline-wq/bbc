"""
Market analysis engine.

Pulls OHLCV data from Hyperliquid and runs technical analysis:
- Trend detection (EMA cross, ADX)
- Xtreme Trend signal simulation
- HOTT/LOTT (High & Low Optimized Trend Tracker) replication
- Volume analysis, volatility (ATR), momentum (RSI, MACD)
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional
import requests
import pandas as pd
import numpy as np
from loguru import logger


# ── Hyperliquid candle fetch ──────────────────────────────────────────────────

HL_BASE = "https://api.hyperliquid.xyz/info"

INTERVAL_MAP = {
    "1m": "1m", "5m": "5m", "15m": "15m",
    "1h": "1h", "4h": "4h", "1d": "1d",
}


def fetch_candles(coin: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    """
    Fetch OHLCV candles from Hyperliquid.
    Returns DataFrame with columns: [open, high, low, close, volume, timestamp]
    """
    import time
    end_ms = int(time.time() * 1000)
    interval_ms = {
        "1m": 60_000, "5m": 300_000, "15m": 900_000,
        "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
    }.get(interval, 3_600_000)
    start_ms = end_ms - limit * interval_ms

    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": INTERVAL_MAP.get(interval, interval),
            "startTime": start_ms,
            "endTime": end_ms,
        },
    }
    resp = requests.post(HL_BASE, json=payload, timeout=15)
    resp.raise_for_status()
    candles = resp.json()

    if not candles:
        return pd.DataFrame()

    df = pd.DataFrame(candles)
    df = df.rename(columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ── Indicators ────────────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    m = ema(series, fast) - ema(series, slow)
    s = ema(m, signal)
    return m, s, m - s


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index — trend strength (>25 = trending)."""
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = (high.diff()).clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    tr = atr(df, 1)
    plus_di = 100 * ema(plus_dm, period) / ema(tr, period)
    minus_di = 100 * ema(minus_dm, period) / ema(tr, period)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, float("nan"))) * 100
    return ema(dx, period)


def hott_lott(df: pd.DataFrame, period: int = 21, multiplier: float = 3.0) -> pd.DataFrame:
    """
    Replication of HOTT/LOTT (High & Low Optimized Trend Tracker).

    Uses a Keltner-channel-style tracker on highs and lows separately.
    Returns 'hott' (upper tracker), 'lott' (lower tracker), and 'trend' (+1 / -1).
    """
    atr_val = atr(df, period)
    hott = df["high"].rolling(period).max() - multiplier * atr_val
    lott = df["low"].rolling(period).min() + multiplier * atr_val

    trend = pd.Series(0, index=df.index)
    for i in range(1, len(df)):
        if df["close"].iloc[i] > hott.iloc[i]:
            trend.iloc[i] = 1
        elif df["close"].iloc[i] < lott.iloc[i]:
            trend.iloc[i] = -1
        else:
            trend.iloc[i] = trend.iloc[i - 1]

    df = df.copy()
    df["hott"] = hott
    df["lott"] = lott
    df["hott_lott_trend"] = trend
    return df


def xtreme_trend(df: pd.DataFrame, fast: int = 8, slow: int = 21, atr_period: int = 14) -> pd.DataFrame:
    """
    Xtreme Trend approximation: dual-EMA cross with ATR filter.
    Signal: +1 (bullish) when fast EMA > slow EMA and price > slow EMA + ATR
            -1 (bearish) when fast EMA < slow EMA and price < slow EMA - ATR
    """
    df = df.copy()
    df["ema_fast"] = ema(df["close"], fast)
    df["ema_slow"] = ema(df["close"], slow)
    df["atr"] = atr(df, atr_period)
    df["xt_signal"] = 0
    bull = (df["ema_fast"] > df["ema_slow"]) & (df["close"] > df["ema_slow"] + df["atr"] * 0.3)
    bear = (df["ema_fast"] < df["ema_slow"]) & (df["close"] < df["ema_slow"] - df["atr"] * 0.3)
    df.loc[bull, "xt_signal"] = 1
    df.loc[bear, "xt_signal"] = -1
    return df


# ── Full analysis report ──────────────────────────────────────────────────────

@dataclass
class MarketReport:
    coin: str
    interval: str
    price: float
    trend: str          # "BULLISH" | "BEARISH" | "NEUTRAL"
    strength: str       # "STRONG" | "MODERATE" | "WEAK"
    rsi_val: float
    macd_cross: str     # "BULLISH" | "BEARISH" | "NONE"
    atr_val: float
    volatility_pct: float
    xt_signal: int      # +1 / -1 / 0
    hott_lott_signal: int
    suggested_action: str
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    summary: str

    def to_telegram(self) -> str:
        emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "⚪"}.get(self.trend, "⚪")
        return (
            f"{emoji} *{self.coin} {self.interval} Analysis*\n"
            f"Price: `${self.price:,.4f}`\n"
            f"Trend: {self.trend} ({self.strength})\n"
            f"RSI: `{self.rsi_val:.1f}` | ATR: `{self.atr_val:.4f}`\n"
            f"MACD Cross: {self.macd_cross}\n"
            f"Xtreme Trend: `{'▲ BUY' if self.xt_signal==1 else '▼ SELL' if self.xt_signal==-1 else '— FLAT'}`\n"
            f"HOTT/LOTT: `{'▲ UP' if self.hott_lott_signal==1 else '▼ DOWN' if self.hott_lott_signal==-1 else '— FLAT'}`\n"
            f"Volatility: `{self.volatility_pct:.2f}%`\n\n"
            f"🎯 *Suggested:* {self.suggested_action}\n"
            f"🛑 Stop Loss: `${self.stop_loss:,.4f}`\n"
            f"✅ TP1: `${self.take_profit_1:,.4f}` | TP2: `${self.take_profit_2:,.4f}`\n\n"
            f"_{self.summary}_"
        )


def analyze(coin: str, interval: str = "1h", limit: int = 200) -> MarketReport:
    """Run full market analysis for a coin on Hyperliquid."""
    df = fetch_candles(coin, interval, limit)
    if df.empty or len(df) < 50:
        raise ValueError(f"Not enough candle data for {coin}")

    df = hott_lott(df)
    df = xtreme_trend(df)
    df["rsi"] = rsi(df["close"])
    macd_line, signal_line, hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["adx"] = adx(df)
    df["atr"] = atr(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = float(last["close"])

    # Trend determination
    rsi_val = float(last["rsi"])
    adx_val = float(last["adx"]) if not math.isnan(float(last["adx"])) else 0
    ema_fast = float(last["ema_fast"])
    ema_slow = float(last["ema_slow"])

    if ema_fast > ema_slow and last["hott_lott_trend"] == 1:
        trend = "BULLISH"
    elif ema_fast < ema_slow and last["hott_lott_trend"] == -1:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    strength = "STRONG" if adx_val > 25 else "MODERATE" if adx_val > 18 else "WEAK"

    # MACD cross
    if float(prev["macd"]) < float(prev["macd_signal"]) and float(last["macd"]) > float(last["macd_signal"]):
        macd_cross = "BULLISH"
    elif float(prev["macd"]) > float(prev["macd_signal"]) and float(last["macd"]) < float(last["macd_signal"]):
        macd_cross = "BEARISH"
    else:
        macd_cross = "NONE"

    atr_val = float(last["atr"])
    volatility_pct = (atr_val / price) * 100

    xt_signal = int(last["xt_signal"])
    hl_signal = int(last["hott_lott_trend"])

    # Action suggestion
    buy_signals = sum([
        trend == "BULLISH",
        xt_signal == 1,
        hl_signal == 1,
        macd_cross == "BULLISH",
        rsi_val < 70 and rsi_val > 40,
    ])
    sell_signals = sum([
        trend == "BEARISH",
        xt_signal == -1,
        hl_signal == -1,
        macd_cross == "BEARISH",
        rsi_val > 30 and rsi_val < 60,
    ])

    if buy_signals >= 4:
        action = "STRONG LONG"
        stop_loss = price - 2 * atr_val
        tp1 = price + 2 * atr_val
        tp2 = price + 4 * atr_val
    elif buy_signals >= 3:
        action = "LONG"
        stop_loss = price - 1.5 * atr_val
        tp1 = price + 2 * atr_val
        tp2 = price + 3.5 * atr_val
    elif sell_signals >= 4:
        action = "STRONG SHORT"
        stop_loss = price + 2 * atr_val
        tp1 = price - 2 * atr_val
        tp2 = price - 4 * atr_val
    elif sell_signals >= 3:
        action = "SHORT"
        stop_loss = price + 1.5 * atr_val
        tp1 = price - 2 * atr_val
        tp2 = price - 3.5 * atr_val
    else:
        action = "WAIT / NO TRADE"
        stop_loss = price - atr_val
        tp1 = price + atr_val
        tp2 = price + 2 * atr_val

    rsi_txt = "overbought" if rsi_val > 70 else "oversold" if rsi_val < 30 else "neutral"
    summary = (
        f"RSI {rsi_val:.0f} ({rsi_txt}), ADX {adx_val:.0f} ({strength.lower()} trend). "
        f"Xtreme Trend {'bullish' if xt_signal==1 else 'bearish' if xt_signal==-1 else 'flat'}, "
        f"HOTT/LOTT {'up' if hl_signal==1 else 'down' if hl_signal==-1 else 'flat'}."
    )

    return MarketReport(
        coin=coin, interval=interval, price=price,
        trend=trend, strength=strength,
        rsi_val=rsi_val, macd_cross=macd_cross,
        atr_val=atr_val, volatility_pct=volatility_pct,
        xt_signal=xt_signal, hott_lott_signal=hl_signal,
        suggested_action=action,
        stop_loss=round(stop_loss, 6),
        take_profit_1=round(tp1, 6),
        take_profit_2=round(tp2, 6),
        summary=summary,
    )
