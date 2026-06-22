"""
Orchestrator — collects sales links, generates content, and dispatches to all platforms.
"""
import random
from loguru import logger
from .config import EBOOK, ACTIVE_PLATFORMS
from .content import ai_writer, templates
from .sales import gumroad, payhip, sendowl, stripe_sales
from .platforms import twitter, linkedin, facebook, instagram, reddit, pinterest, telegram_channel


def _get_best_link() -> str:
    """Try each sales platform in order and return the first available purchase link."""
    checkers = [
        ("Gumroad", gumroad.get_product_link),
        ("Payhip", payhip.get_product_link),
        ("SendOwl", sendowl.get_product_link),
        ("Stripe", stripe_sales.create_checkout_link),
    ]
    for name, fn in checkers:
        try:
            link = fn()
            if link:
                logger.info(f"Using {name} link: {link}")
                return link
        except Exception as e:
            logger.warning(f"{name} link fetch failed: {e}")
    logger.error("No sales link available — check your platform config.")
    return ""


def _is_active(platform: str) -> bool:
    if ACTIVE_PLATFORMS.strip().lower() == "all":
        return True
    return platform in [p.strip().lower() for p in ACTIVE_PLATFORMS.split(",")]


def run_campaign(use_ai: bool = True, style_hint: str = "") -> dict:
    """
    Full campaign run:
    1. Get purchase link from configured sales platforms
    2. Generate content (AI or template)
    3. Post to every active social platform
    Returns a summary dict of results.
    """
    results = {}
    link = _get_best_link()
    if not link:
        logger.error("Aborting campaign — no purchase link available.")
        return {"error": "No purchase link available"}

    cover_image = EBOOK.get("cover_image_url", "")

    # ── Twitter ──────────────────────────────────────────────────────────────
    if _is_active("twitter"):
        if use_ai:
            try:
                text = ai_writer.generate_post("twitter", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for twitter, using template: {e}")
                text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        results["twitter"] = twitter.post(text)

    # ── LinkedIn ─────────────────────────────────────────────────────────────
    if _is_active("linkedin"):
        if use_ai:
            try:
                text = ai_writer.generate_post("linkedin", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for linkedin, using template: {e}")
                text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        results["linkedin"] = linkedin.post(text)

    # ── Facebook ─────────────────────────────────────────────────────────────
    if _is_active("facebook"):
        if use_ai:
            try:
                text = ai_writer.generate_post("facebook", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for facebook, using template: {e}")
                text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        results["facebook"] = facebook.post(text, link=link)

    # ── Instagram ────────────────────────────────────────────────────────────
    if _is_active("instagram"):
        if use_ai:
            try:
                caption = ai_writer.generate_post("instagram", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for instagram, using template: {e}")
                caption = templates.render_template(templates.pick_template("short"), EBOOK, link)
        else:
            caption = templates.render_template(templates.pick_template("short"), EBOOK, link)
        results["instagram"] = instagram.post(caption, image_url=cover_image)

    # ── Reddit ───────────────────────────────────────────────────────────────
    if _is_active("reddit"):
        if use_ai:
            try:
                text = ai_writer.generate_post("reddit", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for reddit, using template: {e}")
                text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("medium"), EBOOK, link)
        results["reddit"] = reddit.post(text, link=link)

    # ── Pinterest ────────────────────────────────────────────────────────────
    if _is_active("pinterest"):
        if use_ai:
            try:
                text = ai_writer.generate_post("pinterest", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for pinterest, using template: {e}")
                text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        results["pinterest"] = pinterest.post(text, link=link, image_url=cover_image)

    # ── Telegram ─────────────────────────────────────────────────────────────
    if _is_active("telegram"):
        if use_ai:
            try:
                text = ai_writer.generate_post("telegram", link, style_hint=style_hint)
            except Exception as e:
                logger.warning(f"AI failed for telegram, using template: {e}")
                text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        else:
            text = templates.render_template(templates.pick_template("short"), EBOOK, link)
        results["telegram"] = telegram_channel.post(text)

    # Summary
    successful = [k for k, v in results.items() if v is not None]
    failed = [k for k, v in results.items() if v is None]
    logger.info(f"Campaign done — posted to: {successful} | failed: {failed}")
    results["_summary"] = {"success": successful, "failed": failed, "link": link}
    return results


def get_sales_report() -> dict:
    """Aggregate sales data from all configured platforms."""
    report = {}
    try:
        report["gumroad"] = gumroad.get_sales()
    except Exception as e:
        report["gumroad"] = {"error": str(e)}
    try:
        report["stripe"] = stripe_sales.get_recent_sales()
    except Exception as e:
        report["stripe"] = {"error": str(e)}
    try:
        report["sendowl"] = sendowl.get_orders()
    except Exception as e:
        report["sendowl"] = {"error": str(e)}
    return report
