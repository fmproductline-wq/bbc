"""
Deal-scanning bots: each bot handles a category, searches the web,
then uses Claude to extract structured deal data.
"""
import asyncio
import json
import re
import httpx
from typing import Any
import anthropic

ANTHROPIC_CLIENT = anthropic.Anthropic()

CATEGORY_QUERIES: dict[str, list[str]] = {
    "Electronics":     ["electronics deals today", "tech sale discount coupon"],
    "Clothing":        ["clothing sale today", "fashion deals discount coupon"],
    "Food & Groceries":["grocery deals this week", "food coupons discount"],
    "Travel":          ["travel deals flights hotels", "vacation discount coupon"],
    "Home & Garden":   ["home decor sale", "garden furniture deals discount"],
    "Sports":          ["sports equipment sale", "fitness deals discount"],
    "Books & Media":   ["book deals kindle sale", "ebook discount coupon"],
    "Beauty":          ["beauty skincare sale", "makeup deals discount coupon"],
    "Gaming":          ["gaming deals sale", "video game discount coupon"],
    "Automotive":      ["auto parts sale", "car accessories deals coupon"],
    "Toys & Kids":     ["toy deals sale", "kids products discount coupon"],
    "Health":          ["health supplement sale", "pharmacy deals coupon"],
}

DEAL_EXTRACTION_PROMPT = """You are a deal-finding assistant. I will give you web search results about deals for the category: {category}.

Extract up to 5 real, specific deals from the text below. For each deal return a JSON object with these fields:
- title: short deal title
- store: store/retailer name
- price: current price (string, e.g. "$29.99")
- original_price: original price if available (string or null)
- discount: discount amount or % if mentioned (string or null)
- coupon_code: coupon code if present (string or null)
- expiry: expiry date or "Limited time" or null
- shipping: shipping info (e.g. "Free shipping", "$5.99", "In-store only", null)
- location: city/region if local deal, otherwise "Online" or null
- image_url: a plausible product image URL from the text if found, else null
- deal_url: the deal link URL if found, else null
- category: "{category}"
- summary: one sentence description of the deal

Return ONLY a JSON array of deal objects. No markdown, no explanation.

Search results:
{results}
"""


async def duckduckgo_search(query: str, max_results: int = 8) -> list[dict]:
    """Fetch DuckDuckGo instant answer + web results via HTML scrape."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DealBot/1.0)"}
    params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get("https://api.duckduckgo.com/", params=params, headers=headers)
            data = r.json()
            results = []
            if data.get("AbstractText"):
                results.append({"title": data.get("Heading", ""), "body": data["AbstractText"], "url": data.get("AbstractURL", "")})
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({"title": topic.get("Text", "")[:80], "body": topic.get("Text", ""), "url": topic.get("FirstURL", "")})
            return results
        except Exception:
            return []


async def brave_search_fallback(query: str) -> list[dict]:
    """Fallback: use a deal aggregator RSS feed."""
    feeds = [
        f"https://www.reddit.com/r/deals/search.json?q={query}&sort=new&limit=5",
    ]
    results = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DealBot/1.0)"}
    async with httpx.AsyncClient(timeout=10) as client:
        for url in feeds:
            try:
                r = await client.get(url, headers=headers)
                data = r.json()
                posts = data.get("data", {}).get("children", [])
                for p in posts:
                    d = p.get("data", {})
                    results.append({
                        "title": d.get("title", ""),
                        "body": d.get("selftext", d.get("title", "")),
                        "url": d.get("url", ""),
                    })
            except Exception:
                pass
    return results


def extract_deals_with_claude(category: str, raw_results: list[dict]) -> list[dict]:
    """Use Claude to parse raw search results into structured deal objects."""
    if not raw_results:
        return []

    results_text = "\n\n".join(
        f"[{i+1}] Title: {r.get('title','')}\nURL: {r.get('url','')}\nBody: {r.get('body','')}"
        for i, r in enumerate(raw_results)
    )

    prompt = DEAL_EXTRACTION_PROMPT.format(category=category, results=results_text)

    try:
        msg = ANTHROPIC_CLIENT.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        # strip markdown code fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        deals = json.loads(text)
        if isinstance(deals, list):
            return deals
    except Exception as e:
        print(f"Claude extraction error for {category}: {e}")
    return []


async def scan_category(category: str, extra_query: str = "") -> list[dict]:
    """Run a full scan for one category and return structured deals."""
    base_queries = CATEGORY_QUERIES.get(category, [f"{category} deals discount"])
    if extra_query:
        base_queries = [f"{extra_query} {category} deal discount coupon"] + base_queries

    all_raw: list[dict] = []
    for q in base_queries[:2]:
        results = await duckduckgo_search(q)
        if not results:
            results = await brave_search_fallback(q)
        all_raw.extend(results)

    return extract_deals_with_claude(category, all_raw[:12])


async def scan_categories(categories: list[str], extra_query: str = "") -> dict[str, list[dict]]:
    """Scan multiple categories concurrently."""
    tasks = {cat: scan_category(cat, extra_query) for cat in categories}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    output: dict[str, list[dict]] = {}
    for cat, res in zip(tasks.keys(), results):
        output[cat] = res if isinstance(res, list) else []
    return output
