"""
Platform fee collection — 0.02% of every trade notional value.

On every Hyperliquid trade the fee is calculated and sent to the
Creator's fee wallet via a Hyperliquid USD transfer. Fees are also
tracked in a local ledger (~/.bbc/fees.jsonl) for transparency.

Fee rate: 0.02%  (FEE_BPS = 2 basis points)
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from loguru import logger

# ── Constants ─────────────────────────────────────────────────────────────────

FEE_BPS: float  = 2.0          # basis points  (2 bps = 0.02%)
FEE_RATE: float = FEE_BPS / 10_000   # 0.0002

# Creator's fee collection wallet — receives every trade fee
FEE_WALLET: str = os.getenv(
    "FEE_WALLET_ADDRESS",
    "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",   # fallback placeholder
)

# Minimum fee to transfer (avoid dust transfers clogging the network)
MIN_FEE_USD: float = 0.10

# Local fee ledger
_BBC_DIR  = Path.home() / ".bbc"
_FEE_LOG  = _BBC_DIR / "fees.jsonl"


def calculate_fee(notional_usd: float) -> float:
    """Return the 0.02% fee in USD for a given trade notional."""
    return round(notional_usd * FEE_RATE, 6)


def collect_fee(coin: str, size: float, price: float, direction: str) -> dict:
    """
    Calculate and collect the platform fee for a completed trade.

    Args:
        coin:       e.g. "BTC"
        size:       position size in coin units
        price:      execution price in USD
        direction:  "long" | "short"

    Returns:
        Fee record dict.
    """
    notional  = size * price
    fee_usd   = calculate_fee(notional)
    tx_hash   = "skipped"
    status    = "pending"

    record = {
        "ts":        time.time(),
        "time":      time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "coin":      coin,
        "size":      size,
        "price":     price,
        "direction": direction,
        "notional":  round(notional, 4),
        "fee_usd":   fee_usd,
        "fee_bps":   FEE_BPS,
        "fee_wallet": FEE_WALLET,
        "tx_hash":   tx_hash,
        "status":    status,
    }

    if fee_usd >= MIN_FEE_USD:
        tx_hash, status = _transfer_fee(fee_usd, record)
        record["tx_hash"] = tx_hash
        record["status"]  = status

    _append_fee_log(record)

    if fee_usd >= MIN_FEE_USD:
        logger.info(
            f"Fee collected: ${fee_usd:.4f} ({FEE_BPS}bps of ${notional:.2f} "
            f"{direction} {size} {coin}) → {FEE_WALLET[:10]}…"
        )
    else:
        logger.debug(f"Fee ${fee_usd:.6f} below min ${MIN_FEE_USD} — logged, not transferred")

    return record


def _transfer_fee(fee_usd: float, record: dict) -> tuple[str, str]:
    """
    Send fee_usd to FEE_WALLET via Hyperliquid USD transfer.
    Returns (tx_hash, status).
    """
    try:
        from trading.hyperliquid import _exchange, TESTNET
        exc = _exchange(TESTNET)
        # Hyperliquid usd_transfer sends USDC from the user's perp account
        result = exc.usd_transfer(fee_usd, FEE_WALLET)
        if result.get("status") == "ok":
            tx = result.get("response", {}).get("data", {}).get("statuses", [{}])[0]
            tx_hash = tx.get("filled", {}).get("oid") or tx.get("error") or str(result)
            return str(tx_hash), "sent"
        return str(result), "failed"
    except AttributeError:
        # usd_transfer may not be available in older SDK versions
        return _transfer_via_l1_action(fee_usd)
    except Exception as e:
        logger.error(f"Fee transfer failed: {e}")
        return f"error:{e}", "failed"


def _transfer_via_l1_action(fee_usd: float) -> tuple[str, str]:
    """Fallback: raw Hyperliquid L1 USD transfer action."""
    try:
        import eth_account
        from eth_account.signers.local import LocalAccount
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils import constants
        from config import cfg
        import time, json
        from web3 import Web3

        account: LocalAccount = eth_account.Account.from_key(cfg.WALLET_PRIVATE_KEY)
        base_url = constants.TESTNET_API_URL if False else constants.MAINNET_API_URL

        # Use the SDK's built-in transfer helper
        exc = Exchange(account, base_url)
        result = exc.usd_class_transfer(fee_usd, True, FEE_WALLET)
        return str(result), "sent" if result.get("status") == "ok" else "failed"
    except Exception as e:
        logger.error(f"L1 fee transfer fallback failed: {e}")
        return f"fallback_error:{e}", "failed"


def _append_fee_log(record: dict):
    """Append fee record to local JSONL ledger."""
    _BBC_DIR.mkdir(parents=True, exist_ok=True)
    with open(_FEE_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")


# ── Ledger queries ─────────────────────────────────────────────────────────────

def get_fee_ledger(limit: int = 100) -> list[dict]:
    """Return most recent fee records from local ledger."""
    if not _FEE_LOG.exists():
        return []
    lines = _FEE_LOG.read_text().strip().splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except Exception:
            pass
    return list(reversed(records))


def get_total_fees_collected() -> float:
    """Return total USD fees collected (sent successfully)."""
    records = get_fee_ledger(limit=10_000)
    return sum(r.get("fee_usd", 0) for r in records if r.get("status") == "sent")
