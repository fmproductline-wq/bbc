"""
Main entrypoint: FastAPI webhook server + Telegram bot + periodic agents.

Start with:
    python main.py

TradingView alert webhook URL:
    POST https://yourdomain.com/webhook/tradingview
"""
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.executor import handle_signal
from trading.state import state
from agents.bug_checker import run_bug_check
from bot.telegram_bot import build_app as build_telegram
from predictions import kalshi as kalshi_client

app = FastAPI(title="Trading & Prediction Bot", version="2.0.0")
scheduler = AsyncIOScheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fmproductline-wq.github.io"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

SYSTEM_PROMPT = (
    "You are the Best Brand AI shopping agent powered by Claude and Bitrefill. "
    "Help customers find and buy gift cards, mobile top-ups, and eSIMs with crypto. "
    "Top brands: Amazon, Netflix, Spotify, Apple, Google Play, PlayStation, Xbox, Steam, "
    "Walmart, DoorDash, Uber, Airbnb, Nike, Starbucks, Disney+, YouTube, Twitch, AT&T, "
    "T-Mobile, Vanilla Visa and 1,500+ more. "
    "Payment methods: Bitcoin Lightning, ETH, USDC, USDT. Be friendly and concise."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


# ── Bitrefill Storefront Chat ─────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    """Proxy chat messages to Claude. API key stays server-side."""
    if not cfg.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 512,
        "system": SYSTEM_PROMPT,
        "messages": [m.model_dump() for m in req.messages],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": cfg.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["content"][0]["text"]
            return JSONResponse({"reply": reply})
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e}")
            raise HTTPException(status_code=502, detail="AI service error")
        except Exception as e:
            logger.error(f"Chat endpoint error: {e}")
            raise HTTPException(status_code=500, detail="Internal error")


# ── TradingView Webhook ───────────────────────────────────────────────────────

@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request):
    """
    Receives JSON alerts from TradingView Pine Script (Xtreme Trend / HOTT LOTT).

    Alert message format:
    {
      "secret": "your_webhook_secret",
      "indicator": "xtreme_trend",
      "action": "{{strategy.order.action}}",
      "symbol": "{{ticker}}",
      "timeframe": "{{interval}}",
      "price": {{close}}
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if cfg.TRADINGVIEW_WEBHOOK_SECRET and body.get("secret") != cfg.TRADINGVIEW_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

    try:
        signal = TVSignal(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(f"TradingView signal: {signal.indicator} {signal.action} {signal.symbol} @ {signal.price}")
    result = await handle_signal(signal)
    await _notify_telegram(f"📡 *TradingView Alert*\n{result}")
    return {"status": "ok", "result": result}


@app.get("/webhook/tradingview")
async def webhook_test():
    """Health check for TradingView to verify the webhook URL."""
    return {"status": "ok", "message": "Webhook active"}


# ── Status ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "running",
        "auto_trade": state.auto_trade,
        "auto_bet": state.auto_bet,
        "open_positions": len(state.open_positions()),
        "signals_received": len(state.signal_log),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Telegram notification helper ──────────────────────────────────────────────

_tg_app = None


async def _notify_telegram(text: str):
    global _tg_app
    try:
        if _tg_app and cfg.TELEGRAM_ALLOWED_USER_ID:
            await _tg_app.bot.send_message(
                chat_id=cfg.TELEGRAM_ALLOWED_USER_ID,
                text=text,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")


# ── Scheduled agents ──────────────────────────────────────────────────────────

async def scheduled_bug_check():
    """Run bug checker every 30 minutes and alert on issues."""
    try:
        result = run_bug_check(auto_remediate=True)
        if result.has_critical:
            await _notify_telegram(f"🚨 *Scheduled Bug Check*\n{result.to_telegram()}")
        elif result.has_warnings:
            await _notify_telegram(f"⚠️ *Scheduled Bug Check*\n{result.to_telegram()}")
        else:
            logger.info("Scheduled bug check: no issues")
    except Exception as e:
        logger.error(f"Scheduled bug check failed: {e}")
        await _notify_telegram(f"❌ Bug checker agent error: {e}")


# ── Startup / shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _tg_app
    logger.info("Bot starting up…")

    if cfg.KALSHI_EMAIL and cfg.KALSHI_PASSWORD:
        try:
            kalshi_client.login()
        except Exception as e:
            logger.warning(f"Kalshi login failed at startup: {e}")

    if cfg.TELEGRAM_BOT_TOKEN:
        _tg_app = build_telegram()
        await _tg_app.initialize()
        await _tg_app.start()
        asyncio.create_task(_run_telegram_polling(_tg_app))
        logger.info("Telegram bot started")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — Telegram disabled")

    # Schedule bug checker every 30 minutes
    scheduler.add_job(scheduled_bug_check, "interval", minutes=30, id="bug_check")
    scheduler.start()
    logger.info("Scheduler started — bug check every 30 min")

    # Run an immediate startup bug check
    asyncio.create_task(scheduled_bug_check())


@app.on_event("shutdown")
async def shutdown():
    global _tg_app
    scheduler.shutdown(wait=False)
    if _tg_app:
        await _tg_app.stop()
        await _tg_app.shutdown()


async def _run_telegram_polling(tg_app):
    await tg_app.updater.start_polling(drop_pending_updates=True)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
