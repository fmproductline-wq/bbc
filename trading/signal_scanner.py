"""
Best Brand Co. — Auto Signal Scanner

Runs in the background every N minutes.
For every asset in the watchlist it:
  1. Fetches 1h candles (1000 bars) AND 4h candles for MTF confirmation (#5, #11)
  2. Runs HOTT/LOTT + Xtreme Trend
  3. Detects if a NEW signal just fired (state change on the last bar)
  4. If MTF_CONFIRMATION is on: requires 1h and 4h to agree on direction (#11)
  5. Scores it with the pattern engine (win rate, expectancy, R:R)
  6. If confidence ≥ threshold → sends Telegram approval request
     with full trade proposal and ✅ Approve / ❌ Reject buttons

Only fires when the signal CHANGES — not every scan, preventing spam.
Position sizing uses RISK_PCT_PER_TRADE (account risk %) instead of
a fixed % of account, so size is derived from the ATR stop distance (#7).
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
BACKTEST_LIMIT     = 1000   # bars of history to feed pattern engine (#5)

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

# Confirmation timeframe for MTF check (#11)
_MTF_TF = "4h"


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
        from config import cfg
        self._last_scan_ts = time.time()
        fired: list[str] = []

        mtf_enabled = cfg.MTF_CONFIRMATION

        for display, ticker, tf in SCAN_LIST:
            try:
                # ── 1h data (primary) ─────────────────────────────────────────
                df = fetch_candles(ticker, tf, limit=BACKTEST_LIMIT)
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

                # ── #11: Multi-timeframe confirmation ─────────────────────────
                if mtf_enabled:
                    try:
                        df4h = fetch_candles(ticker, _MTF_TF, limit=300)
                        if not df4h.empty and len(df4h) >= 30:
                            verdict_4h = evaluate_current(df4h)
                            if verdict_4h.action != "WAIT" and verdict_4h.action != verdict.action:
                                logger.info(
                                    f"Scanner: {ticker} {tf} says {verdict.action} but 4h says "
                                    f"{verdict_4h.action} — MTF conflict, skipping"
                                )
                                continue
                    except Exception as e:
                        logger.warning(f"Scanner: MTF check failed for {ticker}: {e}")

                # Suppress if same signal label is already active
                if verdict.label == state.last_signal_label:
                    continue

                # New signal — update state and fire alert
                state.last_signal_label = verdict.label
                state.last_verdict      = verdict
                state.last_alert_ts     = time.time()
                self._alerts_sent      += 1

                summary = f"{display} ({ticker}) {tf} — {verdict.action}"
                if mtf_enabled:
                    summary += " ✓MTF"
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
        On approval: executes trade with risk-% position sizing (#7).
        """
        from analysis.data_fetcher import is_crypto
        from trading.approval import approval_queue
        from config import cfg

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
                from trading.fees import collect_fee
                from trading.trade_history import record_open   # #3
                from config import cfg

                is_buy = verdict.action == "LONG"
                price  = verdict.entry_price
                sl     = verdict.stop_loss

                # ── #7: Risk-% sizing — risk RISK_PCT_PER_TRADE of account ──
                summary_acc = hl.get_account_summary()
                acct_val    = float(summary_acc.get("account_value") or 0)
                risk_usd    = acct_val * (cfg.RISK_PCT_PER_TRADE / 100)
                sl_dist     = abs(price - sl)
                size        = round(risk_usd / sl_dist, 6) if sl_dist > 0 else 0

                # Fallback: cap at MAX_TRADE_PCT of account value
                max_size = round(acct_val * (cfg.MAX_TRADE_PCT / 100) / price, 6)
                size = min(size, max_size)

                if size <= 0:
                    return f"❌ Cannot size position for {ticker} — check account balance"

                result = hl.market_open(ticker, is_buy=is_buy, size=size)
                try:
                    hl.set_stop_loss(ticker, sl, size)
                except Exception as e:
                    logger.warning(f"Stop-loss failed: {e}")

                # ── #3: Record to trade history DB ────────────────────────────
                trade_id = record_open(
                    ticker=ticker, action=verdict.action,
                    entry_price=price, size=size,
                    stop_loss=sl,
                    take_profit1=verdict.take_profit_1,
                    take_profit2=verdict.take_profit_2,
                    signal_label=verdict.label,
                    timeframe=tf,
                    confidence=verdict.confidence,
                )

                pos = Position(
                    token_in="USD", token_out=ticker,
                    amount_in=size * price, amount_out=size,
                    entry_price=price, stop_loss=sl,
                    chain="hyperliquid", tx_hash=str(result),
                    opened_at=time.time(),
                    take_profit_1=verdict.take_profit_1,
                    take_profit_2=verdict.take_profit_2,
                    size=size,
                    trade_history_id=trade_id,
                )
                state.positions.append(pos)

                try:
                    fee = collect_fee(ticker, size, price, verdict.action.lower())
                    fee_str = f"\nFee: ${fee['fee_usd']:.4f}"
                except Exception:
                    fee_str = ""

                risk_str = f"Risk: ${risk_usd:.2f} ({cfg.RISK_PCT_PER_TRADE:.1f}% of ${acct_val:,.0f})"
                return (
                    f"✅ *{verdict.action} EXECUTED*\n"
                    f"{size} {ticker} @ ${price:,.4f}\n"
                    f"Stop: ${sl:,.4f}\n"
                    f"TP1:  ${verdict.take_profit_1:,.4f}\n"
                    f"{risk_str}{fee_str}"
                )
            else:
                # Non-crypto (CL, GC, ES…) — log for manual execution.
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
            if self._notify_fn:
                await self._notify_fn(result)
        except Exception as e:
            logger.error(f"Approval flow failed for {ticker}: {e}")

    def status(self) -> str:
        """Return a summary of scanner state."""
        from config import cfg
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
            f"MTF:       `{'ON' if cfg.MTF_CONFIRMATION else 'OFF'}`",
            f"Risk/trade:`{cfg.RISK_PCT_PER_TRADE:.1f}%`",
        ]
        if active:
            lines.append("\n*Active signals:*")
            lines += [f"  • {a}" for a in active]
        else:
            lines.append("No active signals above threshold.")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────
signal_scanner = SignalScanner()
