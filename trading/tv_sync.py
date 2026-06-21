"""
TradingView symbol sync — opens TradingView in the browser at the selected
symbol, preserving whatever chart layout/indicators the user has saved there.

Symbol mapping covers Hyperliquid perps (crypto) and common futures like
Crude Oil (CL), Gold (GC), etc.
"""
from __future__ import annotations
import webbrowser
from loguru import logger

# ── Symbol map: app ticker → TradingView symbol ──────────────────────────────

TV_SYMBOLS: dict[str, str] = {
    # Crypto perps (Hyperliquid / Binance feed)
    "BTC":   "BINANCE:BTCUSDT",
    "ETH":   "BINANCE:ETHUSDT",
    "SOL":   "BINANCE:SOLUSDT",
    "BNB":   "BINANCE:BNBUSDT",
    "ARB":   "BINANCE:ARBUSDT",
    "AVAX":  "BINANCE:AVAXUSDT",
    "DOGE":  "BINANCE:DOGEUSDT",
    "LINK":  "BINANCE:LINKUSDT",
    "UNI":   "BINANCE:UNIUSDT",
    "PEPE":  "BINANCE:PEPEUSDT",
    "WIF":   "BINANCE:WIFUSDT",
    "SUI":   "BINANCE:SUIUSDT",

    # Commodities / Futures
    "CL":    "NYMEX:CL1!",    # Crude Oil WTI
    "GC":    "COMEX:GC1!",    # Gold
    "SI":    "COMEX:SI1!",    # Silver
    "NG":    "NYMEX:NG1!",    # Natural Gas
    "HO":    "NYMEX:HO1!",    # Heating Oil
    "RB":    "NYMEX:RB1!",    # RBOB Gasoline

    # Equity index futures
    "ES":    "CME:ES1!",      # S&P 500
    "NQ":    "CME:NQ1!",      # NASDAQ
    "YM":    "CBOT:YM1!",     # Dow Jones

    # FX
    "EURUSD": "FX:EURUSD",
    "GBPUSD": "FX:GBPUSD",
    "USDJPY": "FX:USDJPY",
}

# Timeframe map: internal → TradingView interval string
TV_INTERVALS: dict[str, str] = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1d": "D",
    "1w": "W",
}

# Your saved TradingView chart layout ID (optional).
# If set, TradingView opens your saved layout so indicators are pre-loaded.
# Find it in TradingView URL: /chart/<LAYOUT_ID>/
# Set via Settings → TradingView → Chart Layout ID, or TV_LAYOUT_ID env var.
import os as _os
TV_LAYOUT_ID: str = _os.getenv("TV_LAYOUT_ID", "")


def tv_symbol(ticker: str) -> str:
    """Return the TradingView symbol string for a ticker."""
    return TV_SYMBOLS.get(ticker.upper(), ticker.upper())


def open_chart(ticker: str, timeframe: str = "1h", layout_id: str = "") -> str:
    """
    Open TradingView in the default browser at the given ticker + timeframe.

    If layout_id is provided (or TV_LAYOUT_ID is set), opens that saved
    chart layout so all your saved indicators load automatically.

    Returns the URL that was opened.
    """
    symbol   = tv_symbol(ticker)
    interval = TV_INTERVALS.get(timeframe, "60")
    lid      = layout_id or TV_LAYOUT_ID

    if lid:
        url = f"https://www.tradingview.com/chart/{lid}/?symbol={symbol}&interval={interval}"
    else:
        url = f"https://www.tradingview.com/chart/?symbol={symbol}&interval={interval}"

    try:
        webbrowser.open(url)
        logger.info(f"TradingView sync: {ticker} → {symbol} ({timeframe})")
    except Exception as e:
        logger.warning(f"Failed to open TradingView: {e}")

    return url
