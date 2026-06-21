"""
Trade & Bet Approval Queue.

Every trade (Hyperliquid perp) and prediction market bet is held here
before execution. The Telegram bot sends an approval request with
inline Approve / Reject buttons. Nothing executes until the owner taps.

Flow:
  1. Signal / manual order → approval_queue.request(trade)
  2. Telegram sends message with ✅ / ❌ buttons
  3. Owner taps Approve  → trade executes, result sent back via Telegram
  4. Owner taps Reject   → trade cancelled, notification sent
  5. No response in APPROVAL_TIMEOUT_SECS → auto-rejected

Thread-safe: asyncio.Event used for waiting.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional
from loguru import logger

# How long (seconds) to wait for approval before auto-rejecting
APPROVAL_TIMEOUT_SECS: int = 120   # 2 minutes


@dataclass
class PendingRequest:
    id: str                          # unique request ID (used in callback_data)
    kind: str                        # "trade" | "bet"
    summary: str                     # human-readable one-liner shown in Telegram
    detail: str                      # full detail block shown in Telegram
    execute_fn: Callable[[], Awaitable[str]]  # coroutine that performs the action
    created_at: float = field(default_factory=time.time)
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    approved: Optional[bool] = None  # None=pending, True=approved, False=rejected

    def resolve(self, approved: bool):
        self.approved = approved
        self._event.set()

    async def wait(self) -> bool:
        """Block until resolved or timeout. Returns True if approved."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=APPROVAL_TIMEOUT_SECS)
        except asyncio.TimeoutError:
            self.approved = False
            logger.warning(f"Approval timed out for request {self.id}")
        return bool(self.approved)


class ApprovalQueue:
    """Singleton queue of pending approval requests."""

    def __init__(self):
        self._pending: dict[str, PendingRequest] = {}
        self._notify_fn: Optional[Callable[[PendingRequest], Awaitable[None]]] = None

    def set_notifier(self, fn: Callable[[PendingRequest], Awaitable[None]]):
        """Register the Telegram notification coroutine."""
        self._notify_fn = fn

    async def request(self, kind: str, summary: str, detail: str,
                      execute_fn: Callable[[], Awaitable[str]]) -> str:
        """
        Submit a trade/bet for approval.

        Sends a Telegram approval message, then blocks until the owner
        approves, rejects, or the timeout elapses.

        Returns the result string (execution output or rejection notice).
        """
        req = PendingRequest(
            id=str(uuid.uuid4())[:8],
            kind=kind,
            summary=summary,
            detail=detail,
            execute_fn=execute_fn,
        )
        self._pending[req.id] = req
        logger.info(f"Approval requested [{req.id}]: {summary}")

        # Fire Telegram notification (non-blocking — the bot sends the message)
        if self._notify_fn:
            try:
                await self._notify_fn(req)
            except Exception as e:
                logger.error(f"Failed to send approval notification: {e}")
                # If we can't notify, auto-reject for safety
                del self._pending[req.id]
                return f"❌ Rejected (notification failed: {e})"

        # Wait for owner's decision
        approved = await req.wait()
        self._pending.pop(req.id, None)

        if approved:
            logger.info(f"Approved [{req.id}] — executing")
            try:
                result = await execute_fn()
                return result
            except Exception as e:
                logger.error(f"Execution failed after approval [{req.id}]: {e}")
                return f"❌ Execution failed: {e}"
        else:
            reason = "timed out" if req.approved is False and not req._event.is_set() else "rejected by owner"
            logger.info(f"Rejected [{req.id}]: {reason}")
            return f"❌ {kind.title()} {reason}: {summary}"

    def resolve(self, req_id: str, approved: bool) -> bool:
        """
        Called when the owner taps Approve or Reject in Telegram.
        Returns True if the request was found and resolved.
        """
        req = self._pending.get(req_id)
        if not req:
            return False
        req.resolve(approved)
        return True

    def get_pending(self) -> list[PendingRequest]:
        return list(self._pending.values())

    def pending_count(self) -> int:
        return len(self._pending)


# ── Singleton ─────────────────────────────────────────────────────────────────
approval_queue = ApprovalQueue()
