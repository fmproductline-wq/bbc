"""
Trade-Only Mode — strict fund protection layer.

When TRADE_ONLY_MODE is ON (default: ON) the bot is hard-restricted to:
  ✅ Open long / short positions
  ✅ Close positions
  ✅ Set stop-loss / take-profit orders
  ✅ Withdraw PROFITS ONLY (never principal)

  ❌ Transfer funds for any other purpose
  ❌ Use funds for prediction market bets
  ❌ Pay platform fees from trading capital
  ❌ Withdraw more than realised profit
  ❌ Any action not explicitly whitelisted

Every blocked action raises FundRestrictionError and is logged + Telegram-alerted.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from loguru import logger


class FundRestrictionError(Exception):
    """Raised when an action is blocked by Trade-Only Mode."""


# ── Allowed action whitelist ──────────────────────────────────────────────────

ALLOWED_ACTIONS = frozenset([
    "market_open",
    "market_close",
    "limit_open",
    "set_stop_loss",
    "set_leverage",
    "cancel_order",
    "withdraw_profit",      # only profits, never principal
])

BLOCKED_ACTIONS = frozenset([
    "usd_transfer",         # generic transfer — blocked unless it's profit withdrawal
    "bet",                  # prediction market bets blocked from trading wallet
    "swap",                 # DEX swaps blocked
    "send",                 # wallet sends blocked
    "l1_transfer",          # L1 bridge transfer blocked
])


# ── Profit tracker ────────────────────────────────────────────────────────────

@dataclass
class ProfitLedger:
    """Tracks realised PnL and ensures only profits can be withdrawn."""
    deposits: list[dict]         = field(default_factory=list)
    withdrawals: list[dict]      = field(default_factory=list)
    realised_pnl_usd: float      = 0.0   # cumulative realised profit in USD
    total_withdrawn_usd: float   = 0.0

    def record_realised_pnl(self, pnl_usd: float, trade_info: str = ""):
        self.realised_pnl_usd += pnl_usd
        logger.info(f"Realised PnL recorded: ${pnl_usd:+.4f} | cumulative: ${self.realised_pnl_usd:+.4f} | {trade_info}")

    def available_profit(self) -> float:
        """How much profit is available to withdraw (never negative)."""
        return max(0.0, self.realised_pnl_usd - self.total_withdrawn_usd)

    def request_withdrawal(self, amount_usd: float) -> float:
        """
        Validate and approve a profit withdrawal.
        Raises FundRestrictionError if amount exceeds available profit.
        Returns the approved amount.
        """
        available = self.available_profit()
        if amount_usd <= 0:
            raise FundRestrictionError("Withdrawal amount must be positive.")
        if amount_usd > available:
            raise FundRestrictionError(
                f"❌ BLOCKED: Withdrawal of ${amount_usd:.2f} exceeds available profit "
                f"(${available:.2f}). Principal is protected and cannot be withdrawn "
                f"through this system."
            )
        self.total_withdrawn_usd += amount_usd
        self.withdrawals.append({
            "amount_usd": amount_usd,
            "timestamp": time.time(),
            "available_before": available,
            "remaining_after": self.available_profit(),
        })
        logger.info(
            f"Profit withdrawal approved: ${amount_usd:.2f} | "
            f"remaining profit: ${self.available_profit():.2f}"
        )
        return amount_usd

    def summary(self) -> dict:
        return {
            "realised_pnl_usd":    round(self.realised_pnl_usd, 4),
            "total_withdrawn_usd": round(self.total_withdrawn_usd, 4),
            "available_profit":    round(self.available_profit(), 4),
            "withdrawal_count":    len(self.withdrawals),
        }


# ── Guard ─────────────────────────────────────────────────────────────────────

class TradeOnlyGuard:
    """
    Singleton enforcement layer. Call guard.check(action) before any
    fund-touching operation. Raises FundRestrictionError if blocked.
    """

    def __init__(self):
        self.enabled: bool = True       # Trade-Only Mode ON by default
        self.ledger = ProfitLedger()
        self._notify_fn = None          # set by telegram bot
        self._blocked_log: list[dict] = []

    def set_notifier(self, fn):
        self._notify_fn = fn

    def check(self, action: str, context: str = ""):
        """
        Enforce Trade-Only Mode.
        Raises FundRestrictionError for any blocked action.
        """
        if not self.enabled:
            return   # guard disabled — allow everything

        if action in BLOCKED_ACTIONS:
            msg = (
                f"🚫 *TRADE-ONLY MODE BLOCKED*\n"
                f"Action: `{action}`\n"
                f"Context: {context}\n"
                f"Funds are restricted to trading and profit withdrawal only."
            )
            self._log_blocked(action, context)
            logger.critical(f"BLOCKED by Trade-Only Mode: {action} | {context}")
            if self._notify_fn:
                import asyncio
                try:
                    asyncio.create_task(self._notify_fn(msg))
                except RuntimeError:
                    pass
            raise FundRestrictionError(msg)

        if action not in ALLOWED_ACTIONS:
            msg = f"🚫 BLOCKED: '{action}' is not on the Trade-Only whitelist."
            self._log_blocked(action, context)
            logger.warning(f"Unknown action blocked: {action}")
            raise FundRestrictionError(msg)

    def check_profit_withdrawal(self, amount_usd: float) -> float:
        """Validate a profit withdrawal request. Returns approved amount."""
        self.check("withdraw_profit", f"${amount_usd:.2f}")
        return self.ledger.request_withdrawal(amount_usd)

    def record_trade_pnl(self, pnl_usd: float, trade_info: str = ""):
        """Call after every closed trade to track cumulative profit."""
        self.ledger.record_realised_pnl(pnl_usd, trade_info)

    def _log_blocked(self, action: str, context: str):
        self._blocked_log.insert(0, {
            "action": action,
            "context": context,
            "timestamp": time.time(),
        })
        if len(self._blocked_log) > 200:
            self._blocked_log.pop()

    def get_blocked_log(self, limit: int = 20) -> list[dict]:
        return self._blocked_log[:limit]

    def profit_summary(self) -> dict:
        return self.ledger.summary()

    def status_text(self) -> str:
        s = self.ledger.summary()
        status = "🟢 ON" if self.enabled else "🔴 OFF"
        return (
            f"🔒 *Trade-Only Mode:* {status}\n"
            f"📈 Realised PnL:   `${s['realised_pnl_usd']:+.4f}`\n"
            f"💸 Withdrawn:      `${s['total_withdrawn_usd']:.4f}`\n"
            f"✅ Available:      `${s['available_profit']:.4f}`\n\n"
            f"Funds may only be used for trading.\n"
            f"Withdrawals are limited to realised profits only."
        )


# ── Singleton ─────────────────────────────────────────────────────────────────
guard = TradeOnlyGuard()
