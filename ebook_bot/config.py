"""
Central config — all values come from environment variables / .env file.
Values are read FRESH on each call so that settings saved via the UI take
effect immediately without restarting the app.
"""
import os
from dotenv import load_dotenv

# Load .env once at startup (sets env vars; later os.environ writes override).
load_dotenv(override=False)


def get_ebook() -> dict:
    """Return current ebook metadata, always fresh from os.environ."""
    raw_topics = os.getenv("EBOOK_TOPICS", "")
    topics = [t.strip() for t in raw_topics.split(",") if t.strip()]
    return {
        "title":           os.getenv("EBOOK_TITLE", "My Ebook"),
        "tagline":         os.getenv("EBOOK_TAGLINE", "The ultimate guide you need"),
        "price":           os.getenv("EBOOK_PRICE", "$9.99"),
        "description":     os.getenv("EBOOK_DESCRIPTION", ""),
        "topics":          topics,
        "author":          os.getenv("EBOOK_AUTHOR", ""),
        "cover_image_url": os.getenv("EBOOK_COVER_IMAGE_URL", ""),
    }


def get_active_platforms() -> str:
    """Return comma-separated active platforms string, always fresh."""
    return os.getenv("ACTIVE_PLATFORMS", "all")


# ── Stable module-level constants (not user-configurable at runtime) ──────────
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Kept for backwards-compat but refreshed lazily via getters above ──────────
# Platform modules must call os.getenv() inside their functions — never cache
# these at module level, because the UI updates os.environ after import.
POST_INTERVAL_HOURS: int = int(os.getenv("POST_INTERVAL_HOURS", "6"))
