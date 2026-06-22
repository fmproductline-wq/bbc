"""
Twitter / X posting via Twitter API v2.
Requires tweepy >= 4.x with OAuth 1.0a user context (for posting).
"""
import tweepy
from loguru import logger
from ..config import (
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET,
)


def _client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    )


def post(text: str) -> dict | None:
    """Post a tweet. Returns response dict or None on failure."""
    if not TWITTER_API_KEY:
        logger.warning("Twitter credentials not configured, skipping.")
        return None
    if len(text) > 280:
        text = text[:277] + "..."
    try:
        client = _client()
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        logger.success(f"Twitter: posted tweet {tweet_id}")
        return {"platform": "twitter", "id": tweet_id, "text": text}
    except tweepy.TweepyException as e:
        logger.error(f"Twitter post failed: {e}")
        return None
