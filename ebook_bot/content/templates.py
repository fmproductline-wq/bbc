"""
Pre-written post templates. Each is a Python format string that accepts
keyword arguments from the ebook config dict.
Organized by platform character limits and style.
"""
import random

# Short posts (Twitter / X — 280 chars)
SHORT_TEMPLATES = [
    "📚 {title} — {tagline}\n\nGet your copy today for only {price}!\n\n👉 {link}\n\n#ebook #mustread",
    "Stop scrolling. Start reading.\n\n{title} by {author} is the book you've been waiting for.\n\n{price} → {link}",
    "💡 Want to level up? {title} will change how you think.\n\n{tagline}\n\nOnly {price} → {link}",
    "🔥 New ebook alert!\n\n\"{title}\" — {tagline}\n\nLimited-time offer: {price}\n{link}",
    "I wrote this so YOU don't have to figure it out the hard way.\n\n{title} — {price}\n\n{link}\n\n#ebook",
    "The knowledge inside {title} took years to learn.\nYou can get it today for {price}.\n\n{link}",
    "📖 {title}\n{tagline}\n\n✅ Instant download\n✅ {price}\n✅ {link}",
    "Your next best investment: {title} by {author}\n\nOnly {price} | Instant access\n{link}",
]

# Medium posts (LinkedIn / Facebook)
MEDIUM_TEMPLATES = [
    """\
🚀 Exciting news — my new ebook "{title}" is now available!

{description}

Whether you're a beginner or looking to level up, this guide gives you everything you need.

💰 Price: {price}
📥 Instant digital download
🔗 Get it here: {link}

Drop a comment if you have questions. I'd love to hear from you!

#{tag1} #{tag2} #ebook #digitalproduct""",

    """\
I spent months compiling everything I know into one resource.

"{title}" — {tagline}

Here's what's inside:
{topics_list}

If this sounds like something you need, grab it now for just {price}:
{link}

Share with someone who needs it! 🙌""",

    """\
📚 Knowledge is the best investment.

My ebook "{title}" covers exactly what you need to know about {topics_preview}.

✅ Practical, actionable advice
✅ Written by {author}
✅ Only {price}

👉 Get instant access: {link}""",

    """\
What would you do with the right information at the right time?

"{title}" by {author} gives you that edge.

{tagline}

📌 {price} | Instant download
🔗 {link}

Like and share if you found this helpful! 💪""",
]

# Long-form / blog-style (can be used as LinkedIn articles or Facebook Notes)
LONG_TEMPLATES = [
    """\
Why I Wrote "{title}" — And Why You Should Read It

{description}

After years of working in this space, I realized there was no single resource that covered everything in a practical, no-fluff way. So I wrote {title}.

Here's what you'll learn:
{topics_list}

I priced it at {price} because I want it to be accessible to everyone who needs it.

📥 Grab your copy here: {link}

Questions? Drop them below. I read every comment.""",
]


def pick_template(style: str = "short") -> str:
    """Return a random template for the given style: short | medium | long."""
    mapping = {
        "short": SHORT_TEMPLATES,
        "medium": MEDIUM_TEMPLATES,
        "long": LONG_TEMPLATES,
    }
    pool = mapping.get(style, SHORT_TEMPLATES)
    return random.choice(pool)


def render_template(template: str, ebook: dict, link: str) -> str:
    """Fill a template with ebook metadata."""
    topics = [t.strip() for t in ebook.get("topics", []) if t.strip()]
    topics_list = "\n".join(f"• {t}" for t in topics) if topics else "• Key strategies\n• Proven methods"
    topics_preview = ", ".join(topics[:3]) if topics else "key topics"
    tag1 = topics[0].replace(" ", "").lower() if topics else "selfimprovement"
    tag2 = topics[1].replace(" ", "").lower() if len(topics) > 1 else "growth"

    return template.format(
        title=ebook.get("title", ""),
        tagline=ebook.get("tagline", ""),
        price=ebook.get("price", ""),
        description=ebook.get("description", ebook.get("tagline", "")),
        author=ebook.get("author", ""),
        link=link,
        topics_list=topics_list,
        topics_preview=topics_preview,
        tag1=tag1,
        tag2=tag2,
    )
