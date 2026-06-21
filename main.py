"""
Main entrypoint: FastAPI webhook server + Telegram bot running concurrently.

Start with:
    python main.py

TradingView alert webhook URL:
    POST https://yourdomain.com/webhook/tradingview
"""
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.executor import handle_signal
from trading.state import state
from bot.telegram_bot import build_app as build_telegram
from predictions import kalshi as kalshi_client

app = FastAPI(title="Trading & Prediction Bot", version="1.0.0")


# ── TradingView Webhook ───────────────────────────────────────────────────────

@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request):
    """
    Receives JSON alerts from TradingView Pine Script.

    In TradingView, create an alert on your Xtreme Trend or HOTT/LOTT indicator
    and set the webhook URL to this endpoint. Alert message format (JSON):

    {
      "secret": "your_webhook_secret",
      "indicator": "xtreme_trend",
      "action": "buy",
      "symbol": "{{ticker}}",
      "timeframe": "{{interval}}",
      "price": {{close}},
      "chain": "polygon"
    }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Validate webhook secret
    if cfg.TRADINGVIEW_WEBHOOK_SECRET and body.get("secret") != cfg.TRADINGVIEW_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid secret")

    try:
        signal = TVSignal(**body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    logger.info(f"TradingView signal: {signal.indicator} {signal.action} {signal.symbol} @ {signal.price}")

    result = await handle_signal(signal)

    # Notify Telegram
    await _notify_telegram(f"📡 *TradingView Alert*\n{result}")

    return {"status": "ok", "result": result}


@app.get("/webhook/tradingview")
async def webhook_test():
    """Health check endpoint for TradingView to verify the webhook URL."""
    return {"status": "ok", "message": "Webhook is active"}


# ── Status endpoint ───────────────────────────────────────────────────────────

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
        logger.warning(f"Failed to send Telegram notification: {e}")


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global _tg_app
    logger.info("Bot starting up…")

    # Try Kalshi login on startup
    if cfg.KALSHI_EMAIL and cfg.KALSHI_PASSWORD:
        try:
            kalshi_client.login()
        except Exception as e:
            logger.warning(f"Kalshi login failed at startup: {e}")

    # Start Telegram bot in background
    if cfg.TELEGRAM_BOT_TOKEN:
        _tg_app = build_telegram()
        await _tg_app.initialize()
        await _tg_app.start()
        # Use polling in background task
        asyncio.create_task(_run_telegram_polling(_tg_app))
        logger.info("Telegram bot started")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")


@app.on_event("shutdown")
async def shutdown():
    global _tg_app
    if _tg_app:
        await _tg_app.stop()
        await _tg_app.shutdown()


async def _run_telegram_polling(tg_app):
    """Run Telegram polling in the background."""
    await tg_app.updater.start_polling(drop_pending_updates=True)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
