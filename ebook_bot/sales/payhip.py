"""Payhip integration — read product link from env."""
import os
from loguru import logger


def get_product_link() -> str:
    """Return the direct Payhip product purchase link."""
    link = os.getenv("PAYHIP_PRODUCT_LINK", "") or os.getenv("PAYHIP_STORE_URL", "")
    if not link:
        logger.debug("PAYHIP_PRODUCT_LINK not configured.")
    return link
