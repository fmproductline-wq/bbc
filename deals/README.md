# BestBrand Deal Bots

AI-powered deal scanner. Select categories, optionally type a keyword, and bots scan the web and return deals with prices, coupons, shipping info, expiry, and links.

## Setup

```bash
cd deals
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
python app.py
```

Open http://localhost:8080

## How it works

1. **Frontend** — category checklist + keyword search box
2. **FastAPI backend** — receives selected categories and optional keyword
3. **Deal bots** — each bot searches DuckDuckGo + Reddit r/deals for that category
4. **Claude claude-sonnet-4-6** — extracts structured deal data (price, coupon, shipping, expiry, image, link) from raw search results
5. **Results** — displayed as cards with filter and sort controls
