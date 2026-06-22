"""
Reddit posting via PRAW (Python Reddit API Wrapper).
Posts a link submission to each configured subreddit.
"""
import praw
from loguru import logger
from ..config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME, REDDIT_PASSWORD, REDDIT_SUBREDDITS, EBOOK,
)


def _reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
        user_agent=f"ebookbot/1.0 by {REDDIT_USERNAME}",
    )


def post(text: str, link: str, title: str = None) -> list[dict]:
    """
    Submit a link + selftext post to each configured subreddit.
    Returns list of result dicts.
    """
    if not REDDIT_CLIENT_ID or not REDDIT_USERNAME:
        logger.warning("Reddit credentials not configured, skipping.")
        return []

    title = title or f"{EBOOK['title']} — {EBOOK['tagline']}"
    results = []
    reddit = _reddit()

    for sub_name in REDDIT_SUBREDDITS:
        sub_name = sub_name.strip()
        if not sub_name:
            continue
        try:
            subreddit = reddit.subreddit(sub_name)
            submission = subreddit.submit(title=title, url=link)
            logger.success(f"Reddit: posted to r/{sub_name} — {submission.id}")
            results.append({"platform": f"reddit/{sub_name}", "id": submission.id, "url": submission.shortlink})
        except praw.exceptions.PRAWException as e:
            logger.error(f"Reddit r/{sub_name} failed: {e}")

    return results
