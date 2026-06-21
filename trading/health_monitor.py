"""
Best Brand Co. — Hyperliquid Health Monitor  (#2)

Pings the Hyperliquid API every 60 s.
On failure → Telegram alert.
On recovery after failure → Telegram all-clear.
Exposed as a singleton: health_monitor.start() / .stop() / .status()
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional, Callable, Awaitable
from loguru import logger

CHECK_INTERVAL_SEC = 60       # how often to ping
FAILURE_THRESHOLD  = 2        # consecutive failures before alert
RECOVERY_THRESHOLD = 2        # consecutive successes to declare recovery


class HealthMonitor:
    def __init__(self):
        self._running          = False
        self._consecutive_fail = 0
        self._consecutive_ok   = 0
        self._is_down          = False
        self._last_check_ts    = 0.0
        self._last_latency_ms  = 0.0
        self._total_checks     = 0
        self._total_failures   = 0
        self._notify_fn: Optional[Callable[[str], Awaitable[None]]] = None

    def set_notifier(self, fn: Callable[[str], Awaitable[None]]):
        self._notify_fn = fn

    def stop(self):
        self._running = False

    async def start(self):
        self._running = True
        logger.info("Health monitor started")
        while self._running:
            await self._check()
            await asyncio.sleep(CHECK_INTERVAL_SEC)

    async def _check(self):
        self._total_checks += 1
        self._last_check_ts = time.time()
        t0 = time.monotonic()
        ok = await asyncio.get_event_loop().run_in_executor(None, self._ping_hl)
        self._last_latency_ms = (time.monotonic() - t0) * 1000

        if ok:
            self._consecutive_fail = 0
            self._consecutive_ok  += 1
            if self._is_down and self._consecutive_ok >= RECOVERY_THRESHOLD:
                self._is_down = False
                logger.info("Hyperliquid API recovered")
                await self._alert("✅ *Hyperliquid API — RECOVERED*\nConnection restored. Trading is operational.")
        else:
            self._total_failures  += 1
            self._consecutive_ok   = 0
            self._consecutive_fail += 1
            if not self._is_down and self._consecutive_fail >= FAILURE_THRESHOLD:
                self._is_down = True
                logger.error(f"Hyperliquid API DOWN — {self._consecutive_fail} consecutive failures")
                await self._alert(
                    f"🚨 *Hyperliquid API — DOWN*\n"
                    f"Failed {self._consecutive_fail} consecutive checks.\n"
                    f"*Open positions may be unprotected.* Check manually."
                )

    def _ping_hl(self) -> bool:
        try:
            from trading.hyperliquid import get_all_mids
            mids = get_all_mids()
            return bool(mids)
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def _alert(self, msg: str):
        if self._notify_fn:
            try:
                await self._notify_fn(msg)
            except Exception as e:
                logger.warning(f"Health monitor alert failed: {e}")

    def status(self) -> str:
        ts = time.strftime("%H:%M:%S", time.localtime(self._last_check_ts)) if self._last_check_ts else "never"
        state = "🔴 DOWN" if self._is_down else "🟢 OK"
        uptime = ((self._total_checks - self._total_failures) / max(self._total_checks, 1)) * 100
        return (
            f"🏥 *Health Monitor*\n"
            f"Status:    `{state}`\n"
            f"Latency:   `{self._last_latency_ms:.0f} ms`\n"
            f"Last check: `{ts}`\n"
            f"Uptime:    `{uptime:.1f}%`  ({self._total_checks - self._total_failures}/{self._total_checks} checks passed)\n"
            f"Consecutive failures: `{self._consecutive_fail}`"
        )

    def is_healthy(self) -> bool:
        return not self._is_down


health_monitor = HealthMonitor()
