"""DEX trading via 1inch API v5/v6."""
import requests
from web3 import Web3
from loguru import logger
from config import cfg
from trading.wallet import get_web3, get_account, approve_token

# 1inch v6 router addresses per chain
ONEINCH_ROUTERS = {
    1: "0x111111125421cA6dc452d289314280a0f8842A65",    # Ethereum
    137: "0x111111125421cA6dc452d289314280a0f8842A65",  # Polygon
    56: "0x111111125421cA6dc452d289314280a0f8842A65",   # BSC
}

# Native token placeholder used by 1inch
NATIVE_TOKEN = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

BASE_URL = "https://api.1inch.dev/swap/v6.0"


def _headers() -> dict:
    return {"Authorization": f"Bearer {cfg.ONEINCH_API_KEY}", "Accept": "application/json"}


def get_quote(
    token_in: str,
    token_out: str,
    amount_wei: int,
    chain_id: int | None = None,
) -> dict:
    """Get a swap quote from 1inch."""
    chain_id = chain_id or cfg.chain_id
    url = f"{BASE_URL}/{chain_id}/quote"
    params = {
        "src": token_in,
        "dst": token_out,
        "amount": str(amount_wei),
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def build_swap_tx(
    token_in: str,
    token_out: str,
    amount_wei: int,
    slippage: float | None = None,
    chain_id: int | None = None,
) -> dict:
    """Build a swap transaction via 1inch."""
    chain_id = chain_id or cfg.chain_id
    slippage = slippage if slippage is not None else cfg.SLIPPAGE_PCT
    url = f"{BASE_URL}/{chain_id}/swap"
    params = {
        "src": token_in,
        "dst": token_out,
        "amount": str(amount_wei),
        "from": cfg.WALLET_ADDRESS,
        "slippage": slippage,
        "disableEstimate": False,
    }
    resp = requests.get(url, params=params, headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def execute_swap(
    token_in: str,
    token_out: str,
    amount_human: float,
    token_in_decimals: int = 18,
    chain: str | None = None,
) -> str:
    """Execute a token swap. Returns tx hash."""
    chain = chain or cfg.DEFAULT_CHAIN
    chain_id = cfg.CHAIN_IDS.get(chain, 137)
    w3 = get_web3(chain)
    account = get_account()

    amount_wei = int(amount_human * 10 ** token_in_decimals)
    router = ONEINCH_ROUTERS[chain_id]

    # Approve if not native
    if token_in.lower() != NATIVE_TOKEN:
        logger.info(f"Approving {amount_human} of {token_in} to 1inch router")
        approve_token(token_in, router, amount_wei, chain)

    logger.info(f"Building swap: {amount_human} {token_in} → {token_out}")
    swap_data = build_swap_tx(token_in, token_out, amount_wei, chain_id=chain_id)

    tx = swap_data["tx"]
    tx["nonce"] = w3.eth.get_transaction_count(account.address)
    tx["gas"] = int(tx.get("gas", 300_000) * 1.2)
    tx["gasPrice"] = w3.eth.gas_price
    tx["value"] = int(tx.get("value", 0))

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    logger.info(f"Swap tx sent: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        raise RuntimeError(f"Swap tx reverted: {tx_hash.hex()}")
    logger.success(f"Swap confirmed: {tx_hash.hex()}")
    return tx_hash.hex()
