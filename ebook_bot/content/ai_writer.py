"""
AI content generation using the Claude API.
All credentials are read from os.environ at call-time so that keys entered
in the Settings UI take effect without restarting.
"""
import os
import anthropic
from loguru import logger
from ..config import CLAUDE_MODEL, get_ebook


def _client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set — add it in Settings.")
    return anthropic.Anthropic(api_key=key)


def _ebook_context(ebook: dict) -> str:
    topics = ", ".join(t.strip() for t in ebook.get("topics", []) if t.strip())
    return (
        f"Title: {ebook.get('title', '')}\n"
        f"Tagline: {ebook.get('tagline', '')}\n"
        f"Price: {ebook.get('price', '')}\n"
        f"Author: {ebook.get('author', '')}\n"
        f"Description: {ebook.get('description', '')}\n"
        f"Topics covered: {topics or 'various topics'}"
    )


def generate_post(platform: str, link: str, ebook: dict = None, style_hint: str = "") -> str:
    """
    Ask Claude to write a platform-specific promotional post for the ebook.

    platform  : twitter | linkedin | facebook | instagram | reddit | pinterest | telegram
    link      : the purchase / listing URL
    style_hint: optional extra instruction (e.g. 'make it funny', 'include a question')
    """
    ebook = ebook or get_ebook()
    ctx = _ebook_context(ebook)

    platform_rules = {
        "twitter":   "Max 280 characters. Be punchy, use 1-2 emojis, 2-3 hashtags, include the link at the end.",
        "linkedin":  "Professional tone, 150-300 words. Include a personal insight, bullet points if helpful, call to action, 3-5 hashtags.",
        "facebook":  "Friendly and conversational, 100-200 words. Use emojis, ask the audience a question, include the link.",
        "instagram": "Engaging caption, 50-150 words + up to 30 relevant hashtags on a new line. No live links in caption (mention 'link in bio').",
        "reddit":    "Genuine, community-first tone. No hard selling. Share value first, mention the ebook naturally, include the link.",
        "pinterest": "Descriptive, keyword-rich pin description under 500 characters. Focus on what readers will learn.",
        "telegram":  "Casual and direct, 50-150 words. Use bold text with **asterisks**, include the link.",
    }

    rules = platform_rules.get(platform.lower(), "Write a compelling 100-word promotional post, include the link.")

    prompt = (
        "You are a skilled digital marketing copywriter. Write a promotional post for the following ebook.\n\n"
        f"Ebook details:\n{ctx}\n\n"
        f"Purchase link: {link}\n\n"
        f"Platform: {platform.upper()}\n"
        f"Rules: {rules}\n"
        + (f"Style note: {style_hint}\n" if style_hint else "")
        + "\nWrite ONLY the post content — no explanations, no labels, no quotes around it."
    )

    logger.debug(f"Generating {platform} post via Claude...")
    message = _client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_batch(platforms: list[str], link: str, ebook: dict = None) -> dict[str, str]:
    """Generate one post per platform. Returns {platform: text | None}."""
    results = {}
    for platform in platforms:
        try:
            results[platform] = generate_post(platform, link, ebook)
        except Exception as e:
            logger.error(f"Failed to generate post for {platform}: {e}")
            results[platform] = None
    return results


def generate_email_sequence(link: str, ebook: dict = None, num_emails: int = 3) -> list[dict]:
    """Generate a short email marketing sequence (subject + body) for the ebook."""
    ebook = ebook or get_ebook()
    ctx = _ebook_context(ebook)

    # Build per-email guidance dynamically for any num_emails
    email_roles = [
        "Introduce the problem the ebook solves (soft sell, no direct price mention)",
        "Share what's inside and include a testimonial or social proof (medium sell)",
        "Urgency / final call to action — mention price and deadline (hard sell)",
        "Bonus content teaser or FAQ to overcome objections",
        "Last chance — final reminder, re-state the value and link",
    ]
    role_lines = "\n".join(
        f"Email {i+1}: {email_roles[i % len(email_roles)]}"
        for i in range(num_emails)
    )

    prompt = (
        f"You are an email marketing expert. Write {num_emails} emails for a sequence promoting this ebook.\n\n"
        f"Ebook details:\n{ctx}\n\n"
        f"Purchase link: {link}\n\n"
        f"{role_lines}\n\n"
        "Format EACH email exactly like this (keep the --- separator):\n"
        "SUBJECT: <subject line>\n"
        "BODY:\n"
        "<body text>\n"
        "---"
    )

    message = _client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    emails = []
    for block in raw.split("---"):
        block = block.strip()
        if not block:
            continue
        subject, body_lines, in_body = "", [], False
        for line in block.split("\n"):
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)
        if subject or body_lines:
            emails.append({"subject": subject, "body": "\n".join(body_lines).strip()})

    return emails[:num_emails]
