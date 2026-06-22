"""
Instagram posting via Meta Graph API (Instagram Graph API).
Requires a Business or Creator account linked to a Facebook Page.
Images must be hosted on a public URL.
"""
import requests
from loguru import logger
from ..config import META_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID

GRAPH = "https://graph.facebook.com/v19.0"


def post(caption: str, image_url: str = "") -> dict | None:
    """Post a photo (or text-only carousel placeholder) to Instagram."""
    if not META_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        logger.warning("Instagram credentials not configured, skipping.")
        return None
    if not image_url:
        logger.warning("Instagram requires an image URL; skipping post.")
        return None

    try:
        # Step 1: create media container
        container_r = requests.post(
            f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": META_ACCESS_TOKEN,
            },
            timeout=15,
        )
        container_r.raise_for_status()
        container_id = container_r.json().get("id")

        # Step 2: publish
        pub_r = requests.post(
            f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
            data={"creation_id": container_id, "access_token": META_ACCESS_TOKEN},
            timeout=15,
        )
        pub_r.raise_for_status()
        media_id = pub_r.json().get("id", "unknown")
        logger.success(f"Instagram: posted {media_id}")
        return {"platform": "instagram", "id": media_id}
    except requests.HTTPError as e:
        logger.error(f"Instagram post failed: {e}")
        return None
