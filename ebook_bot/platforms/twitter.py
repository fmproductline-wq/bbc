"""Twitter / X posting via Twitter API v2 (tweepy)."""
import os
import tweepy
from loguru import logger


def _client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.getenv("TWITTER_API_KEY", ""),
        consumer_secret=os.getenv("TWITTER_API_SECRET", ""),
        access_token=os.getenv("TWITTER_ACCESS_TOKEN", ""),
        access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET", ""),
    )


def post(text: str) -> dict | None:
    """Post a tweet. Returns result dict or None on failure/missing creds."""
    if not os.getenv("TWITTER_API_KEY"):
        logger.warning("Twitter credentials not configured, skipping.")
        return None
    if len(text) > 280:
        text = text[:277] + "..."
    try:
        response = _client().create_tweet(text=text)
        tweet_id = response.data["id"]
        logger.success(f"Twitter: posted tweet {tweet_id}")
        return {"platform": "twitter", "id": tweet_id, "text": text}
    except tweepy.TweepyException as e:
        logger.error(f"Twitter post failed: {e}")
        return None
