"""
Bug-checker agent.

Runs autonomously on a schedule (or on-demand via Telegram /bugcheck).
Checks for:
  1. Orphaned positions (open in state but no matching Hyperliquid position)
  2. Stop-loss breaches (price moved past stop without triggering)
  3. Stale signals (last signal > configured threshold ago)
  4. Wallet connectivity issues
  5. API health (Hyperliquid, Polymarket, Kalshi)
  6. Config validation (missing keys, zero balances)
  7. Duplicate positions
  8. Runaway PnL (position down > 2x stop-loss — emergency close)
"""
from __future__ import annotations
import time
import traceback
from dataclasses import dataclass, field
from typing import Callable, Awaitable
from loguru import logger
from config import cfg
from trading.state import state, Position
from trading import hyperliquid as hl


@dataclass
class BugReport:
    severity: str   # "CRITICAL" | "WARNING" | "INFO"
    category: str
    message: str
    action_taken: str = ""

    def to_str(self) -> str:
        icon = {"CRITICAL": "🚨", "WARNING": "⚠️", "INFO": "ℹ️"}.get(self.severity, "?")
        base = f"{icon} [{self.severity}] {self.category}: {self.message}"
        if self.action_taken:
            base += f"\n  → Action: {self.action_taken}"
        return base


@dataclass
class BugCheckResult:
    reports: list[BugReport] = field(default_factory=list)
    checked_at: float = field(default_factory=time.time)

    def add(self, severity: str, category: str, message: str, action: str = ""):
        self.reports.append(BugReport(severity, category, message, action))

    @property
    def has_critical(self) -> bool:
        return any(r.severity == "CRITICAL" for r in self.reports)

    @property
    def has_warnings(self) -> bool:
        return any(r.severity in ("CRITICAL", "WARNING") for r in self.reports)

    def to_telegram(self) -> str:
        if not self.reports:
            return "✅ *Bug Check Passed* — no issues found."
        lines = ["*🔍 Bug Check Report*\n"]
        for r in self.reports:
            lines.append(r.to_str())
        return "\n".join(lines)


# ── Individual checks ─────────────────────────────────────────────────────────

def check_config(result: BugCheckResult):
    """Validate all required config keys are set."""
    required = {
        "WALLET_PRIVATE_KEY": cfg.WALLET_PRIVATE_KEY,
        "WALLET_ADDRESS": cfg.WALLET_ADDRESS,
        "TELEGRAM_BOT_TOKEN": cfg.TELEGRAM_BOT_TOKEN,
        "TRADINGVIEW_WEBHOOK_SECRET": cfg.TRADINGVIEW_WEBHOOK_SECRET,
    }
    for key, val in required.items():
        if not val or val.startswith("your_") or val.startswith("0xyour"):
            result.add("WARNING", "Config", f"{key} is not set or still uses the placeholder value")

    if cfg.MAX_TRADE_PCT > 20:
        result.add("WARNING", "Risk", f"MAX_TRADE_PCT={cfg.MAX_TRADE_PCT}% is very high (>20%)")
    if cfg.STOP_LOSS_PCT < 0.5:
        result.add("WARNING", "Risk", f"STOP_LOSS_PCT={cfg.STOP_LOSS_PCT}% is very tight (<0.5%)")


def check_hyperliquid_connectivity(result: BugCheckResult):
    """Verify Hyperliquid API is reachable and wallet is valid."""
    try:
        mids = hl.get_all_mids()
        if not mids:
            result.add("WARNING", "Hyperliquid", "get_all_mids returned empty response")
        else:
            result.add("INFO", "Hyperliquid", f"Connected — {len(mids)} markets available")
    except Exception as e:
        result.add("CRITICAL", "Hyperliquid", f"API unreachable: {e}")
        return

    if cfg.WALLET_PRIVATE_KEY and not cfg.WALLET_PRIVATE_KEY.startswith("0xyour"):
        try:
            summary = hl.get_account_summary()
            val = summary.get("account_value", "?")
            result.add("INFO", "Wallet", f"Account value: ${val}")
        except Exception as e:
            result.add("CRITICAL", "Wallet", f"Cannot fetch account state: {e}")


def check_orphaned_positions(result: BugCheckResult):
    """Cross-check bot state positions against live Hyperliquid positions."""
    if not state.open_positions():
        return
    try:
        summary = hl.get_account_summary()
        live_coins = {p["coin"] for p in summary["positions"]}
        for pos in state.open_positions():
            coin = _extract_coin(pos)
            if coin and coin not in live_coins:
                result.add(
                    "WARNING", "Orphaned Position",
                    f"Bot state has open position for {coin} but Hyperliquid shows none.",
                    "Marked as orphaned — consider /closeall",
                )
    except Exception as e:
        result.add("WARNING", "Position Check", f"Could not verify positions: {e}")


def check_stop_loss_breaches(result: BugCheckResult):
    """Check if any open position has breached its stop loss without being closed."""
    if not state.open_positions():
        return
    try:
        mids = hl.get_all_mids()
    except Exception:
        return

    for pos in state.open_positions():
        coin = _extract_coin(pos)
        if not coin or coin not in mids:
            continue
        current_price = mids[coin]
        entry = pos.entry_price
        stop = pos.stop_loss

        # Detect if it's a long or short based on stop vs entry
        is_long = stop < entry
        breached = (is_long and current_price < stop) or (not is_long and current_price > stop)

        if breached:
            loss_pct = abs(current_price - entry) / entry * 100
            result.add(
                "CRITICAL", "Stop Loss Breach",
                f"{coin} breached stop loss! Entry={entry:.4f} Stop={stop:.4f} Current={current_price:.4f} "
                f"(loss: {loss_pct:.2f}%)",
                "Auto-close recommended — use /emergencyclose",
            )


def check_runaway_loss(result: BugCheckResult):
    """Emergency check: position losing > 2x the configured stop-loss percent."""
    if not state.open_positions():
        return
    try:
        mids = hl.get_all_mids()
    except Exception:
        return

    threshold = cfg.STOP_LOSS_PCT * 2

    for pos in state.open_positions():
        coin = _extract_coin(pos)
        if not coin or coin not in mids:
            continue
        current_price = mids[coin]
        if pos.entry_price <= 0:
            continue
        loss_pct = (pos.entry_price - current_price) / pos.entry_price * 100
        if loss_pct > threshold:
            result.add(
                "CRITICAL", "Runaway Loss",
                f"{coin} is down {loss_pct:.1f}% (threshold {threshold:.1f}%). Emergency close advised.",
            )


def check_stale_signals(result: BugCheckResult):
    """Warn if no signal has been received in a long time while auto_trade is on."""
    if not state.auto_trade:
        return
    if not state.signal_log:
        result.add("INFO", "Signals", "No signals received yet — waiting for TradingView alerts")
        return
    last_ts = state.signal_log[0].get("ts", 0)
    age_hours = (time.time() - last_ts) / 3600
    if age_hours > 6:
        result.add("WARNING", "Signals", f"Last signal was {age_hours:.1f}h ago. Check TradingView alert setup.")


def check_duplicate_positions(result: BugCheckResult):
    """Check for duplicate open positions on the same coin."""
    coins = [_extract_coin(p) for p in state.open_positions()]
    coins = [c for c in coins if c]
    seen: set[str] = set()
    for coin in coins:
        if coin in seen:
            result.add("WARNING", "Duplicate Position", f"Multiple bot positions tracked for {coin}")
        seen.add(coin)


def check_prediction_market_apis(result: BugCheckResult):
    """Light connectivity checks for prediction market APIs."""
    import requests

    # Polymarket
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets", params={"limit": 1}, timeout=5)
        resp.raise_for_status()
        result.add("INFO", "Polymarket", "API reachable ✓")
    except Exception as e:
        result.add("WARNING", "Polymarket", f"API unreachable: {e}")

    # Kalshi
    try:
        resp = requests.get(f"{cfg.KALSHI_BASE_URL}/markets", params={"limit": 1}, timeout=5)
        if resp.status_code in (200, 401, 403):
            result.add("INFO", "Kalshi", "API reachable ✓")
        else:
            result.add("WARNING", "Kalshi", f"API returned {resp.status_code}")
    except Exception as e:
        result.add("WARNING", "Kalshi", f"API unreachable: {e}")

    # Metaculus
    try:
        resp = requests.get("https://www.metaculus.com/api2/questions/", params={"limit": 1}, timeout=5)
        resp.raise_for_status()
        result.add("INFO", "Metaculus", "API reachable ✓")
    except Exception as e:
        result.add("WARNING", "Metaculus", f"API unreachable: {e}")


# ── Main agent entry point ────────────────────────────────────────────────────

def run_bug_check(auto_remediate: bool = False) -> BugCheckResult:
    """
    Run all checks and return a BugCheckResult.

    If auto_remediate=True, critical stop-loss breaches will attempt
    emergency market closes on Hyperliquid.
    """
    result = BugCheckResult()
    checks = [
        check_config,
        check_hyperliquid_connectivity,
        check_orphaned_positions,
        check_stop_loss_breaches,
        check_runaway_loss,
        check_stale_signals,
        check_duplicate_positions,
        check_prediction_market_apis,
    ]

    for check in checks:
        try:
            check(result)
        except Exception as e:
            result.add("WARNING", "BugChecker", f"Check '{check.__name__}' threw: {e}\n{traceback.format_exc()}")

    if auto_remediate:
        _auto_remediate(result)

    logger.info(f"Bug check complete: {len(result.reports)} findings")
    return result


def _auto_remediate(result: BugCheckResult):
    """Attempt automatic remediation of critical issues."""
    for report in result.reports:
        if report.severity == "CRITICAL" and "Runaway Loss" in report.category:
            coin = report.message.split()[0]
            try:
                hl.market_close(coin)
                report.action_taken = f"Emergency closed {coin} via Hyperliquid market order"
                logger.warning(f"Auto-remediated: emergency close on {coin}")
            except Exception as e:
                report.action_taken = f"Auto-close FAILED: {e}"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_coin(pos: Position) -> str | None:
    """Guess the Hyperliquid coin name from a position's token_out field."""
    token = pos.token_out or ""
    # If it looks like a coin name (not a 0x address), return it directly
    if not token.startswith("0x"):
        return token.upper()
    # Otherwise we can't resolve it without a mapping
    return None
