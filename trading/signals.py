"""
TradingView signal parser.

Indicator names are OBFUSCATED in all external-facing surfaces
(webhook docs, alert templates, logs, UI) so users cannot determine
which proprietary indicators power the strategy.

External alias  →  Internal engine
─────────────────────────────────
sig_a           →  Strategy engine A  (trend momentum)
sig_b           →  Strategy engine B  (high/low tracker)
sig_c           →  Combined multi-engine signal

Only use sig_a / sig_b / sig_c in TradingView alert JSON payloads.
"""
from pydantic import BaseModel
from typing import Optional
import time

# ── Indicator alias map (kept server-side only) ───────────────────────────────
# Maps public-facing alias to internal engine tag used in analysis
_ALIAS_MAP: dict[str, str] = {
    "sig_a":  "engine_a",
    "sig_b":  "engine_b",
    "sig_c":  "engine_c",
    # Accept legacy internal names if sent directly (server-to-server only)
    "engine_a": "engine_a",
    "engine_b": "engine_b",
    "engine_c": "engine_c",
}

# Public aliases shown to users
PUBLIC_ALIAS_A = "sig_a"
PUBLIC_ALIAS_B = "sig_b"
PUBLIC_ALIAS_C = "sig_c"


def resolve_indicator(raw: str) -> str:
    """Map public alias to internal engine tag. Unknown values pass through."""
    return _ALIAS_MAP.get(raw.lower().strip(), raw.lower().strip())


class TVSignal(BaseModel):
    secret: str
    indicator: str          # PUBLIC: use "sig_a" | "sig_b" | "sig_c"
    action: str             # "buy" | "sell" | "close"
    symbol: str
    timeframe: str = "1h"
    price: float = 0.0
    token_in: Optional[str] = None
    token_out: Optional[str] = None
    chain: Optional[str] = None
    amount_usd: Optional[float] = None

    def resolved_indicator(self) -> str:
        """Internal engine tag — never logged externally."""
        return resolve_indicator(self.indicator)

    def is_buy(self) -> bool:
        return self.action.lower() == "buy"

    def is_sell(self) -> bool:
        return self.action.lower() in ("sell", "close")

    def to_log(self) -> dict:
        """Log entry — indicator alias only, engine name hidden."""
        return {
            "ts":        time.time(),
            "indicator": self.indicator,   # public alias, e.g. "sig_a"
            "action":    self.action,
            "symbol":    self.symbol,
            "tf":        self.timeframe,
            "price":     self.price,
        }
