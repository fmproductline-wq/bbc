"""
Hyperliquid perpetuals trading via hyperliquid-python-sdk.

Uses your Rabby wallet private key to sign orders on Hyperliquid's
decentralised perpetuals exchange (no CEX account needed).

Docs: https://hyperliquid.gitbook.io/hyperliquid-docs
SDK:  https://github.com/hyperliquid-dex/hyperliquid-python-sdk
"""
import eth_account
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from loguru import logger
from config import cfg


# ── Client singletons ────────────────────────────────────────────────────────

def _account() -> LocalAccount:
    return eth_account.Account.from_key(cfg.WALLET_PRIVATE_KEY)


def _exchange(testnet: bool = False) -> Exchange:
    base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
    return Exchange(_account(), base_url)


def _info(testnet: bool = False) -> Info:
    base_url = constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL
    return Info(base_url, skip_ws=True)


TESTNET: bool = False   # flip to True while testing


# ── Account info ─────────────────────────────────────────────────────────────

def get_account_summary() -> dict:
    """Return margin summary, positions, and open orders."""
    info = _info(TESTNET)
    address = _account().address
    state = info.user_state(address)
    margin = state.get("marginSummary", {})
    positions = [
        {
            "coin": p["position"]["coin"],
            "side": "LONG" if float(p["position"]["szi"]) > 0 else "SHORT",
            "size": abs(float(p["position"]["szi"])),
            "entry_px": p["position"].get("entryPx"),
            "unrealized_pnl": p["position"].get("unrealizedPnl"),
            "leverage": p["position"].get("leverage", {}).get("value"),
        }
        for p in state.get("assetPositions", [])
        if float(p["position"]["szi"]) != 0
    ]
    return {
        "account_value": margin.get("accountValue"),
        "total_margin_used": margin.get("totalMarginUsed"),
        "total_ntl_pos": margin.get("totalNtlPos"),
        "positions": positions,
    }


def get_open_orders() -> list[dict]:
    info = _info(TESTNET)
    return info.open_orders(_account().address)


def get_all_mids() -> dict[str, float]:
    """Return mid prices for all perp markets {coin: price}."""
    info = _info(TESTNET)
    mids = info.all_mids()
    return {k: float(v) for k, v in mids.items()}


def get_meta() -> dict:
    """Return universe metadata (all tradeable coins, max leverage, etc.)."""
    info = _info(TESTNET)
    return info.meta()


# ── Order execution ──────────────────────────────────────────────────────────

def market_open(
    coin: str,
    is_buy: bool,
    size: float,
    slippage: float = 0.05,
) -> dict:
    """
    Open a market order on Hyperliquid perps.

    Args:
        coin:      e.g. "BTC", "ETH", "SOL"
        is_buy:    True = long, False = short
        size:      position size in coin units
        slippage:  max acceptable slippage (0.05 = 5%)
    """
    exc = _exchange(TESTNET)
    logger.info(f"Hyperliquid market {'BUY' if is_buy else 'SELL'} {size} {coin}")
    result = exc.market_open(coin, is_buy, size, slippage=slippage)
    logger.info(f"Order result: {result}")
    _check_result(result)
    return result


def market_close(
    coin: str,
    size: float | None = None,
    slippage: float = 0.05,
) -> dict:
    """
    Close an existing position (or partial close if size provided).
    If size is None, closes the full position.
    """
    exc = _exchange(TESTNET)
    if size is not None:
        # Determine current side to flip it
        summary = get_account_summary()
        pos = next((p for p in summary["positions"] if p["coin"] == coin), None)
        if not pos:
            raise ValueError(f"No open position for {coin}")
        is_buy = pos["side"] == "SHORT"  # close by going opposite direction
        result = exc.market_open(coin, is_buy, size, slippage=slippage, reduce_only=True)
    else:
        result = exc.market_close(coin, slippage=slippage)
    logger.info(f"Close result: {result}")
    _check_result(result)
    return result


def limit_open(
    coin: str,
    is_buy: bool,
    size: float,
    price: float,
    reduce_only: bool = False,
) -> dict:
    """Place a limit order."""
    exc = _exchange(TESTNET)
    order_type = {"limit": {"tif": "Gtc"}}
    logger.info(f"Limit {'BUY' if is_buy else 'SELL'} {size} {coin} @ {price}")
    result = exc.order(coin, is_buy, size, price, order_type, reduce_only=reduce_only)
    logger.info(f"Limit order result: {result}")
    _check_result(result)
    return result


def set_leverage(coin: str, leverage: int, is_cross: bool = True) -> dict:
    """Set leverage for a coin (cross or isolated margin)."""
    exc = _exchange(TESTNET)
    result = exc.update_leverage(leverage, coin, is_cross)
    logger.info(f"Leverage set: {coin} {leverage}x {'cross' if is_cross else 'isolated'}")
    return result


def cancel_order(coin: str, oid: int) -> dict:
    exc = _exchange(TESTNET)
    return exc.cancel(coin, oid)


def set_stop_loss(coin: str, trigger_price: float, size: float) -> dict:
    """Place a stop-market order (reduce-only) as stop loss."""
    exc = _exchange(TESTNET)
    summary = get_account_summary()
    pos = next((p for p in summary["positions"] if p["coin"] == coin), None)
    if not pos:
        raise ValueError(f"No open position for {coin}")
    is_buy = pos["side"] == "SHORT"
    order_type = {"trigger": {"triggerPx": trigger_price, "isMarket": True, "tpsl": "sl"}}
    result = exc.order(coin, is_buy, size, trigger_price, order_type, reduce_only=True)
    logger.info(f"Stop-loss set: {coin} @ {trigger_price}")
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_result(result: dict):
    status = result.get("status")
    if status != "ok":
        raise RuntimeError(f"Hyperliquid order failed: {result}")


def coin_from_signal(symbol: str) -> str:
    """
    Convert a TradingView symbol like 'BTCUSDT' or 'BTC/USDT.P'
    to a Hyperliquid coin name like 'BTC'.
    """
    for suffix in ["USDT.P", "USDT", "USD", "/USDT", "/USD"]:
        symbol = symbol.replace(suffix, "")
    return symbol.strip().upper()
