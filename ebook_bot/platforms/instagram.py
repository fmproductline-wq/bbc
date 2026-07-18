"""Instagram posting via Meta Graph API (Instagram Graph API)."""
import os
import requests
from loguru import logger

GRAPH = "https://graph.facebook.com/v19.0"


def post(caption: str, image_url: str = "") -> dict | None:
    """Post a photo to Instagram. image_url must be publicly accessible."""
    token      = os.getenv("META_ACCESS_TOKEN", "")
    account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
    if not token or not account_id:
        logger.warning("Instagram credentials not configured, skipping.")
        return None
    if not image_url:
        logger.warning("Instagram requires an image URL (EBOOK_COVER_IMAGE_URL); skipping.")
        return None

    try:
        # Step 1: create media container
        r1 = requests.post(
            f"{GRAPH}/{account_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=15,
        )
        r1.raise_for_status()
        container_id = r1.json().get("id")
        if not container_id:
            logger.error("Instagram: no container ID returned")
            return None

        # Step 2: publish
        r2 = requests.post(
            f"{GRAPH}/{account_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
            timeout=15,
        )
        r2.raise_for_status()
        media_id = r2.json().get("id", "unknown")
        logger.success(f"Instagram: posted {media_id}")
        return {"platform": "instagram", "id": media_id}
    except requests.HTTPError as e:
        logger.error(f"Instagram post failed: {e}")
        return None
