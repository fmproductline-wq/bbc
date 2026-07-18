"""Reddit posting via PRAW."""
import os
import praw
from loguru import logger
from ..config import get_ebook


def _reddit() -> praw.Reddit:
    username = os.getenv("REDDIT_USERNAME", "")
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID", ""),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
        username=username,
        password=os.getenv("REDDIT_PASSWORD", ""),
        user_agent=f"ebookbot/1.0 by {username}",
    )


def post(text: str, link: str, title: str = "") -> list[dict]:
    """Submit a link post to each configured subreddit."""
    if not os.getenv("REDDIT_CLIENT_ID") or not os.getenv("REDDIT_USERNAME"):
        logger.warning("Reddit credentials not configured, skipping.")
        return []

    ebook = get_ebook()
    title = title or f"{ebook['title']} — {ebook['tagline']}"
    raw_subs = os.getenv("REDDIT_SUBREDDITS", "ebooks,selfpublishing")
    subreddits = [s.strip() for s in raw_subs.split(",") if s.strip()]

    results = []
    reddit = _reddit()
    for sub_name in subreddits:
        try:
            submission = reddit.subreddit(sub_name).submit(title=title, url=link)
            logger.success(f"Reddit: posted to r/{sub_name} — {submission.id}")
            results.append({"platform": f"reddit/{sub_name}", "id": submission.id, "url": submission.shortlink})
        except praw.exceptions.PRAWException as e:
            logger.error(f"Reddit r/{sub_name} failed: {e}")
    return results
