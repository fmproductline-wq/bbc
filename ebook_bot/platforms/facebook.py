"""Facebook Page posting via Meta Graph API."""
import os
import requests
from loguru import logger

GRAPH = "https://graph.facebook.com/v19.0"


def post(text: str, link: str = "") -> dict | None:
    """Publish a post on the configured Facebook Page."""
    token   = os.getenv("META_ACCESS_TOKEN", "")
    page_id = os.getenv("FACEBOOK_PAGE_ID", "")
    if not token or not page_id:
        logger.warning("Facebook credentials not configured, skipping.")
        return None

    params = {"message": text, "access_token": token}
    if link:
        params["link"] = link
    try:
        r = requests.post(f"{GRAPH}/{page_id}/feed", data=params, timeout=15)
        r.raise_for_status()
        post_id = r.json().get("id", "unknown")
        logger.success(f"Facebook: posted {post_id}")
        return {"platform": "facebook", "id": post_id}
    except requests.HTTPError as e:
        logger.error(f"Facebook post failed: {e} — {r.text}")
        return None
