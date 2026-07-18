"""Telegram channel broadcasting via Bot API."""
import os
import requests
from loguru import logger


def post(text: str) -> dict | None:
    """Send a message to the configured Telegram channel."""
    token      = os.getenv("TELEGRAM_BOT_TOKEN", "")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "")
    if not token or not channel_id:
        logger.warning("Telegram channel not configured, skipping.")
        return None

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": channel_id,
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
