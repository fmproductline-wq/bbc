"""
Unified OHLCV data fetcher.

- Crypto perps (BTC, ETH, SOL …) → Hyperliquid
- Futures / Commodities / Indices (CL, GC, ES …) → Yahoo Finance

All data returned as a DataFrame with columns:
  timestamp, open, high, low, close, volume
"""
from __future__ import annotations
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from loguru import logger

# ── Symbol routing ─────────────────────────────────────────────────────────────

# Tickers that come from Hyperliquid perps
_HL_TICKERS = {
    "BTC", "ETH", "SOL", "BNB", "ARB", "AVAX", "DOGE", "LINK",
    "UNI", "PEPE", "WIF", "SUI", "OP", "INJ", "TIA", "APT",
    "LTC", "BCH", "XRP", "ADA", "MATIC", "FIL",
}

# Yahoo Finance ticker for everything else
_YF_TICKERS: dict[str, str] = {
    # Crude / Energy futures
    "CL":  "CL=F",
    "NG":  "NG=F",
    "HO":  "HO=F",
    "RB":  "RB=F",
    # Metals
    "GC":  "GC=F",
    "SI":  "SI=F",
    "HG":  "HG=F",
    # Equity indices
    "ES":  "ES=F",
    "NQ":  "NQ=F",
    "YM":  "YM=F",
    "RTY": "RTY=F",
    # FX
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    # Major ETFs as proxies when futures aren't available
    "SPY": "SPY",
    "QQQ": "QQQ",
    "GLD": "GLD",
    "USO": "USO",
}

# Yahoo Finance interval strings
_YF_INTERVALS: dict[str, str] = {
    "1m":  "1m",
    "5m":  "5m",
    "15m": "15m",
    "1h":  "1h",
    "4h":  "1h",   # yfinance has no 4h; we resample after fetching
    "1d":  "1d",
}

# How many calendar days to fetch per timeframe
_YF_PERIODS: dict[str, int] = {
    "1m":  2,
    "5m":  5,
    "15m": 14,
    "1h":  60,
    "4h":  120,
    "1d":  500,
}


_hl_dynamic_cache: set[str] = set()
_hl_cache_ts: float = 0.0


def _refresh_hl_tickers():
    """Check Hyperliquid live mids to detect newly listed tickers (#4)."""
    global _hl_dynamic_cache, _hl_cache_ts
    if time.time() - _hl_cache_ts < 3600:
        return
    try:
        from trading.hyperliquid import get_all_mids
        mids = get_all_mids()
        _hl_dynamic_cache = set(mids.keys())
        _hl_cache_ts = time.time()
    except Exception:
        pass


def is_crypto(ticker: str) -> bool:
    t = ticker.upper()
    if t in _HL_TICKERS:
        return True
    _refresh_hl_tickers()
    return t in _hl_dynamic_cache


def fetch_candles(ticker: str, timeframe: str = "1h", limit: int = 120) -> pd.DataFrame:
    """
    Fetch OHLCV data for any supported ticker.
    Returns a DataFrame with columns: timestamp, open, high, low, close, volume.
    """
    t = ticker.upper()
    if is_crypto(t):
        return _fetch_hl(t, timeframe, limit)
    else:
        return _fetch_yf(t, timeframe, limit)


# ── Hyperliquid source ────────────────────────────────────────────────────────

def _fetch_hl(coin: str, timeframe: str, limit: int) -> pd.DataFrame:
    from analysis.market_analyzer import fetch_candles as _ma_fetch
    return _ma_fetch(coin, timeframe, limit)


# ── Yahoo Finance source ──────────────────────────────────────────────────────

def _fetch_yf(ticker: str, timeframe: str, limit: int) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed — run: pip install yfinance")
        return pd.DataFrame()

    yf_ticker = _YF_TICKERS.get(ticker, f"{ticker}=F")
    yf_interval = _YF_INTERVALS.get(timeframe, "1h")
    days = _YF_PERIODS.get(timeframe, 60)

    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    try:
        df = yf.download(
            yf_ticker,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=yf_interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception as e:
        logger.error(f"yfinance download failed for {yf_ticker}: {e}")
        return pd.DataFrame()

    if df.empty:
        logger.warning(f"No data returned from yfinance for {yf_ticker}")
        return pd.DataFrame()

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    df = df.rename(columns={"open": "open", "high": "high", "low": "low",
                             "close": "close", "volume": "volume"})

    # Resample 1h → 4h if needed
    if timeframe == "4h":
        df = df.resample("4h").agg({
            "open":   "first",
            "high":   "max",
            "low":    "min",
            "close":  "last",
            "volume": "sum",
        }).dropna()

    df = df.reset_index()
    ts_col = [c for c in df.columns if "date" in c.lower() or "datetime" in c.lower() or "index" in c.lower()]
    if ts_col:
        df = df.rename(columns={ts_col[0]: "timestamp"})
    else:
        df.insert(0, "timestamp", df.index)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)

    # Keep only the last `limit` rows
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].tail(limit).reset_index(drop=True)

    # Ensure numeric
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["open", "high", "low", "close"])
    logger.info(f"yfinance: fetched {len(df)} candles for {yf_ticker} ({timeframe})")
    return df
