"""Gumroad API integration. Docs: https://app.gumroad.com/api"""
import os
import requests
from loguru import logger

BASE = "https://api.gumroad.com/v2"


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('GUMROAD_ACCESS_TOKEN', '')}"}


def get_product_link() -> str:
    """Return the short URL for the configured Gumroad product."""
    token      = os.getenv("GUMROAD_ACCESS_TOKEN", "")
    product_id = os.getenv("GUMROAD_PRODUCT_ID", "")
    if not token or not product_id:
        return ""
    try:
        r = requests.get(f"{BASE}/products/{product_id}", headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json().get("product", {}).get("short_url", "")
    except requests.RequestException as e:
        logger.warning(f"Gumroad product fetch failed: {e}")
        return ""


def get_sales() -> list[dict]:
    """Fetch recent sales from Gumroad."""
    if not os.getenv("GUMROAD_ACCESS_TOKEN"):
        return []
    try:
        r = requests.get(f"{BASE}/sales", headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json().get("sales", [])
    except requests.RequestException as e:
        logger.warning(f"Gumroad sales fetch failed: {e}")
        return []


def update_product_description(description: str) -> bool:
    """Update the product description on Gumroad."""
    token      = os.getenv("GUMROAD_ACCESS_TOKEN", "")
    product_id = os.getenv("GUMROAD_PRODUCT_ID", "")
    if not token or not product_id:
        return False
    try:
        r = requests.put(f"{BASE}/products/{product_id}", headers=_headers(),
                         data={"description": description}, timeout=15)
        return r.status_code == 200
    except requests.RequestException as e:
        logger.warning(f"Gumroad update failed: {e}")
        return False
