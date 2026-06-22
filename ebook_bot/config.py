"""
Central config — all values come from environment variables / .env file.
Copy .env.example to .env and fill in your keys.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Ebook metadata ────────────────────────────────────────────────────────────
EBOOK = {
    "title": os.getenv("EBOOK_TITLE", "My Ebook"),
    "tagline": os.getenv("EBOOK_TAGLINE", "The ultimate guide you need"),
    "price": os.getenv("EBOOK_PRICE", "$9.99"),
    "description": os.getenv("EBOOK_DESCRIPTION", ""),
    "topics": os.getenv("EBOOK_TOPICS", "").split(","),  # comma-separated list
    "author": os.getenv("EBOOK_AUTHOR", ""),
    "cover_image_url": os.getenv("EBOOK_COVER_IMAGE_URL", ""),
}

# ── Sales platform keys ───────────────────────────────────────────────────────
GUMROAD_ACCESS_TOKEN = os.getenv("GUMROAD_ACCESS_TOKEN", "")
GUMROAD_PRODUCT_ID = os.getenv("GUMROAD_PRODUCT_ID", "")

PAYHIP_API_KEY = os.getenv("PAYHIP_API_KEY", "")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
STRIPE_SUCCESS_URL = os.getenv("STRIPE_SUCCESS_URL", "")

SENDOWL_API_KEY = os.getenv("SENDOWL_API_KEY", "")
SENDOWL_API_SECRET = os.getenv("SENDOWL_API_SECRET", "")
SENDOWL_PRODUCT_ID = os.getenv("SENDOWL_PRODUCT_ID", "")

# ── Social media keys ─────────────────────────────────────────────────────────
# Twitter / X
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# LinkedIn
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")  # urn:li:person:XXXXX

# Facebook / Instagram (Meta Graph API)
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

# Reddit
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_SUBREDDITS = os.getenv("REDDIT_SUBREDDITS", "ebooks,selfpublishing").split(",")

# Pinterest
PINTEREST_ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
PINTEREST_BOARD_ID = os.getenv("PINTEREST_BOARD_ID", "")

# TikTok
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# Telegram channel (optional broadcast)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# ── AI content generation ─────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Scheduler ─────────────────────────────────────────────────────────────────
# How often to post (in hours)
POST_INTERVAL_HOURS = int(os.getenv("POST_INTERVAL_HOURS", "6"))
# Which platforms to post to (comma-separated, or "all")
ACTIVE_PLATFORMS = os.getenv("ACTIVE_PLATFORMS", "all")
