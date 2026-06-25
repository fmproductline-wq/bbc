"""
Main entrypoint: FastAPI webhook server + Telegram bot + periodic agents.

Start with:
    python main.py

TradingView alert webhook URL:
    POST https://yourdomain.com/webhook/tradingview
"""
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from config import cfg
from trading.signals import TVSignal
from trading.executor import handle_signal
from trading.state import state
from agents.bug_checker import run_bug_check
from bot.telegram_bot import build_app as build_telegram
from predictions import kalshi as kalshi_client
from predictions.polymarket_research_bot import poly_research_bot
from trading.signal_scanner import signal_scanner
from trading.health_monitor import health_monitor
from trading.trailing_stop import trailing_stop_monitor
from payments.stripe_checkout import (
    create_checkout_session, verify_session,
    issue_download_token, consume_token,
    verify_stripe_webhook, DOWNLOAD_LINKS,
)

app = FastAPI(title="Best Brand Co. — Trading Bot", version="2.0.0")

# Allow bestbrand.ca to call these endpoints from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bestbrand.ca", "https://www.bestbrand.ca"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
scheduler = AsyncIOScheduler()


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


# ── Payment & Download endpoints ──────────────────────────────────────────────

@app.post("/payments/create-checkout")
async def create_checkout(request: Request):
    """Called by bestbrand.ca Buy button → returns Stripe Checkout URL."""
    base = cfg.APP_BASE_URL
    try:
        url = create_checkout_session(
            success_url=f"{base}/payments/success",
            cancel_url=f"{base}/download",
        )
        return {"url": url}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Checkout creation failed: {e}")
        raise HTTPException(status_code=500, detail="Payment unavailable")


@app.get("/payments/success", response_class=HTMLResponse)
async def payment_success(session_id: str = ""):
    """
    Stripe redirects here after payment.
    Verifies the session then shows download links protected by a token.
    """
    if not session_id or not verify_session(session_id):
        return HTMLResponse(_payment_error_page(), status_code=402)

    token = issue_download_token()
    return HTMLResponse(_success_page(token))


@app.get("/payments/download")
async def download_file(token: str, platform: str):
    """Serve download link after validating token."""
    if not consume_token(token):
        raise HTTPException(status_code=403, detail="Invalid or expired download link. Please purchase again.")
    link = DOWNLOAD_LINKS.get(platform)
    if not link:
        raise HTTPException(status_code=400, detail="Unknown platform")
    return RedirectResponse(url=link)


@app.post("/payments/webhook")
async def stripe_webhook(request: Request):
    """Stripe calls this server-side to confirm payment (backup to success redirect)."""
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    event      = verify_stripe_webhook(payload, sig_header, cfg.STRIPE_WEBHOOK_SECRET)
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        logger.info(f"Payment confirmed: {session['id']} — {session.get('customer_email','unknown')}")
        # Optionally notify yourself via Telegram
        await _notify_telegram(
            f"💰 *New Purchase!*\n"
            f"Email: {session.get('customer_email', 'N/A')}\n"
            f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
            f"Session: `{session['id']}`"
        )
    return {"status": "ok"}


# ── Payment page helpers ───────────────────────────────────────────────────────

def _success_page(token: str) -> str:
    base = cfg.APP_BASE_URL
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Download — Best Brand Co.</title>
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#0A0A0F;color:#fff;font-family:'Inter',-apple-system,sans-serif;
         display:flex;flex-direction:column;align-items:center;justify-content:center;
         min-height:100vh;padding:24px;text-align:center}}
    .card{{background:#10101E;border:1px solid #2D2D5E;border-radius:16px;
           padding:48px 40px;max-width:520px;width:100%}}
    h1{{font-size:28px;margin-bottom:8px;background:linear-gradient(135deg,#fff,#A855F7);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent}}
    p{{color:#B0B0CC;margin-bottom:32px;line-height:1.6}}
    .btn{{display:block;background:linear-gradient(135deg,#6C63FF,#A855F7);
          color:#fff;text-decoration:none;font-weight:700;font-size:16px;
          padding:14px 24px;border-radius:10px;margin:10px 0;transition:opacity .2s}}
    .btn:hover{{opacity:.85}}
    .btn.mac{{background:linear-gradient(135deg,#555,#333)}}
    .btn.linux{{background:linear-gradient(135deg,#E95420,#bf3d0e)}}
    .note{{font-size:12px;color:#5A5A80;margin-top:24px;line-height:1.6}}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:52px;margin-bottom:16px">✅</div>
    <h1>Payment Successful!</h1>
    <p>Thank you for purchasing <strong>Best Brand Co.</strong><br>
       Choose your platform to download:</p>

    <a class="btn" href="{base}/payments/download?token={token}&platform=windows">
      🪟 Download for Windows (.zip)
    </a>
    <a class="btn mac" href="{base}/payments/download?token={token}&platform=mac">
      🍎 Download for macOS (.dmg)
    </a>
    <a class="btn linux" href="{base}/payments/download?token={token}&platform=linux">
      🐧 Download for Linux (.tar.gz)
    </a>

    <p class="note">
      These links are valid for <strong>24 hours</strong>.<br>
      Bookmark this page or save your links now.<br>
      Need help? Email <a href="mailto:support@bestbrand.ca"
        style="color:#6C63FF">support@bestbrand.ca</a>
    </p>
  </div>
</body>
</html>"""


def _payment_error_page() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Payment Error — Best Brand Co.</title>
  <style>
    body{{background:#0A0A0F;color:#fff;font-family:sans-serif;
         display:flex;align-items:center;justify-content:center;
         min-height:100vh;text-align:center;padding:24px}}
    .card{{background:#10101E;border:1px solid #F85149;border-radius:16px;padding:48px}}
    h1{{color:#F85149;margin-bottom:12px}}
    a{{color:#6C63FF}}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:52px">❌</div>
    <h1>Payment not verified</h1>
    <p style="color:#B0B0CC;margin:16px 0">
      We could not confirm your payment.<br>
      Please <a href="/download">try again</a> or contact
      <a href="mailto:support@bestbrand.ca">support@bestbrand.ca</a>
    </p>
  </div>
</body>
</html>"""


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

    # Start Polymarket Research Bot
    async def _notify_poly(msg: str):
        await _notify_telegram(msg)
    poly_research_bot.set_notifier(_notify_poly)
    asyncio.create_task(poly_research_bot.start())
    logger.info("Polymarket Research Bot started")

    # Start Signal Scanner — watches all assets, fires Telegram approval on new signals
    async def _notify_scanner(msg: str):
        await _notify_telegram(msg)
    signal_scanner.set_notifier(_notify_scanner)
    asyncio.create_task(signal_scanner.start())
    logger.info(f"Signal Scanner started — watching {len(signal_scanner._states)} assets")

    # Start Health Monitor — pings Hyperliquid API, alerts on failure (#2)
    async def _notify_health(msg: str):
        await _notify_telegram(msg)
    health_monitor.set_notifier(_notify_health)
    asyncio.create_task(health_monitor.start())
    logger.info("Health monitor started")

    # Start Trailing Stop Monitor — moves SL to breakeven after TP1 (#10)
    async def _notify_trailing(msg: str):
        await _notify_telegram(msg)
    trailing_stop_monitor.set_notifier(_notify_trailing)
    asyncio.create_task(trailing_stop_monitor.start())
    logger.info("Trailing stop monitor started")

    # Run an immediate startup bug check
    asyncio.create_task(scheduled_bug_check())


@app.on_event("shutdown")
async def shutdown():
    global _tg_app
    scheduler.shutdown(wait=False)
    poly_research_bot.stop()
    signal_scanner.stop()
    health_monitor.stop()
    trailing_stop_monitor.stop()
    if _tg_app:
        await _tg_app.stop()
        await _tg_app.shutdown()


async def _run_telegram_polling(tg_app):
    await tg_app.updater.start_polling(drop_pending_updates=True)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
