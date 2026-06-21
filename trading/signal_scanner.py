"""
Best Brand Co. — Auto Signal Scanner

Runs in the background every N minutes.
For every asset in the watchlist it:
  1. Fetches candles
  2. Runs HOTT/LOTT + Xtreme Trend
  3. Detects if a NEW signal just fired (state change on the last bar)
  4. Scores it with the pattern engine (win rate, expectancy, R:R)
  5. If confidence ≥ threshold → sends Telegram approval request
     with full trade proposal and ✅ Approve / ❌ Reject buttons

Only fires when the signal CHANGES — not every scan, preventing spam.
Signal state is persisted in memory so duplicate alerts are suppressed.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable
from loguru import logger

from trading.pattern_engine import evaluate_current, SignalVerdict, BUY_LABELS, SELL_LABELS

# ── Config ────────────────────────────────────────────────────────────────────

SCAN_INTERVAL_SEC  = 300    # scan every 5 minutes
MIN_CONFIDENCE     = 55.0   # minimum confidence % to send an alert
MIN_SAMPLE_SIZE    = 8      # need at least this many historical signals

# Assets to scan — (display_name, ticker, timeframe)
SCAN_LIST: list[tuple[str, str, str]] = [
    # Crypto perps
    ("Bitcoin",      "BTC",  "1h"),
    ("Ethereum",     "ETH",  "1h"),
    ("Solana",       "SOL",  "1h"),
    ("Dogecoin",     "DOGE", "1h"),
    ("SUI",          "SUI",  "1h"),
    # Futures
    ("Crude Oil",    "CL",   "1h"),
    ("Gold",         "GC",   "1h"),
    ("S&P 500",      "ES",   "1h"),
    ("NASDAQ",       "NQ",   "1h"),
]


# ── State tracking (suppress duplicate alerts) ────────────────────────────────

@dataclass
class AssetState:
    ticker: str
    last_signal_label: str = "FLAT"   # last label that was alerted
    last_alert_ts: float   = 0.0
    last_verdict: Optional[SignalVerdict] = None


# ── Scanner ───────────────────────────────────────────────────────────────────

class SignalScanner:
    def __init__(self):
        self._running  = False
        self._states:  dict[str, AssetState] = {
            ticker: AssetState(ticker=ticker)
            for _, ticker, _ in SCAN_LIST
        }
        self._notify_fn: Optional[Callable[[str], Awaitable[None]]] = None
        self._last_scan_ts: float = 0.0
        self._alerts_sent: int = 0

    def set_notifier(self, fn: Callable[[str], Awaitable[None]]):
        """Register async fn(message_text) to send Telegram alerts."""
        self._notify_fn = fn

    def stop(self):
        self._running = False

    async def start(self):
        """Main loop — runs forever until stop() is called."""
        self._running = True
        logger.info(f"Signal scanner started — scanning {len(SCAN_LIST)} assets every {SCAN_INTERVAL_SEC}s")
        while self._running:
            try:
                await self._scan_all()
            except Exception as e:
                logger.error(f"Scanner error: {e}")
            await asyncio.sleep(SCAN_INTERVAL_SEC)

    async def force_scan(self) -> str:
        """Trigger an immediate scan and return a summary string."""
        fired = await self._scan_all()
        ts = time.strftime("%H:%M:%S")
        if fired:
            return f"🔍 Scan complete ({ts}) — {len(fired)} signal(s) fired:\n" + "\n".join(fired)
        return f"🔍 Scan complete ({ts}) — no new signals above threshold."

    async def _scan_all(self) -> list[str]:
        """Scan every asset, return list of alert summaries."""
        from analysis.data_fetcher import fetch_candles
        self._last_scan_ts = time.time()
        fired: list[str] = []

        for display, ticker, tf in SCAN_LIST:
            try:
                df = fetch_candles(ticker, tf, limit=300)
                if df.empty or len(df) < 50:
                    continue

                verdict = evaluate_current(df)
                state   = self._states[ticker]

                # Skip WAIT / FLAT / no-edge signals
                if verdict.action == "WAIT":
                    continue
                if verdict.confidence < MIN_CONFIDENCE:
                    continue
                if verdict.sample_size < MIN_SAMPLE_SIZE:
                    continue

                # Suppress if same signal label is already active
                if verdict.label == state.last_signal_label:
                    continue

                # New signal — update state and fire alert
                state.last_signal_label = verdict.label
                state.last_verdict      = verdict
                state.last_alert_ts     = time.time()
                self._alerts_sent      += 1

                summary = f"{display} ({ticker}) {tf} — {verdict.action}"
                fired.append(summary)
                logger.info(f"Signal scanner: NEW SIGNAL — {summary} | conf={verdict.confidence:.0f}%")

                await self._send_trade_proposal(display, ticker, tf, verdict)

            except Exception as e:
                logger.warning(f"Scanner: {ticker} failed — {e}")

        return fired

    async def _send_trade_proposal(self, display: str, ticker: str, tf: str,
                                    verdict: SignalVerdict):
        """
        Route the signal through the approval queue.
        The queue sends a Telegram message with ✅ Approve / ❌ Reject.
        If approved, executes the trade on Hyperliquid (crypto) or logs
        it for manual execution (futures/FX — not on Hyperliquid).
        """
        from analysis.data_fetcher import is_crypto
        from trading.approval import approval_queue

        action_emoji = "📈" if verdict.action == "LONG" else "📉"
        bar = "█" * int(verdict.confidence / 10) + "░" * (10 - int(verdict.confidence / 10))

        summary = f"{verdict.action} {ticker} @ ${verdict.entry_price:,.4f} ({verdict.confidence:.0f}% conf)"

        detail = (
            f"{action_emoji} *{verdict.action} SIGNAL — {display} ({ticker})*\n"
            f"Timeframe: `{tf}`\n"
            f"Confidence: `[{bar}] {verdict.confidence:.0f}%`\n"
            f"Setup: `{verdict.label}`\n"
            f"\n"
            f"*Entry:*  `${verdict.entry_price:,.4f}`\n"
            f"*Stop:*   `${verdict.stop_loss:,.4f}`\n"
            f"*TP 1:*   `${verdict.take_profit_1:,.4f}`\n"
            f"*TP 2:*   `${verdict.take_profit_2:,.4f}`\n"
            f"\n"
            f"*Pattern stats* ({verdict.sample_size} historical signals)\n"
            f"Win rate:   `{verdict.win_rate*100:.0f}%`\n"
            f"Expectancy: `{verdict.expectancy:+.2f}%` per trade\n"
            f"R:R:        `1:{verdict.rr:.1f}`\n"
            f"\n"
            f"_{verdict.reasoning}_"
        )

        crypto = is_crypto(ticker)

        async def execute() -> str:
            if crypto:
                from trading import hyperliquid as hl
                from trading.state import state, Position
                from trading.fees import collect_fee, FEE_RATE
                from config import cfg

                is_buy = verdict.action == "LONG"
                # Size from account value
                summary_acc = hl.get_account_summary()
                acct_val    = float(summary_acc.get("account_value") or 0)
                price       = verdict.entry_price
                size        = round(acct_val * (cfg.MAX_TRADE_PCT / 100) / price, 6) if price else 0
                if size <= 0:
                    return f"❌ Cannot size position for {ticker} — check account balance"

                result = hl.market_open(ticker, is_buy=is_buy, size=size)
                try:
                    hl.set_stop_loss(ticker, verdict.stop_loss, size)
                except Exception as e:
                    logger.warning(f"Stop-loss failed: {e}")

                state.positions.append(Position(
                    token_in="USD", token_out=ticker,
                    amount_in=size * price, amount_out=size,
                    entry_price=price, stop_loss=verdict.stop_loss,
                    chain="hyperliquid", tx_hash=str(result),
                    opened_at=time.time(),
                ))
                try:
                    fee = collect_fee(ticker, size, price, verdict.action.lower())
                    fee_str = f"\nFee: ${fee['fee_usd']:.4f}"
                except Exception:
                    fee_str = ""

                return (
                    f"✅ *{verdict.action} EXECUTED*\n"
                    f"{size} {ticker} @ ${price:,.4f}\n"
                    f"Stop: ${verdict.stop_loss:,.4f}\n"
                    f"TP1:  ${verdict.take_profit_1:,.4f}{fee_str}"
                )
            else:
                # Non-crypto (CL, GC, ES…) — Hyperliquid doesn't carry these.
                # Log for manual execution and return info.
                return (
                    f"📋 *SIGNAL LOGGED — {ticker}* (manual execution)\n"
                    f"{verdict.action} @ ${verdict.entry_price:,.4f}\n"
                    f"Stop: ${verdict.stop_loss:,.4f}\n"
                    f"TP1:  ${verdict.take_profit_1:,.4f}\n"
                    f"TP2:  ${verdict.take_profit_2:,.4f}\n"
                    f"_(Execute manually — {ticker} not on Hyperliquid)_"
                )

        try:
            result = await approval_queue.request("trade", summary, detail, execute)
            # Send execution result back via notify fn
            if self._notify_fn:
                await self._notify_fn(result)
        except Exception as e:
            logger.error(f"Approval flow failed for {ticker}: {e}")

    def status(self) -> str:
        """Return a summary of scanner state."""
        ts = time.strftime("%H:%M:%S", time.localtime(self._last_scan_ts)) if self._last_scan_ts else "never"
        active = [
            f"{t}: {s.last_signal_label}"
            for t, s in self._states.items()
            if s.last_signal_label not in ("FLAT", "CONFLICT", "")
        ]
        lines = [
            f"🔍 *Signal Scanner*",
            f"Last scan: `{ts}`",
            f"Interval:  every {SCAN_INTERVAL_SEC // 60} min",
            f"Assets:    {len(SCAN_LIST)}",
            f"Alerts:    {self._alerts_sent} sent",
        ]
        if active:
            lines.append("\n*Active signals:*")
            lines += [f"  • {a}" for a in active]
        else:
            lines.append("No active signals above threshold.")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────
signal_scanner = SignalScanner()
