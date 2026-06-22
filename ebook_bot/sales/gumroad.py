"""
Gumroad API integration.
Docs: https://app.gumroad.com/api
"""
import requests
from loguru import logger
from ..config import GUMROAD_ACCESS_TOKEN, GUMROAD_PRODUCT_ID

BASE = "https://api.gumroad.com/v2"


def _headers() -> dict:
    return {"Authorization": f"Bearer {GUMROAD_ACCESS_TOKEN}"}


def get_product_link() -> str:
    """Return the short URL for the configured Gumroad product."""
    if not GUMROAD_ACCESS_TOKEN or not GUMROAD_PRODUCT_ID:
        return ""
    r = requests.get(f"{BASE}/products/{GUMROAD_PRODUCT_ID}", headers=_headers(), timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("product", {}).get("short_url", "")


def get_sales() -> list[dict]:
    """Fetch recent sales from Gumroad."""
    if not GUMROAD_ACCESS_TOKEN:
        return []
    r = requests.get(f"{BASE}/sales", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json().get("sales", [])


def update_product_description(description: str) -> bool:
    """Update the product description on Gumroad."""
    if not GUMROAD_ACCESS_TOKEN or not GUMROAD_PRODUCT_ID:
        return False
    r = requests.put(
        f"{BASE}/products/{GUMROAD_PRODUCT_ID}",
        headers=_headers(),
        data={"description": description},
        timeout=15,
    )
    success = r.status_code == 200
    if not success:
        logger.warning(f"Gumroad update failed: {r.text}")
    return success


def enable_product() -> bool:
    """Enable (unpublish → publish) the product."""
    if not GUMROAD_ACCESS_TOKEN or not GUMROAD_PRODUCT_ID:
        return False
    r = requests.put(
        f"{BASE}/products/{GUMROAD_PRODUCT_ID}/enable",
        headers=_headers(),
        timeout=15,
    )
    return r.status_code == 200
