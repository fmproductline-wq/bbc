"""Kalshi prediction market integration."""
import requests
from loguru import logger
from config import cfg

BASE = cfg.KALSHI_BASE_URL
_session_token: str = ""


def _get_headers(authed: bool = True) -> dict:
    h = {"Content-Type": "application/json"}
    if authed and _session_token:
        h["Authorization"] = f"Bearer {_session_token}"
    elif authed and cfg.KALSHI_API_KEY:
        h["Authorization"] = f"Bearer {cfg.KALSHI_API_KEY}"
    return h


def login() -> bool:
    """Authenticate and cache session token."""
    global _session_token
    resp = requests.post(
        f"{BASE}/log_in",
        json={"email": cfg.KALSHI_EMAIL, "password": cfg.KALSHI_PASSWORD},
        timeout=10,
    )
    if resp.status_code == 200:
        _session_token = resp.json().get("token", "")
        logger.info("Kalshi login successful")
        return True
    logger.error(f"Kalshi login failed: {resp.text}")
    return False


def search_markets(query: str = "", limit: int = 5) -> list[dict]:
    """Search Kalshi markets."""
    params = {"limit": limit}
    if query:
        params["search"] = query
    resp = requests.get(f"{BASE}/markets", params=params, headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    markets = resp.json().get("markets", [])
    return [
        {
            "ticker": m.get("ticker"),
            "title": m.get("title"),
            "yes_bid": m.get("yes_bid"),
            "yes_ask": m.get("yes_ask"),
            "no_bid": m.get("no_bid"),
            "no_ask": m.get("no_ask"),
            "close_time": m.get("close_time"),
            "volume": m.get("volume"),
        }
        for m in markets
    ]


def get_market(ticker: str) -> dict:
    resp = requests.get(f"{BASE}/markets/{ticker}", headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("market", {})


def place_order(
    ticker: str,
    side: str,       # "yes" | "no"
    action: str,     # "buy" | "sell"
    count: int,      # number of contracts
    price: int,      # cents (1–99)
    order_type: str = "limit",
) -> dict:
    """Place an order on Kalshi."""
    body = {
        "ticker": ticker,
        "client_order_id": f"bot_{ticker}_{int(__import__('time').time())}",
        "type": order_type,
        "action": action,
        "side": side,
        "count": count,
        "no_price" if side == "no" else "yes_price": price,
    }
    resp = requests.post(f"{BASE}/portfolio/orders", json=body, headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    result = resp.json()
    logger.info(f"Kalshi order placed: {result}")
    return result


def get_portfolio() -> dict:
    resp = requests.get(f"{BASE}/portfolio/balance", headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_open_positions() -> list[dict]:
    resp = requests.get(f"{BASE}/portfolio/positions", headers=_get_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json().get("market_positions", [])
