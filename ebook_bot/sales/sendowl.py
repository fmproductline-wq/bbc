"""SendOwl API integration. Docs: https://www.sendowl.com/developers/api/introduction"""
import os
import requests
from loguru import logger

BASE = "https://www.sendowl.com/api/v1"


def _auth() -> tuple:
    return (os.getenv("SENDOWL_API_KEY", ""), os.getenv("SENDOWL_API_SECRET", ""))


def get_product_link() -> str:
    """Return the buy-now URL for the SendOwl product."""
    product_id = os.getenv("SENDOWL_PRODUCT_ID", "")
    if not os.getenv("SENDOWL_API_KEY") or not product_id:
        return ""
    try:
        r = requests.get(
            f"{BASE}/products/{product_id}",
            auth=_auth(),
            headers={"Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("product", {}).get("sales_page_url", "")
    except requests.RequestException as e:
        logger.warning(f"SendOwl product fetch failed: {e}")
        return ""


def get_orders() -> list[dict]:
    """Fetch recent orders from SendOwl."""
    if not os.getenv("SENDOWL_API_KEY"):
        return []
    try:
        r = requests.get(
            f"{BASE}/orders",
            auth=_auth(),
            headers={"Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        # API returns a list of {"order": {...}} wrappers or a plain list
        if isinstance(data, list):
            return [item.get("order", item) for item in data]
        return data.get("orders", [])
    except requests.RequestException as e:
        logger.warning(f"SendOwl orders fetch failed: {e}")
        return []
