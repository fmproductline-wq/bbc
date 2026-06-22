"""
Pinterest Pin creation via Pinterest API v5.
"""
import requests
from loguru import logger
from ..config import PINTEREST_ACCESS_TOKEN, PINTEREST_BOARD_ID, EBOOK

BASE = "https://api.pinterest.com/v5"


def post(description: str, link: str, image_url: str = "") -> dict | None:
    """Create a Pinterest Pin."""
    if not PINTEREST_ACCESS_TOKEN or not PINTEREST_BOARD_ID:
        logger.warning("Pinterest credentials not configured, skipping.")
        return None

    image_url = image_url or EBOOK.get("cover_image_url", "")
    if not image_url:
        logger.warning("Pinterest requires an image URL; skipping.")
        return None

    headers = {
        "Authorization": f"Bearer {PINTEREST_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "board_id": PINTEREST_BOARD_ID,
        "title": EBOOK.get("title", ""),
        "description": description,
        "link": link,
        "media_source": {
            "source_type": "image_url",
            "url": image_url,
        },
    }
    try:
        r = requests.post(f"{BASE}/pins", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        pin_id = r.json().get("id", "unknown")
        logger.success(f"Pinterest: created pin {pin_id}")
        return {"platform": "pinterest", "id": pin_id}
    except requests.HTTPError as e:
        logger.error(f"Pinterest post failed: {e} — {r.text}")
        return None
