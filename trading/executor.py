"""Trade execution logic driven by TradingView signals — uses Hyperliquid perps."""
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.state import state, Position
from trading import hyperliquid as hl
from trading.fees import collect_fee
import time


def _position_size(coin: str) -> float:
    """
    Calculate position size in coin units based on MAX_TRADE_PCT of account value.
    Falls back to a minimum size if account value is unavailable.
    """
    try:
        summary = hl.get_account_summary()
        account_value = float(summary.get("account_value") or 0)
        if account_value <= 0:
            return 0.0
        mids = hl.get_all_mids()
        price = mids.get(coin, 0)
        if price <= 0:
            return 0.0
        usd_to_spend = account_value * (cfg.MAX_TRADE_PCT / 100)
        return round(usd_to_spend / price, 6)
    except Exception as e:
        logger.error(f"Position size calculation failed: {e}")
        return 0.0


async def handle_signal(signal: TVSignal) -> str:
    """Process a TradingView signal and execute Hyperliquid perp trade if auto_trade is on."""
    state.log_signal(signal.to_log())

    coin = hl.coin_from_signal(signal.symbol)

    if not state.auto_trade:
        msg = (
            f"Signal received ({signal.indicator} {signal.action} {coin} @ {signal.price}) "
            f"— auto-trade is OFF"
        )
        logger.info(msg)
        return msg

    try:
        if signal.is_buy():
            return await _open_long(signal, coin)
        elif signal.is_sell():
            return await _close_or_short(signal, coin)
        else:
            return f"Unknown action: {signal.action}"
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        return f"Trade failed: {e}"


async def _open_long(signal: TVSignal, coin: str) -> str:
    size = _position_size(coin)
    if size <= 0:
        return f"❌ Cannot calculate position size for {coin} — check account balance"

    logger.info(f"Opening LONG {size} {coin} on Hyperliquid @ ~{signal.price}")
    result = hl.market_open(coin, is_buy=True, size=size)

    stop = signal.price * (1 - cfg.STOP_LOSS_PCT / 100)
    try:
        hl.set_stop_loss(coin, stop, size)
    except Exception as e:
        logger.warning(f"Stop-loss order failed (position still open): {e}")

    pos = Position(
        token_in="USD",
        token_out=coin,
        amount_in=size * signal.price,
        amount_out=size,
        entry_price=signal.price,
        stop_loss=stop,
        chain="hyperliquid",
        tx_hash=str(result),
        opened_at=time.time(),
    )
    state.positions.append(pos)

    # Collect 0.02% platform fee
    try:
        fee = collect_fee(coin, size, signal.price, "long")
        fee_str = f"\nFee: ${fee['fee_usd']:.4f} (0.02%)"
    except Exception as e:
        logger.warning(f"Fee collection failed: {e}")
        fee_str = ""

    return (
        f"✅ LONG opened: {size} {coin} on Hyperliquid\n"
        f"Entry: ${signal.price:,.4f}\n"
        f"Stop: ${stop:,.4f}{fee_str}"
    )


async def _close_or_short(signal: TVSignal, coin: str) -> str:
    open_pos = [p for p in state.open_positions() if p.token_out == coin]

    if open_pos:
        # Close existing long
        results = []
        for pos in open_pos:
            try:
                hl.market_close(coin)
                pnl_pct = ((signal.price - pos.entry_price) / pos.entry_price) * 100
                pos.closed = True
                pos.pnl = pnl_pct
                # Collect 0.02% fee on the closed notional
                try:
                    fee = collect_fee(coin, pos.amount_out, signal.price, "close")
                    fee_str = f"\nFee: ${fee['fee_usd']:.4f} (0.02%)"
                except Exception:
                    fee_str = ""
                results.append(
                    f"✅ CLOSED {coin} @ ${signal.price:,.4f}\n"
                    f"PnL: {pnl_pct:+.2f}%{fee_str}"
                )
            except Exception as e:
                results.append(f"❌ Close failed for {coin}: {e}")
        return "\n".join(results)

    # No existing long — open a short
    size = _position_size(coin)
    if size <= 0:
        return f"❌ Cannot calculate position size for {coin}"

    logger.info(f"Opening SHORT {size} {coin} on Hyperliquid @ ~{signal.price}")
    result = hl.market_open(coin, is_buy=False, size=size)

    stop = signal.price * (1 + cfg.STOP_LOSS_PCT / 100)
    try:
        hl.set_stop_loss(coin, stop, size)
    except Exception as e:
        logger.warning(f"Stop-loss order failed: {e}")

    pos = Position(
        token_in="USD",
        token_out=coin,
        amount_in=size * signal.price,
        amount_out=size,
        entry_price=signal.price,
        stop_loss=stop,
        chain="hyperliquid",
        tx_hash=str(result),
        opened_at=time.time(),
    )
    state.positions.append(pos)

    # Collect 0.02% platform fee
    try:
        fee = collect_fee(coin, size, signal.price, "short")
        fee_str = f"\nFee: ${fee['fee_usd']:.4f} (0.02%)"
    except Exception as e:
        logger.warning(f"Fee collection failed: {e}")
        fee_str = ""

    return (
        f"✅ SHORT opened: {size} {coin} on Hyperliquid\n"
        f"Entry: ${signal.price:,.4f}\n"
        f"Stop: ${stop:,.4f}{fee_str}"
    )
