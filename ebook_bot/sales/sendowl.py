"""
SendOwl API integration.
Docs: https://www.sendowl.com/developers/api/introduction
"""
import requests
from loguru import logger
from ..config import SENDOWL_API_KEY, SENDOWL_API_SECRET, SENDOWL_PRODUCT_ID

BASE = "https://www.sendowl.com/api/v1"


def _auth() -> tuple:
    return (SENDOWL_API_KEY, SENDOWL_API_SECRET)


def get_product_link() -> str:
    """Return the buy-now URL for the SendOwl product."""
    if not SENDOWL_API_KEY or not SENDOWL_PRODUCT_ID:
        return ""
    r = requests.get(
        f"{BASE}/products/{SENDOWL_PRODUCT_ID}",
        auth=_auth(),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if r.status_code != 200:
        logger.warning(f"SendOwl product fetch failed: {r.text}")
        return ""
    data = r.json()
    return data.get("product", {}).get("sales_page_url", "")


def get_orders() -> list[dict]:
    """Fetch recent orders from SendOwl."""
    if not SENDOWL_API_KEY:
        return []
    r = requests.get(
        f"{BASE}/orders",
        auth=_auth(),
        headers={"Accept": "application/json"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()
