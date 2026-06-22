"""
LinkedIn posting via LinkedIn Marketing API v2 (UGC Posts).
"""
import requests
from loguru import logger
from ..config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN

BASE = "https://api.linkedin.com/v2"


def post(text: str) -> dict | None:
    """Publish a text post to the authenticated user's LinkedIn feed."""
    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_PERSON_URN:
        logger.warning("LinkedIn credentials not configured, skipping.")
        return None

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    payload = {
        "author": LINKEDIN_PERSON_URN,
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
