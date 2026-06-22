"""
Facebook Page posting via Meta Graph API.
"""
import requests
from loguru import logger
from ..config import META_ACCESS_TOKEN, FACEBOOK_PAGE_ID

GRAPH = "https://graph.facebook.com/v19.0"


def post(text: str, link: str = "") -> dict | None:
    """Publish a post on the configured Facebook Page."""
    if not META_ACCESS_TOKEN or not FACEBOOK_PAGE_ID:
        logger.warning("Facebook credentials not configured, skipping.")
        return None

    params = {
        "message": text,
        "access_token": META_ACCESS_TOKEN,
    }
    if link:
        params["link"] = link

    try:
        r = requests.post(f"{GRAPH}/{FACEBOOK_PAGE_ID}/feed", data=params, timeout=15)
        r.raise_for_status()
        post_id = r.json().get("id", "unknown")
        logger.success(f"Facebook: posted {post_id}")
        return {"platform": "facebook", "id": post_id}
    except requests.HTTPError as e:
        logger.error(f"Facebook post failed: {e} — {r.text}")
        return None
