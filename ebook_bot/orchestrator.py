"""
Orchestrator — the complete campaign loop:
  1. Collect the best available purchase link from all sales platforms
  2. Generate content per platform (AI or template fallback)
  3. Post to every active social platform
  4. Return a structured result dict with _summary always present
"""
import os
from loguru import logger
from .config import get_ebook, get_active_platforms
from .content import ai_writer, templates
from .sales import gumroad, payhip, sendowl, stripe_sales
from .platforms import twitter, linkedin, facebook, instagram, reddit, pinterest, telegram_channel


def _get_best_link() -> str:
    """Try each sales platform in priority order; return first working link."""
    checkers = [
        ("Gumroad", gumroad.get_product_link),
        ("Payhip",  payhip.get_product_link),
        ("SendOwl", sendowl.get_product_link),
        ("Stripe",  stripe_sales.create_checkout_link),
    ]
    for name, fn in checkers:
        try:
            link = fn()
            if link:
                logger.info(f"Using {name} link: {link}")
                return link
        except Exception as e:
            logger.warning(f"{name} link fetch failed: {e}")
    logger.error("No sales link available — check your platform config in Settings.")
    return ""


def _is_active(platform: str) -> bool:
    active = get_active_platforms().strip().lower()
    if active == "all":
        return True
    return platform in [p.strip().lower() for p in active.split(",")]


def _make_content(platform: str, link: str, use_ai: bool, style_hint: str, ebook: dict) -> str:
    """Generate content for one platform; fall back to template if AI fails."""
    short_platforms = {"twitter", "instagram", "telegram", "pinterest"}
    style = "short" if platform in short_platforms else "medium"

    if use_ai:
        try:
            return ai_writer.generate_post(platform, link, ebook=ebook, style_hint=style_hint)
        except Exception as e:
            logger.warning(f"AI failed for {platform} ({e}), using template fallback.")

    return templates.render_template(templates.pick_template(style), ebook, link)


def run_campaign(use_ai: bool = True, style_hint: str = "") -> dict:
    """
    Full campaign loop — always returns a dict with a '_summary' key.

    Result shape:
      {
        "twitter":   {"platform": ..., "id": ...} | None,
        ...
        "_summary":  {"success": [...], "failed": [...], "link": "..."},
        "error":     "..." (only present when a top-level error occurred)
      }
    """
    results: dict = {}
    link = _get_best_link()

    if not link:
        msg = "No purchase link available — configure at least one sales platform in Settings."
        logger.error(msg)
        return {
            "_summary": {"success": [], "failed": list(_active_platforms()), "link": ""},
            "error": msg,
        }

    ebook = get_ebook()
    cover  = ebook.get("cover_image_url", "")

    platform_handlers = {
        "twitter":   lambda text: twitter.post(text),
        "linkedin":  lambda text: linkedin.post(text),
        "facebook":  lambda text: facebook.post(text, link=link),
        "instagram": lambda text: instagram.post(text, image_url=cover),
        "reddit":    lambda text: reddit.post(text, link=link),
        "pinterest": lambda text: pinterest.post(text, link=link, image_url=cover),
        "telegram":  lambda text: telegram_channel.post(text),
    }

    for platform, handler in platform_handlers.items():
        if not _is_active(platform):
            continue
        text = _make_content(platform, link, use_ai, style_hint, ebook)
        try:
            results[platform] = handler(text)
        except Exception as e:
            logger.error(f"{platform} handler raised: {e}")
            results[platform] = None

    successful = [k for k, v in results.items() if v is not None]
    failed     = [k for k, v in results.items() if v is None]
    logger.info(f"Campaign done — posted to: {successful} | failed/skipped: {failed}")

    results["_summary"] = {"success": successful, "failed": failed, "link": link}
    return results


def _active_platforms() -> list[str]:
    active = get_active_platforms().strip().lower()
    from .platforms import twitter as _  # noqa — ensure import works
    all_platforms = ["twitter", "linkedin", "facebook", "instagram", "reddit", "pinterest", "telegram"]
    if active == "all":
        return all_platforms
    return [p.strip() for p in active.split(",") if p.strip()]


def get_sales_report() -> dict:
    """Aggregate sales data from all configured platforms."""
    report = {}
    for name, fn in [
        ("gumroad", gumroad.get_sales),
        ("stripe",  stripe_sales.get_recent_sales),
        ("sendowl", sendowl.get_orders),
    ]:
        try:
            report[name] = fn()
        except Exception as e:
            report[name] = {"error": str(e)}
    return report
