"""
Telegram channel broadcasting via Bot API.
"""
import requests
from loguru import logger
from ..config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID


def post(text: str) -> dict | None:
    """Send a message to the configured Telegram channel."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        logger.warning("Telegram channel not configured, skipping.")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHANNEL_ID,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        r.raise_for_status()
        msg_id = r.json().get("result", {}).get("message_id", "unknown")
        logger.success(f"Telegram: sent message {msg_id}")
        return {"platform": "telegram", "id": msg_id}
    except requests.HTTPError as e:
        logger.error(f"Telegram post failed: {e} — {r.text}")
        return None
