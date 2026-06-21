"""Trade execution logic driven by TradingView signals."""
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.wallet import get_balance_native
from trading.dex import execute_swap, get_quote, NATIVE_TOKEN
from trading.state import state, Position
import time


# Common token addresses per chain (add more as needed)
TOKENS = {
    "polygon": {
        "USDC": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "WMATIC": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "WETH": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",
        "WBTC": "0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6",
    },
    "ethereum": {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    },
    "bsc": {
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "WETH": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",
    },
}


def resolve_token(symbol_or_addr: str, chain: str) -> str:
    """Return token contract address from symbol or pass-through if already an address."""
    if symbol_or_addr.startswith("0x"):
        return symbol_or_addr
    chain_tokens = TOKENS.get(chain, {})
    addr = chain_tokens.get(symbol_or_addr.upper())
    if not addr:
        raise ValueError(f"Unknown token '{symbol_or_addr}' on {chain}. Pass a contract address instead.")
    return addr


def _trade_amount_native(chain: str) -> float:
    """Calculate how much native token to use based on MAX_TRADE_PCT."""
    balance = get_balance_native(chain)
    return balance * (cfg.MAX_TRADE_PCT / 100)


async def handle_signal(signal: TVSignal) -> str:
    """Process a TradingView signal and execute trade if auto_trade is on."""
    state.log_signal(signal.to_log())

    if not state.auto_trade:
        msg = f"Signal received ({signal.indicator} {signal.action} {signal.symbol} @ {signal.price}) — auto-trade is OFF"
        logger.info(msg)
        return msg

    chain = signal.chain or cfg.DEFAULT_CHAIN

    try:
        if signal.is_buy():
            return await _open_position(signal, chain)
        elif signal.is_sell():
            return await _close_position(signal, chain)
        else:
            return f"Unknown action: {signal.action}"
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        return f"Trade failed: {e}"


async def _open_position(signal: TVSignal, chain: str) -> str:
    # Determine tokens
    if signal.token_in and signal.token_out:
        token_in = resolve_token(signal.token_in, chain)
        token_out = resolve_token(signal.token_out, chain)
    else:
        # Default: spend native token to buy WBTC (override via signal)
        token_in = NATIVE_TOKEN
        chain_tokens = TOKENS.get(chain, {})
        token_out = chain_tokens.get("WBTC") or chain_tokens.get("WETH") or ""
        if not token_out:
            return "No default token_out configured for this chain"

    amount = signal.amount_usd or _trade_amount_native(chain)
    if amount <= 0:
        return "Insufficient balance for trade"

    logger.info(f"BUY signal: spending {amount} native → {token_out} on {chain}")
    tx = execute_swap(token_in, token_out, amount, chain=chain)

    stop = signal.price * (1 - cfg.STOP_LOSS_PCT / 100)
    pos = Position(
        token_in=token_in,
        token_out=token_out,
        amount_in=amount,
        amount_out=0,
        entry_price=signal.price,
        stop_loss=stop,
        chain=chain,
        tx_hash=tx,
    )
    state.positions.append(pos)
    return f"✅ BUY executed on {chain}\nTx: {tx}\nEntry: {signal.price}\nStop: {stop:.4f}"


async def _close_position(signal: TVSignal, chain: str) -> str:
    open_pos = state.open_positions()
    if not open_pos:
        return "No open positions to close"

    results = []
    for pos in open_pos:
        try:
            amount = pos.amount_out if pos.amount_out else _trade_amount_native(chain)
            tx = execute_swap(pos.token_out, pos.token_in, amount, chain=pos.chain)
            pos.closed = True
            pos.close_tx = tx
            pnl_pct = ((signal.price - pos.entry_price) / pos.entry_price) * 100
            pos.pnl = pnl_pct
            results.append(f"✅ CLOSED position\nTx: {tx}\nPnL: {pnl_pct:+.2f}%")
        except Exception as e:
            results.append(f"❌ Failed to close: {e}")

    return "\n".join(results)
