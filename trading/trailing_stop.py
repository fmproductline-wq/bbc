"""
Best Brand Co. — Trailing Stop Monitor  (#10)

Background task that checks open Hyperliquid positions every 30 s.
When price reaches TP1, moves stop loss to breakeven (entry price).
This locks in profit without needing manual intervention.

Logic per position:
  1. Fetch current mid price from Hyperliquid
  2. Compare against stored TP1 and entry
  3. If price >= TP1 (long) or price <= TP1 (short) AND stop is still below/above entry:
       → call set_stop_loss(entry_price)  to move to breakeven
       → send Telegram notification
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Callable, Awaitable
from loguru import logger

CHECK_INTERVAL_SEC = 30


class TrailingStopMonitor:
    def __init__(self):
        self._running   = False
        self._moved:    set[str] = set()   # tickers already moved to breakeven
        self._notify_fn: Optional[Callable[[str], Awaitable[None]]] = None

    def set_notifier(self, fn: Callable[[str], Awaitable[None]]):
        self._notify_fn = fn

    def stop(self):
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Trailing stop monitor started")
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                logger.warning(f"Trailing stop monitor error: {e}")
            await asyncio.sleep(CHECK_INTERVAL_SEC)

    async def _check_all(self):
        from trading.state import state
        if not state.positions:
            return

        mids = await asyncio.get_event_loop().run_in_executor(None, self._fetch_mids)
        if not mids:
            return

        for pos in list(state.positions):
            ticker = pos.token_out
            if ticker in self._moved:
                continue

            price = mids.get(ticker)
            if not price:
                continue

            entry = pos.entry_price
            sl    = pos.stop_loss
            tp1   = pos.take_profit_1

            if not entry or not tp1:
                continue

            if sl is None:
                continue

            # Direction: long if stop is below entry, short if above
            is_long = sl < entry

            # Check if TP1 hit and stop still below entry (long) / above entry (short)
            tp1_hit = (price >= tp1) if is_long else (price <= tp1)
            sl_not_moved = (sl < entry) if is_long else (sl > entry)

            size = getattr(pos, "size", None) or getattr(pos, "amount_out", 0)
            if tp1_hit and sl_not_moved:
                await self._move_to_breakeven(ticker, entry, size, is_long)
                self._moved.add(ticker)
                # Update the in-memory position
                pos.stop_loss = entry

    def _fetch_mids(self) -> dict[str, float]:
        try:
            from trading.hyperliquid import get_all_mids
            return get_all_mids()
        except Exception as e:
            logger.warning(f"Trailing stop: could not fetch prices — {e}")
            return {}

    async def _move_to_breakeven(self, ticker: str, entry: float, size: float, is_long: bool):
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._set_sl, ticker, entry, size
            )
            msg = (
                f"🔒 *Stop moved to breakeven — {ticker}*\n"
                f"TP1 reached — stop loss set to entry `${entry:,.4f}`\n"
                f"Position is now risk-free."
            )
            logger.info(f"Trailing stop: moved {ticker} stop to breakeven @ {entry}")
            if self._notify_fn:
                await self._notify_fn(msg)
        except Exception as e:
            logger.warning(f"Trailing stop: failed to move SL for {ticker}: {e}")

    def _set_sl(self, ticker: str, entry: float, size: float):
        from trading.hyperliquid import set_stop_loss
        set_stop_loss(ticker, entry, size)

    def reset_ticker(self, ticker: str):
        """Call this when a position is closed to allow trailing on re-entry."""
        self._moved.discard(ticker)


trailing_stop_monitor = TrailingStopMonitor()
