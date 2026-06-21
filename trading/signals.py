"""
TradingView signal parser for:
  - Xtreme Trend
  - High and Low Optimized Trend Tracker (HOTT / LOTT)

TradingView Pine Script alert message format (JSON):
{
  "secret": "your_webhook_secret",
  "indicator": "xtreme_trend" | "hott_lott",
  "action": "buy" | "sell" | "close",
  "symbol": "BTCUSDT",
  "timeframe": "1h" | "1m",
  "price": 65000.00,
  "token_in": "0x...",   // optional token address
  "token_out": "0x...",  // optional token address
  "chain": "polygon"     // optional
}

Paste one of these example alert messages into TradingView's alert dialog
pointing to your webhook URL: https://yourdomain.com/webhook/tradingview
"""
from pydantic import BaseModel
from typing import Optional
import time


class TVSignal(BaseModel):
    secret: str
    indicator: str          # "xtreme_trend" | "hott_lott"
    action: str             # "buy" | "sell" | "close"
    symbol: str
    timeframe: str = "1h"
    price: float = 0.0
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    chain: Optional[str] = None
    amount_usd: Optional[float] = None  # override trade size in USD

    def is_buy(self) -> bool:
        return self.action.lower() == "buy"

    def is_sell(self) -> bool:
        return self.action.lower() in ("sell", "close")

    def to_log(self) -> dict:
        return {
            "ts": time.time(),
            "indicator": self.indicator,
            "action": self.action,
            "symbol": self.symbol,
            "tf": self.timeframe,
            "price": self.price,
        }
