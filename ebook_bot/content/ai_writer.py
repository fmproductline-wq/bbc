"""
AI content generation using the Claude API.
Generates unique marketing posts, captions, and ad copy for the ebook.
"""
import anthropic
from loguru import logger
from ..config import ANTHROPIC_API_KEY, CLAUDE_MODEL, EBOOK


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _ebook_context(ebook: dict) -> str:
    topics = ", ".join(t.strip() for t in ebook.get("topics", []) if t.strip())
    return (
        f"Title: {ebook['title']}\n"
        f"Tagline: {ebook['tagline']}\n"
        f"Price: {ebook['price']}\n"
        f"Author: {ebook['author']}\n"
        f"Description: {ebook.get('description', '')}\n"
        f"Topics covered: {topics}"
    )


def generate_post(platform: str, link: str, ebook: dict = None, style_hint: str = "") -> str:
    """
    Ask Claude to write a platform-specific promotional post for the ebook.

    platform: twitter | linkedin | facebook | instagram | reddit | pinterest | telegram
    link: the purchase / listing URL
    style_hint: optional extra instruction (e.g. 'make it funny', 'include a question')
    """
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    ebook = ebook or EBOOK
    ctx = _ebook_context(ebook)

    platform_rules = {
        "twitter": "Max 280 characters. Be punchy, use 1-2 emojis, 2-3 hashtags, include the link at the end.",
        "linkedin": "Professional tone, 150-300 words. Include a personal insight, bullet points if helpful, call to action, 3-5 hashtags.",
        "facebook": "Friendly and conversational, 100-200 words. Use emojis, ask the audience a question, include the link.",
        "instagram": "Engaging caption, 50-150 words + up to 30 relevant hashtags on a new line. No live links in caption (mention 'link in bio').",
        "reddit": "Genuine, community-first tone. No hard selling. Share value first, mention the ebook naturally, include the link.",
        "pinterest": "Descriptive, keyword-rich pin description under 500 characters. Focus on what readers will learn.",
        "telegram": "Casual and direct, 50-150 words. Use bold text with **asterisks**, include the link.",
    }

    rules = platform_rules.get(platform.lower(), "Write a compelling 100-word promotional post, include the link.")

    prompt = f"""You are a skilled digital marketing copywriter. Write a promotional post for the following ebook.

Ebook details:
{ctx}

Purchase link: {link}

Platform: {platform.upper()}
Rules: {rules}
{f'Style note: {style_hint}' if style_hint else ''}

Write ONLY the post content — no explanations, no labels, no quotes around it."""

    logger.debug(f"Generating {platform} post via Claude...")
    client = _client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_batch(platforms: list[str], link: str, ebook: dict = None) -> dict[str, str]:
    """Generate one post per platform. Returns {platform: post_text}."""
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
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set")

    ebook = ebook or EBOOK
    ctx = _ebook_context(ebook)

    prompt = f"""You are an email marketing expert. Write {num_emails} emails for a sequence promoting this ebook.

Ebook details:
{ctx}

Purchase link: {link}

Email 1: Introduce the problem the ebook solves (soft sell)
Email 2: Share what's inside / social proof (medium sell)
Email 3: Urgency / final call to action (hard sell)

Format each email as:
SUBJECT: <subject line>
BODY:
<body>
---"""

    client = _client()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    emails = []
    for block in raw.split("---"):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        subject = ""
        body_lines = []
        in_body = False
        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)
        emails.append({"subject": subject, "body": "\n".join(body_lines).strip()})
    return emails
