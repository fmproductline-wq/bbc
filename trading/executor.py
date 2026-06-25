"""
Trade execution — every order goes through the Telegram approval queue.

Flow for every trade:
  1. Signal received / manual order
  2. Build trade parameters, calculate size + fee preview
  3. Send approval request → Telegram shows ✅ Approve / ❌ Reject
  4. Owner taps within 2 minutes → executes or cancels
  5. Result sent back via Telegram
"""
from __future__ import annotations
import time
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.state import state, Position
from trading import hyperliquid as hl
from trading.fees import collect_fee, FEE_RATE
from trading.approval import approval_queue
from trading.restrictions import guard, FundRestrictionError, ALLOWED_BET_PLATFORMS


# ── Position sizing ───────────────────────────────────────────────────────────

def _position_size(coin: str) -> float:
    try:
        summary = hl.get_account_summary()
        account_value = float(summary.get("account_value") or 0)
        if account_value <= 0:
            return 0.0
        price = hl.get_all_mids().get(coin, 0)
        if price <= 0:
            return 0.0
        return round(account_value * (cfg.MAX_TRADE_PCT / 100) / price, 6)
    except Exception as e:
        logger.error(f"Position size error: {e}")
        return 0.0


# ── Signal handler ────────────────────────────────────────────────────────────

async def handle_signal(signal: TVSignal) -> str:
    """
    Process a TradingView signal.
    Always routes through the Telegram approval queue — even with auto-trade ON.
    """
    state.log_signal(signal.to_log())
    coin = hl.coin_from_signal(signal.symbol)

    if not state.auto_trade:
        return (
            f"📡 Signal received ({signal.indicator} {signal.action} "
            f"{coin} @ ${signal.price:,.4f}) — auto-trade is OFF"
        )

    try:
        if signal.is_buy():
            return await _request_long(signal, coin)
        elif signal.is_sell():
            return await _request_close_or_short(signal, coin)
        else:
            return f"Unknown action: {signal.action}"
    except Exception as e:
        logger.error(f"Signal handling error: {e}")
        return f"❌ Error: {e}"


# ── Long ──────────────────────────────────────────────────────────────────────

async def _request_long(signal: TVSignal, coin: str) -> str:
    size = _position_size(coin)
    if size <= 0:
        return f"❌ Cannot size position for {coin} — check account balance"

    notional  = size * signal.price
    fee_est   = notional * FEE_RATE
    stop      = signal.price * (1 - cfg.STOP_LOSS_PCT / 100)
    tp1       = signal.price * (1 + cfg.STOP_LOSS_PCT * 2 / 100)

    summary = f"LONG {size} {coin} @ ${signal.price:,.4f}"
    detail  = (
        f"📈 *LONG — {coin}*\n"
        f"Signal: `{signal.indicator}` ({signal.timeframe})\n"
        f"Entry:    `${signal.price:,.4f}`\n"
        f"Size:     `{size} {coin}`\n"
        f"Notional: `${notional:,.2f}`\n"
        f"Stop:     `${stop:,.4f}` ({cfg.STOP_LOSS_PCT}%)\n"
        f"TP est:   `${tp1:,.4f}`\n"
        f"Fee:      `${fee_est:.4f}` (0.05%)\n"
        f"Exchange: Hyperliquid Perps"
    )

    async def execute() -> str:
        result = hl.market_open(coin, is_buy=True, size=size)
        try:
            hl.set_stop_loss(coin, stop, size)
        except Exception as e:
            logger.warning(f"Stop-loss placement failed: {e}")
        state.positions.append(Position(
            token_in="USD", token_out=coin,
            amount_in=notional, amount_out=size,
            entry_price=signal.price, stop_loss=stop,
            chain="hyperliquid", tx_hash=str(result),
            opened_at=time.time(),
        ))
        try:
            fee = collect_fee(coin, size, signal.price, "long")
            fee_str = f"\nPlatform fee: ${fee['fee_usd']:.4f}"
        except Exception:
            fee_str = ""
        return (
            f"✅ *LONG EXECUTED*\n"
            f"{size} {coin} @ ${signal.price:,.4f}\n"
            f"Stop: ${stop:,.4f}{fee_str}"
        )

    return await approval_queue.request("trade", summary, detail, execute)


# ── Close / Short ─────────────────────────────────────────────────────────────

async def _request_close_or_short(signal: TVSignal, coin: str) -> str:
    open_pos = [p for p in state.open_positions() if p.token_out == coin]

    if open_pos:
        # Close existing long(s)
        results = []
        for pos in open_pos:
            pnl_est = ((signal.price - pos.entry_price) / pos.entry_price) * 100
            notional  = pos.amount_out * signal.price
            fee_est   = notional * FEE_RATE
            summary   = f"CLOSE {pos.amount_out} {coin} @ ${signal.price:,.4f}"
            detail    = (
                f"🔴 *CLOSE — {coin}*\n"
                f"Signal: `{signal.indicator}` ({signal.timeframe})\n"
                f"Size:     `{pos.amount_out} {coin}`\n"
                f"Exit:     `${signal.price:,.4f}`\n"
                f"Entry:    `${pos.entry_price:,.4f}`\n"
                f"Est PnL:  `{pnl_est:+.2f}%`\n"
                f"Notional: `${notional:,.2f}`\n"
                f"Fee:      `${fee_est:.4f}` (0.05%)\n"
                f"Exchange: Hyperliquid Perps"
            )

            _pos = pos   # capture for closure

            async def execute_close(_p=_pos) -> str:
                hl.market_close(coin)
                actual_pnl_pct = ((signal.price - _p.entry_price) / _p.entry_price) * 100
                actual_pnl_usd = _p.amount_in * (actual_pnl_pct / 100)
                _p.closed = True
                _p.pnl = actual_pnl_pct
                # Record realised PnL in the Trade-Only guard
                guard.record_trade_pnl(
                    actual_pnl_usd,
                    f"{coin} close @ ${signal.price:,.4f}"
                )
                try:
                    fee = collect_fee(coin, _p.amount_out, signal.price, "close")
                    fee_str = f"\nPlatform fee: ${fee['fee_usd']:.4f}"
                except Exception:
                    fee_str = ""
                profit_avail = guard.ledger.available_profit()
                return (
                    f"✅ *CLOSED*\n"
                    f"{coin} @ ${signal.price:,.4f}\n"
                    f"PnL: {actual_pnl_pct:+.2f}% (${actual_pnl_usd:+.2f}){fee_str}\n"
                    f"Available profit: ${profit_avail:.2f}"
                )

            results.append(
                await approval_queue.request("trade", summary, detail, execute_close)
            )
        return "\n".join(results)

    # No open long — request a short
    size = _position_size(coin)
    if size <= 0:
        return f"❌ Cannot size position for {coin}"

    notional  = size * signal.price
    fee_est   = notional * FEE_RATE
    stop      = signal.price * (1 + cfg.STOP_LOSS_PCT / 100)
    tp1       = signal.price * (1 - cfg.STOP_LOSS_PCT * 2 / 100)
    summary   = f"SHORT {size} {coin} @ ${signal.price:,.4f}"
    detail    = (
        f"📉 *SHORT — {coin}*\n"
        f"Signal: `{signal.indicator}` ({signal.timeframe})\n"
        f"Entry:    `${signal.price:,.4f}`\n"
        f"Size:     `{size} {coin}`\n"
        f"Notional: `${notional:,.2f}`\n"
        f"Stop:     `${stop:,.4f}` ({cfg.STOP_LOSS_PCT}%)\n"
        f"TP est:   `${tp1:,.4f}`\n"
        f"Fee:      `${fee_est:.4f}` (0.05%)\n"
        f"Exchange: Hyperliquid Perps"
    )

    async def execute_short() -> str:
        result = hl.market_open(coin, is_buy=False, size=size)
        try:
            hl.set_stop_loss(coin, stop, size)
        except Exception as e:
            logger.warning(f"Stop-loss placement failed: {e}")
        state.positions.append(Position(
            token_in="USD", token_out=coin,
            amount_in=notional, amount_out=size,
            entry_price=signal.price, stop_loss=stop,
            chain="hyperliquid", tx_hash=str(result),
            opened_at=time.time(),
        ))
        try:
            fee = collect_fee(coin, size, signal.price, "short")
            fee_str = f"\nPlatform fee: ${fee['fee_usd']:.4f}"
        except Exception:
            fee_str = ""
        return (
            f"✅ *SHORT EXECUTED*\n"
            f"{size} {coin} @ ${signal.price:,.4f}\n"
            f"Stop: ${stop:,.4f}{fee_str}"
        )

    return await approval_queue.request("trade", summary, detail, execute_short)


# ── Manual trade helpers (called from UI / Telegram /long /short commands) ────

async def manual_long(coin: str, size: float, leverage: int | None = None) -> str:
    """Request approval then open a manual long."""
    try:
        mids   = hl.get_all_mids()
        price  = mids.get(coin, 0)
    except Exception:
        price = 0

    notional = size * price
    fee_est  = notional * FEE_RATE
    stop_est = price * (1 - cfg.STOP_LOSS_PCT / 100) if price else 0
    lev_str  = f"{leverage}x" if leverage else "current"

    summary = f"MANUAL LONG {size} {coin} @ ~${price:,.4f}"
    detail  = (
        f"📈 *MANUAL LONG — {coin}*\n"
        f"Size:     `{size} {coin}`\n"
        f"Est. price: `${price:,.4f}`\n"
        f"Notional: `${notional:,.2f}`\n"
        f"Leverage: `{lev_str}`\n"
        f"Est. stop: `${stop_est:,.4f}`\n"
        f"Fee est:  `${fee_est:.4f}` (0.02%)\n"
        f"Exchange: Hyperliquid Perps"
    )

    async def execute() -> str:
        if leverage:
            hl.set_leverage(coin, leverage)
        result = hl.market_open(coin, is_buy=True, size=size)
        if stop_est:
            try:
                hl.set_stop_loss(coin, stop_est, size)
            except Exception:
                pass
        try:
            fee = collect_fee(coin, size, price if price else 0.0, "long")
            fee_str = f"\nFee: ${fee['fee_usd']:.4f}"
        except Exception:
            fee_str = ""
        return f"✅ *MANUAL LONG*\n{size} {coin} executed{fee_str}"

    return await approval_queue.request("trade", summary, detail, execute)


async def manual_short(coin: str, size: float, leverage: int | None = None) -> str:
    """Request approval then open a manual short."""
    try:
        price = hl.get_all_mids().get(coin, 0)
    except Exception:
        price = 0

    notional = size * price
    fee_est  = notional * FEE_RATE
    stop_est = price * (1 + cfg.STOP_LOSS_PCT / 100) if price else 0
    lev_str  = f"{leverage}x" if leverage else "current"

    summary = f"MANUAL SHORT {size} {coin} @ ~${price:,.4f}"
    detail  = (
        f"📉 *MANUAL SHORT — {coin}*\n"
        f"Size:     `{size} {coin}`\n"
        f"Est. price: `${price:,.4f}`\n"
        f"Notional: `${notional:,.2f}`\n"
        f"Leverage: `{lev_str}`\n"
        f"Est. stop: `${stop_est:,.4f}`\n"
        f"Fee est:  `${fee_est:.4f}` (0.02%)\n"
        f"Exchange: Hyperliquid Perps"
    )

    async def execute() -> str:
        if leverage:
            hl.set_leverage(coin, leverage)
        result = hl.market_open(coin, is_buy=False, size=size)
        if stop_est:
            try:
                hl.set_stop_loss(coin, stop_est, size)
            except Exception:
                pass
        try:
            fee = collect_fee(coin, size, price if price else 0.0, "short")
            fee_str = f"\nFee: ${fee['fee_usd']:.4f}"
        except Exception:
            fee_str = ""
        return f"✅ *MANUAL SHORT*\n{size} {coin} executed{fee_str}"

    return await approval_queue.request("trade", summary, detail, execute)


async def manual_close(coin: str) -> str:
    """Request approval then close a position."""
    try:
        price = hl.get_all_mids().get(coin, 0)
    except Exception:
        price = 0

    open_pos = [p for p in state.open_positions() if p.token_out == coin]
    size_str = str(open_pos[0].amount_out) if open_pos else "full"
    summary  = f"CLOSE {coin} @ ~${price:,.4f}"
    detail   = (
        f"🔴 *CLOSE — {coin}*\n"
        f"Size:   `{size_str} {coin}`\n"
        f"Price:  `~${price:,.4f}`\n"
        f"Exchange: Hyperliquid Perps"
    )

    async def execute() -> str:
        hl.market_close(coin)
        for p in open_pos:
            if not p.closed:
                close_price = price or p.entry_price
                direction = 1 if (p.stop_loss is None or p.stop_loss < p.entry_price) else -1
                pnl_usd = p.amount_in * ((close_price - p.entry_price) / p.entry_price) * direction
                guard.record_trade_pnl(pnl_usd, f"{coin} manual close @ ~${close_price:,.4f}")
                p.closed = True
                # Record close in trade history DB (#3)
                if getattr(p, "trade_history_id", None):
                    try:
                        from trading.trade_history import record_close
                        record_close(p.trade_history_id, close_price, pnl_usd)
                    except Exception:
                        pass
                # Reset trailing stop tracker (#10)
                try:
                    from trading.trailing_stop import trailing_stop_monitor
                    trailing_stop_monitor.reset_ticker(coin)
                except Exception:
                    pass
        profit_avail = guard.ledger.available_profit()
        return (
            f"✅ *CLOSED* {coin} @ ~${price:,.4f}\n"
            f"Available profit: ${profit_avail:.2f}"
        )

    return await approval_queue.request("trade", summary, detail, execute)


# ── Profit withdrawal ─────────────────────────────────────────────────────────

async def request_profit_withdrawal(amount_usd: float, destination: str) -> str:
    """
    Request approval to withdraw profits to a wallet address.
    Trade-Only Mode ensures amount never exceeds realised profit.
    """
    available = guard.ledger.available_profit()

    if amount_usd > available:
        return (
            f"❌ *BLOCKED — Trade-Only Mode*\n"
            f"Requested: `${amount_usd:.2f}`\n"
            f"Available profit: `${available:.2f}`\n"
            f"You can only withdraw realised profits. Principal is protected."
        )

    summary = f"WITHDRAW PROFIT ${amount_usd:.2f} → {destination[:12]}…"
    detail  = (
        f"💰 *PROFIT WITHDRAWAL*\n"
        f"Amount:    `${amount_usd:.2f}`\n"
        f"To:        `{destination}`\n"
        f"Available: `${available:.2f}`\n"
        f"Remaining: `${available - amount_usd:.2f}`\n\n"
        f"🔒 Trade-Only Mode: only realised profits may be withdrawn."
    )

    async def execute() -> str:
        result = hl.withdraw_profit(amount_usd, destination)
        return (
            f"✅ *PROFIT WITHDRAWN*\n"
            f"${amount_usd:.2f} → `{destination}`\n"
            f"Remaining profit: ${guard.ledger.available_profit():.2f}"
        )

    return await approval_queue.request("trade", summary, detail, execute)


# ── Prediction market bet approval ────────────────────────────────────────────

async def request_bet_approval(
    platform: str,
    market_id: str,
    question: str,
    side: str,
    price: float,
    size: float,
    execute_fn,
) -> str:
    """Route any prediction market bet through the approval queue."""
    if platform.lower() not in ALLOWED_BET_PLATFORMS:
        return (
            f"❌ *Platform not allowed*\n"
            f"`{platform}` is not supported. Betting is restricted to "
            f"**Polymarket** and **Kalshi** only."
        )
    summary = f"{platform.upper()} {side} on '{question[:40]}…'"
    detail  = (
        f"🎰 *{platform.upper()} BET*\n"
        f"Market: _{question}_\n"
        f"Side:   `{side}`\n"
        f"Price:  `{price}`\n"
        f"Size:   `{size}`\n"
        f"ID:     `{market_id}`"
    )
    return await approval_queue.request("bet", summary, detail, execute_fn)
