"""
Polymarket Live Bet Research Bot.

Runs as a background agent that continuously:
  1. Fetches all active, high-volume Polymarket markets
  2. Scores each market using multi-factor probability research:
       - Market implied probability vs base rate
       - Volume & liquidity health check
       - Time-to-resolution weighting
       - Bayesian update from related market signals
       - Kelly criterion for optimal sizing
       - Expected value edge calculation
  3. Ranks top opportunities and alerts via Telegram
  4. Provides deep-dive research on any specific market

The bot ONLY scouts opportunities — all actual bets still require
Telegram approval from the owner before any money moves.
"""
from __future__ import annotations

import math
import time
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger
import requests

from analysis.probability import (
    kelly_fraction, implied_probability, expected_value, edge,
    bayesian_update, BetOpportunity,
)

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

# ── Thresholds ────────────────────────────────────────────────────────────────
MIN_VOLUME_USD    = 5_000     # ignore thin markets
MIN_EDGE_PCT      = 5.0       # only flag if edge > 5%
MAX_MARKETS_SCAN  = 100       # how many markets to fetch per scan
SCAN_INTERVAL_SEC = 300       # scan every 5 minutes
MIN_DAYS_TO_CLOSE = 1         # skip markets closing today (too risky)
MAX_DAYS_TO_CLOSE = 60        # skip markets too far out (uncertainty)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class LiveMarket:
    id: str
    question: str
    yes_token_id: str
    no_token_id: str
    yes_price: float          # 0–1
    no_price: float           # 0–1
    volume_usd: float
    end_date: str
    days_to_close: float
    category: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class ResearchReport:
    market: LiveMarket
    our_yes_prob: float           # our estimated YES probability
    edge_pct: float               # edge over market price (%)
    ev: float                     # expected value per $1 bet
    kelly_pct: float              # kelly fraction (%)
    recommended_side: str         # "YES" | "NO" | "SKIP"
    confidence: str               # "HIGH" | "MEDIUM" | "LOW"
    reasoning: list[str]          # bullet points explaining the score
    score: float                  # composite 0–100 score
    scanned_at: float = field(default_factory=time.time)

    def to_telegram(self) -> str:
        conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(self.confidence, "⚪")
        side_emoji = {"YES": "✅", "NO": "❌", "SKIP": "⏭"}.get(self.recommended_side, "")
        reasoning_text = "\n".join(f"  • {r}" for r in self.reasoning)
        return (
            f"🔬 *POLYMARKET RESEARCH*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"*{self.market.question}*\n\n"
            f"{conf_emoji} Confidence: `{self.confidence}`\n"
            f"{side_emoji} Recommended: `{self.recommended_side}`\n\n"
            f"📊 *Probability Analysis*\n"
            f"  Market price (YES): `{self.market.yes_price*100:.1f}%`\n"
            f"  Our estimate:       `{self.our_yes_prob*100:.1f}%`\n"
            f"  Edge:               `{self.edge_pct:+.1f}%`\n"
            f"  Expected value:     `{self.ev:+.3f}` per $1\n"
            f"  Kelly size:         `{self.kelly_pct:.1f}%` of bankroll\n\n"
            f"📈 *Market Health*\n"
            f"  Volume: `${self.market.volume_usd:,.0f}`\n"
            f"  Closes in: `{self.market.days_to_close:.0f} days`\n\n"
            f"🧠 *Research Notes*\n{reasoning_text}\n\n"
            f"Composite Score: `{self.score:.0f}/100`\n"
            f"ID: `{self.market.id}`"
        )

    def to_short(self) -> str:
        conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(self.confidence, "⚪")
        return (
            f"{conf_emoji} `{self.score:.0f}/100` | "
            f"{self.recommended_side} | "
            f"edge {self.edge_pct:+.1f}% | "
            f"vol ${self.market.volume_usd/1000:.0f}k | "
            f"{self.market.days_to_close:.0f}d | "
            f"{self.market.question[:55]}…"
        )


# ── Market fetcher ────────────────────────────────────────────────────────────

def fetch_live_markets(limit: int = MAX_MARKETS_SCAN) -> list[LiveMarket]:
    """Fetch active Polymarket markets sorted by volume."""
    try:
        resp = requests.get(
            f"{GAMMA_BASE}/markets",
            params={
                "active": True,
                "closed": False,
                "limit": limit,
                "order": "volume",
                "ascending": False,
            },
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
        markets_raw = raw if isinstance(raw, list) else raw.get("markets", [])
    except Exception as e:
        logger.error(f"Polymarket fetch failed: {e}")
        return []

    markets = []
    now = time.time()

    for m in markets_raw:
        try:
            prices   = m.get("outcomePrices") or ["0.5", "0.5"]
            tokens   = m.get("clobTokenIds") or ["", ""]
            vol      = float(m.get("volume") or 0)
            end_raw  = m.get("endDate") or ""

            if vol < MIN_VOLUME_USD:
                continue

            yes_price = float(prices[0]) if prices else 0.5
            no_price  = float(prices[1]) if len(prices) > 1 else (1 - yes_price)

            # Parse days to close
            days_to_close = _days_until(end_raw)
            if days_to_close < MIN_DAYS_TO_CLOSE or days_to_close > MAX_DAYS_TO_CLOSE:
                continue

            # Skip near-certain markets (price > 95% either way — too little edge)
            if yes_price > 0.95 or yes_price < 0.05:
                continue

            markets.append(LiveMarket(
                id           = str(m.get("id", "")),
                question     = m.get("question", "Unknown"),
                yes_token_id = tokens[0] if tokens else "",
                no_token_id  = tokens[1] if len(tokens) > 1 else "",
                yes_price    = yes_price,
                no_price     = no_price,
                volume_usd   = vol,
                end_date     = end_raw,
                days_to_close= days_to_close,
                category     = m.get("category", ""),
                tags         = m.get("tags", []),
            ))
        except Exception:
            continue

    return markets


def _days_until(date_str: str) -> float:
    """Parse ISO date string and return days until that date."""
    if not date_str:
        return 30.0
    try:
        import datetime
        dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.datetime.now(datetime.timezone.utc)
        return max(0.0, (dt - now).total_seconds() / 86_400)
    except Exception:
        return 30.0


# ── Probability research engine ───────────────────────────────────────────────

def _research_market(m: LiveMarket) -> ResearchReport:
    """
    Multi-factor probability research for a single market.

    Since we don't have external news APIs, we use:
      1. Base rate — market price as Bayesian prior
      2. Time decay — shorter time = higher certainty needed
      3. Market efficiency — high volume = more efficient price
      4. Liquidity skew — if YES and NO prices don't sum to ~1, arb exists
      5. Extreme avoidance — fade extreme prices slightly
      6. Volume weight — thin markets get uncertainty penalty
    """
    reasoning = []
    p_market  = m.yes_price

    # ── Factor 1: Start from market price as prior ────────────────────────────
    p_est = p_market
    reasoning.append(f"Market prices YES at {p_market*100:.1f}% (starting estimate)")

    # ── Factor 2: Volume / liquidity quality ─────────────────────────────────
    if m.volume_usd > 500_000:
        vol_weight = 0.95   # high volume = trust the market price more
        reasoning.append(f"High volume (${m.volume_usd/1e6:.1f}M) — market is efficient")
    elif m.volume_usd > 50_000:
        vol_weight = 0.80
        reasoning.append(f"Medium volume (${m.volume_usd/1000:.0f}k) — moderate efficiency")
    else:
        vol_weight = 0.60
        reasoning.append(f"Low volume (${m.volume_usd/1000:.0f}k) — price may be stale")

    # ── Factor 3: Price sum check — if YES+NO ≠ 1.0, arb/mispricing exists ──
    price_sum = m.yes_price + m.no_price
    if abs(price_sum - 1.0) > 0.04:
        skew_side = "YES" if m.yes_price / price_sum < 0.5 else "NO"
        reasoning.append(
            f"Price sum = {price_sum:.3f} (not 1.0) — {skew_side} may be underpriced"
        )
        # Normalize and slightly favour the cheaper side
        p_est = m.yes_price / price_sum

    # ── Factor 4: Mean-reversion nudge — extreme prices are often over-priced ─
    if p_market > 0.80:
        p_est = p_est * 0.97    # slight fade of high-confidence markets
        reasoning.append("Fading high confidence slightly — markets tend to over-price near certainty")
    elif p_market < 0.20:
        p_est = p_est * 1.05    # slight boost for low-probability markets
        p_est = min(p_est, 0.25)
        reasoning.append("Boosting low-probability estimate slightly — long shots often undervalued")

    # ── Factor 5: Time pressure adjustment ────────────────────────────────────
    if m.days_to_close < 7:
        # Close to resolution — market is usually well-calibrated
        reasoning.append(f"Resolves in {m.days_to_close:.0f} days — high resolution certainty")
    elif m.days_to_close > 30:
        # Far out — wider uncertainty band
        uncertainty = 0.05 * (m.days_to_close / 30)
        p_est = p_est + (0.5 - p_est) * uncertainty * (1 - vol_weight)
        reasoning.append(f"Long time horizon ({m.days_to_close:.0f}d) — uncertainty pull toward 50%")

    # Clamp
    p_est = max(0.02, min(0.98, p_est))

    # ── Edge calculation ──────────────────────────────────────────────────────
    edge_yes = (p_est - m.yes_price) * 100      # % edge if we bet YES
    edge_no  = ((1 - p_est) - m.no_price) * 100 # % edge if we bet NO

    if abs(edge_yes) >= abs(edge_no):
        best_side = "YES" if edge_yes > 0 else "SKIP"
        best_edge = edge_yes
        bet_price = m.yes_price
    else:
        best_side = "NO" if edge_no > 0 else "SKIP"
        best_edge = edge_no
        bet_price = m.no_price

    if best_edge < MIN_EDGE_PCT:
        best_side = "SKIP"
        reasoning.append(f"Edge too small ({best_edge:+.1f}%) — no bet recommended")
    else:
        reasoning.append(f"Edge of {best_edge:+.1f}% on {best_side} — above threshold")

    # ── EV and Kelly ──────────────────────────────────────────────────────────
    if best_side == "YES":
        ev_val    = expected_value(p_est, m.yes_price)
        b         = (1 / m.yes_price) - 1   # net odds
        kelly_val = kelly_fraction(p_est, b, f_max=0.10) * 100
    elif best_side == "NO":
        p_no_est  = 1 - p_est
        ev_val    = expected_value(p_no_est, m.no_price)
        b         = (1 / m.no_price) - 1
        kelly_val = kelly_fraction(p_no_est, b, f_max=0.10) * 100
    else:
        ev_val    = 0.0
        kelly_val = 0.0

    # ── Confidence tier ───────────────────────────────────────────────────────
    if best_edge > 15 and m.volume_usd > 100_000 and best_side != "SKIP":
        confidence = "HIGH"
        reasoning.append("Strong edge + good liquidity = HIGH confidence")
    elif best_edge > MIN_EDGE_PCT and best_side != "SKIP":
        confidence = "MEDIUM"
        reasoning.append("Moderate edge detected")
    else:
        confidence = "LOW"

    # ── Composite score (0–100) ───────────────────────────────────────────────
    score = 0.0
    if best_side != "SKIP":
        score += min(40, best_edge * 2)           # up to 40 pts for edge
        score += min(20, math.log10(max(1, m.volume_usd)) * 4)   # up to 20 for volume
        score += min(20, ev_val * 20)             # up to 20 for EV
        score += min(20, kelly_val * 4)           # up to 20 for Kelly

    return ResearchReport(
        market           = m,
        our_yes_prob     = p_est,
        edge_pct         = best_edge,
        ev               = ev_val,
        kelly_pct        = kelly_val,
        recommended_side = best_side,
        confidence       = confidence,
        reasoning        = reasoning,
        score            = max(0, min(100, score)),
    )


# ── Scanner / Bot ─────────────────────────────────────────────────────────────

class PolyResearchBot:
    """
    Background bot that scans Polymarket every SCAN_INTERVAL_SEC seconds,
    scores all live markets, and surfaces the top opportunities.
    """

    def __init__(self):
        self._running        = False
        self._last_scan      = 0.0
        self._top_picks: list[ResearchReport] = []
        self._all_reports:  list[ResearchReport] = []
        self._notify_fn      = None     # async callable(str) — Telegram send
        self.scan_count      = 0
        self.total_markets_scanned = 0

    def set_notifier(self, fn):
        self._notify_fn = fn

    async def _notify(self, msg: str):
        if self._notify_fn:
            try:
                await self._notify_fn(msg)
            except Exception as e:
                logger.error(f"PolyBot notify error: {e}")

    async def start(self):
        self._running = True
        logger.info("Polymarket Research Bot started")
        while self._running:
            try:
                await self._scan()
            except Exception as e:
                logger.error(f"Polymarket scan error: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SEC)

    def stop(self):
        self._running = False

    async def _scan(self):
        logger.info("Polymarket Research Bot: scanning live markets…")
        markets = fetch_live_markets()
        if not markets:
            logger.warning("No markets returned from Polymarket scan")
            return

        reports = [_research_market(m) for m in markets]
        reports.sort(key=lambda r: r.score, reverse=True)

        self._all_reports           = reports
        self._last_scan             = time.time()
        self._top_picks             = [r for r in reports if r.recommended_side != "SKIP"][:5]
        self.scan_count            += 1
        self.total_markets_scanned += len(markets)

        high_conf = [r for r in self._top_picks if r.confidence == "HIGH"]
        logger.info(
            f"Scan #{self.scan_count}: {len(markets)} markets | "
            f"{len(self._top_picks)} opportunities | {len(high_conf)} HIGH confidence"
        )

        # Alert only on HIGH confidence finds
        if high_conf:
            lines = [f"🔬 *Polymarket Research Bot — Top Picks*\n_{len(markets)} markets scanned_\n"]
            for r in high_conf[:3]:
                lines.append(r.to_short())
            lines.append("\n_Type /bestbets for full details_")
            await self._notify("\n".join(lines))

    def get_top_picks(self, limit: int = 5) -> list[ResearchReport]:
        return self._top_picks[:limit]

    def get_all_reports(self, limit: int = 20) -> list[ResearchReport]:
        return self._all_reports[:limit]

    def research_by_id(self, market_id: str) -> Optional[ResearchReport]:
        for r in self._all_reports:
            if r.market.id == market_id:
                return r
        return None

    def scan_summary(self) -> str:
        age = int(time.time() - self._last_scan) if self._last_scan else 0
        picks = len(self._top_picks)
        high  = sum(1 for r in self._top_picks if r.confidence == "HIGH")
        return (
            f"🤖 *Polymarket Research Bot*\n"
            f"Status: {'🟢 Running' if self._running else '🔴 Stopped'}\n"
            f"Scans completed: `{self.scan_count}`\n"
            f"Markets scanned: `{self.total_markets_scanned}`\n"
            f"Last scan: `{age}s ago`\n"
            f"Current picks: `{picks}` ({high} HIGH confidence)\n"
            f"Scan interval: every `{SCAN_INTERVAL_SEC // 60} min`"
        )

    async def force_scan(self) -> str:
        """Trigger an immediate scan and return summary."""
        await self._scan()
        picks = self._top_picks
        if not picks:
            return "✅ Scan complete — no opportunities above threshold right now."
        lines = [f"✅ *Scan complete — {len(picks)} opportunities found:*\n"]
        for r in picks:
            lines.append(r.to_short())
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────
poly_research_bot = PolyResearchBot()
