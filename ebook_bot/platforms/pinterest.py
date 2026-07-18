"""Pinterest Pin creation via Pinterest API v5."""
import os
import requests
from loguru import logger
from ..config import get_ebook

BASE = "https://api.pinterest.com/v5"


def post(description: str, link: str, image_url: str = "") -> dict | None:
    """Create a Pinterest Pin."""
    token    = os.getenv("PINTEREST_ACCESS_TOKEN", "")
    board_id = os.getenv("PINTEREST_BOARD_ID", "")
    if not token or not board_id:
        logger.warning("Pinterest credentials not configured, skipping.")
        return None

    ebook = get_ebook()
    image_url = image_url or ebook.get("cover_image_url", "")
    if not image_url:
        logger.warning("Pinterest requires an image URL (EBOOK_COVER_IMAGE_URL); skipping.")
        return None

    payload = {
        "board_id": board_id,
        "title": ebook.get("title", ""),
        "description": description,
        "link": link,
        "media_source": {"source_type": "image_url", "url": image_url},
    }
    try:
        r = requests.post(
            f"{BASE}/pins",
            json=payload,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        pin_id = r.json().get("id", "unknown")
        logger.success(f"Pinterest: created pin {pin_id}")
        return {"platform": "pinterest", "id": pin_id}
    except requests.HTTPError as e:
        logger.error(f"Pinterest post failed: {e} — {r.text}")
        return None
