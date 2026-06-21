"""Polymarket integration via CLOB API."""
import requests
import hmac
import hashlib
import base64
import time
import json
from loguru import logger
from config import cfg

CLOB_BASE = "https://clob.polymarket.com"
GAMMA_BASE = "https://gamma-api.polymarket.com"


def _auth_headers(method: str, path: str, body: str = "") -> dict:
    """Generate L1 auth headers for Polymarket CLOB."""
    ts = str(int(time.time()))
    msg = ts + method.upper() + path + body
    sig = hmac.new(
        cfg.POLYMARKET_API_SECRET.encode(),
        msg.encode(),
        hashlib.sha256,
    ).digest()
    sig_b64 = base64.b64encode(sig).decode()
    return {
        "POLY-API-KEY": cfg.POLYMARKET_API_KEY,
        "POLY-SIGNATURE": sig_b64,
        "POLY-TIMESTAMP": ts,
        "POLY-PASSPHRASE": cfg.POLYMARKET_API_PASSPHRASE,
        "Content-Type": "application/json",
    }


def search_markets(query: str, limit: int = 5) -> list[dict]:
    """Search Polymarket markets by keyword."""
    resp = requests.get(
        f"{GAMMA_BASE}/markets",
        params={"q": query, "limit": limit, "active": True},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    markets = data if isinstance(data, list) else data.get("markets", [])
    return [
        {
            "id": m.get("id"),
            "question": m.get("question"),
            "yes_price": m.get("outcomePrices", ["?"])[0] if m.get("outcomePrices") else "?",
            "no_price": m.get("outcomePrices", ["?", "?"])[1] if m.get("outcomePrices") else "?",
            "volume": m.get("volume"),
            "end_date": m.get("endDate"),
        }
        for m in markets[:limit]
    ]


def get_orderbook(token_id: str) -> dict:
    """Get current orderbook for a market token."""
    resp = requests.get(f"{CLOB_BASE}/book", params={"token_id": token_id}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def place_order(
    token_id: str,
    side: str,       # "BUY" | "SELL"
    price: float,    # 0.0–1.0
    size: float,     # USDC amount
) -> dict:
    """Place a limit order on Polymarket CLOB."""
    path = "/order"
    body = json.dumps({
        "token_id": token_id,
        "side": side.upper(),
        "price": price,
        "size": size,
        "type": "GTC",
    })
    headers = _auth_headers("POST", path, body)
    resp = requests.post(f"{CLOB_BASE}{path}", data=body, headers=headers, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    logger.info(f"Polymarket order placed: {result}")
    return result


def get_positions() -> list[dict]:
    """Get open positions on Polymarket."""
    path = "/positions"
    headers = _auth_headers("GET", path)
    resp = requests.get(f"{CLOB_BASE}{path}", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()
