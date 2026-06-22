"""
Payhip integration.
Payhip does not have a public write API — this module provides helpers
for building your Payhip store link and checking webhook events.
"""
import os
from loguru import logger

PAYHIP_STORE_URL = os.getenv("PAYHIP_STORE_URL", "")  # e.g. https://payhip.com/YourStore
PAYHIP_PRODUCT_LINK = os.getenv("PAYHIP_PRODUCT_LINK", "")  # direct product URL


def get_product_link() -> str:
    """Return the direct Payhip product purchase link."""
    link = PAYHIP_PRODUCT_LINK or PAYHIP_STORE_URL
    if not link:
        logger.warning("PAYHIP_PRODUCT_LINK not configured")
    return link
