"""LinkedIn posting via LinkedIn Marketing API v2 (UGC Posts)."""
import os
import requests
from loguru import logger

BASE = "https://api.linkedin.com/v2"


def post(text: str) -> dict | None:
    """Publish a text post to the authenticated user's LinkedIn feed."""
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    urn   = os.getenv("LINKEDIN_PERSON_URN", "")
    if not token or not urn:
        logger.warning("LinkedIn credentials not configured, skipping.")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    try:
        r = requests.post(f"{BASE}/ugcPosts", json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        post_id = r.headers.get("x-restli-id", "unknown")
        logger.success(f"LinkedIn: posted {post_id}")
        return {"platform": "linkedin", "id": post_id}
    except requests.HTTPError as e:
        logger.error(f"LinkedIn post failed: {e} — {r.text}")
        return None
