"""
Symbol routing — maps app tickers to their data source.
No external browser calls; all charting is done in-app.
"""
from __future__ import annotations

# Tickers routed to Yahoo Finance (futures, commodities, indices, FX)
YF_LABEL: dict[str, str] = {
    "CL":     "Crude Oil WTI",
    "GC":     "Gold",
    "SI":     "Silver",
    "NG":     "Natural Gas",
    "HO":     "Heating Oil",
    "RB":     "RBOB Gasoline",
    "ES":     "S&P 500",
    "NQ":     "NASDAQ 100",
    "YM":     "Dow Jones",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
}


def display_label(ticker: str) -> str:
    """Human-readable label for a ticker."""
    return YF_LABEL.get(ticker.upper(), ticker.upper())
