"""
Telegram bot — trade approval gateway + full remote control.

APPROVAL FLOW
─────────────
Every trade/bet arrives as a pending request in approval_queue.
The bot sends a message like:

  ┌──────────────────────────────────┐
  │ ⏳ APPROVAL REQUIRED              │
  │ 📈 LONG — BTC                    │
  │ Entry: $65,000  Size: 0.001 BTC  │
  │ Notional: $65.00   Fee: $0.013   │
  │ Stop: $63,050      TP: $67,000   │
  │                                  │
  │  [✅ APPROVE]    [❌ REJECT]      │
  └──────────────────────────────────┘

Tapping APPROVE executes the trade immediately.
Tapping REJECT cancels it.
No response within 2 minutes → auto-rejected.
"""
import asyncio
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from loguru import logger
from config import cfg
from trading.state import state
from trading import hyperliquid as hl
from trading.approval import approval_queue, PendingRequest
from predictions import polymarket, kalshi, metaculus
from analysis import market_analyzer as ma
from analysis import probability as prob
from agents.bug_checker import run_bug_check


def auth(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != cfg.TELEGRAM_ALLOWED_USER_ID:
            if update.message:
                await update.message.reply_text("⛔ Unauthorized")
            return
        return await func(update, ctx)
    return wrapper


# ── Approval notifier (registered with approval_queue at startup) ─────────────

_bot_app = None   # set in build_app()


async def _send_approval_request(req: PendingRequest):
    """
    Called by approval_queue whenever a trade/bet needs owner approval.
    Sends a Telegram message with ✅ Approve / ❌ Reject inline buttons.
    """
    if not _bot_app or not cfg.TELEGRAM_ALLOWED_USER_ID:
        # No Telegram configured — auto-reject for safety
        req.resolve(False)
        return

    kind_emoji = "📈" if req.kind == "trade" else "🎰"
    timeout_mins = 2

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅  APPROVE", callback_data=f"approve:{req.id}"),
            InlineKeyboardButton(f"❌  REJECT",  callback_data=f"reject:{req.id}"),
        ]
    ])

    text = (
        f"⏳ *APPROVAL REQUIRED*\n"
        f"{kind_emoji} {req.detail}\n\n"
        f"_Request ID: `{req.id}` — expires in {timeout_mins} min_"
    )

    try:
        msg = await _bot_app.bot.send_message(
            chat_id=cfg.TELEGRAM_ALLOWED_USER_ID,
            text=text,
            parse_mode="Markdown",
            reply_markup=kb,
        )
        # Schedule a timeout edit to grey out buttons
        asyncio.create_task(_expire_approval(req, msg.message_id))
    except Exception as e:
        logger.error(f"Failed to send approval request: {e}")
        req.resolve(False)


async def _expire_approval(req: PendingRequest, msg_id: int):
    """After timeout, edit the message to show it expired (if still pending)."""
    from trading.approval import APPROVAL_TIMEOUT_SECS
    await asyncio.sleep(APPROVAL_TIMEOUT_SECS + 2)
    if req.approved is None:
        req.resolve(False)
    try:
        await _bot_app.bot.edit_message_text(
            chat_id=cfg.TELEGRAM_ALLOWED_USER_ID,
            message_id=msg_id,
            text=f"⏰ *EXPIRED* — request `{req.id}` was auto-rejected (no response in 2 min)",
            parse_mode="Markdown",
        )
    except Exception:
        pass


# ── Callback handler for Approve / Reject buttons ────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id if query.from_user else 0

    data = query.data or ""

    # ── Approval callbacks ────────────────────────────────────────────────────
    if data.startswith("approve:") or data.startswith("reject:"):
        if uid != cfg.TELEGRAM_ALLOWED_USER_ID:
            await query.answer("⛔ Unauthorized", show_alert=True)
            return

        action, req_id = data.split(":", 1)
        approved = (action == "approve")
        found = approval_queue.resolve(req_id, approved)

        if not found:
            await query.edit_message_text(
                f"{'✅' if approved else '❌'} Already {'approved' if approved else 'rejected'} "
                f"or expired (ID `{req_id}`)",
                parse_mode="Markdown",
            )
            return

        status_icon = "✅" if approved else "❌"
        status_word = "APPROVED — executing…" if approved else "REJECTED — cancelled"
        await query.edit_message_text(
            f"{status_icon} *{status_word}*\nRequest ID: `{req_id}`",
            parse_mode="Markdown",
        )
        return

    # ── Navigation callbacks ──────────────────────────────────────────────────
    dispatch = {
        "status":   cmd_status,
        "hlpos":    cmd_hlpos,
        "account":  cmd_account,
        "signals":  cmd_signals,
        "toggle_trade": cmd_toggle_trade,
        "toggle_bet":   cmd_toggle_bet,
        "bugcheck": cmd_bugcheck,
    }
    if data in dispatch:
        await dispatch[data](update, ctx)
    elif data == "pending":
        await _show_pending(query)
    elif data == "analyze_prompt":
        await query.message.reply_text("Send: /analyze <coin> [tf]  e.g. /analyze BTC 1h")
    elif data == "prob_prompt":
        await query.message.reply_text("Send: /prob <mkt_price> <our_est> [YES|NO] [platform]")
    elif data in ("poly_search", "kalshi_search", "meta_search"):
        platform = {"poly_search": "poly", "kalshi_search": "kalshi", "meta_search": "meta"}[data]
        await query.message.reply_text(f"Send: /{platform} <keyword>")


async def _show_pending(query):
    pending = approval_queue.get_pending()
    if not pending:
        await query.message.reply_text("No pending approvals.")
        return
    lines = [f"*{len(pending)} pending approval(s):*\n"]
    for req in pending:
        age = int(__import__("time").time() - req.created_at)
        lines.append(f"• `{req.id}` — {req.summary} ({age}s ago)")
    await query.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /start ────────────────────────────────────────────────────────────────────

@auth
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pending = approval_queue.pending_count()
    pending_badge = f" 🔴 {pending} pending" if pending else ""
    kb = [
        [InlineKeyboardButton(f"⏳ Pending Approvals{pending_badge}", callback_data="pending")],
        [InlineKeyboardButton("📊 Status",        callback_data="status"),
         InlineKeyboardButton("💼 Positions",     callback_data="hlpos")],
        [InlineKeyboardButton("🤖 Auto-Trade",    callback_data="toggle_trade"),
         InlineKeyboardButton("🎰 Auto-Bet",      callback_data="toggle_bet")],
        [InlineKeyboardButton("💰 Account",       callback_data="account"),
         InlineKeyboardButton("📜 Signals",       callback_data="signals")],
        [InlineKeyboardButton("📈 Analyze",       callback_data="analyze_prompt"),
         InlineKeyboardButton("🔍 Bug Check",     callback_data="bugcheck")],
        [InlineKeyboardButton("🔮 Polymarket",    callback_data="poly_search"),
         InlineKeyboardButton("📊 Kalshi",        callback_data="kalshi_search")],
        [InlineKeyboardButton("🧠 Metaculus",     callback_data="meta_search"),
         InlineKeyboardButton("📐 Prob",          callback_data="prob_prompt")],
    ]
    await update.message.reply_text(
        "🤖 *Trading & Prediction Bot*\n\n"
        "⚠️ _All trades and bets require your approval before execution._\n\n"
        "Choose an action:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── /pending ──────────────────────────────────────────────────────────────────

@auth
async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pending = approval_queue.get_pending()
    if not pending:
        await update.message.reply_text("✅ No pending approvals.")
        return
    lines = [f"*{len(pending)} pending approval(s):*\n"]
    for req in pending:
        age = int(__import__("time").time() - req.created_at)
        lines.append(f"• `{req.id}` — {req.summary} ({age}s ago)")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /status ───────────────────────────────────────────────────────────────────

@auth
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pending = approval_queue.pending_count()
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    text = (
        f"*Bot Status*\n"
        f"Auto-Trade: {'✅ ON' if state.auto_trade else '❌ OFF'}\n"
        f"Auto-Bet:   {'✅ ON' if state.auto_bet else '❌ OFF'}\n"
        f"Pending Approvals: *{pending}*\n"
        f"Open Positions: {len(state.open_positions())}\n"
        f"Signals Received: {len(state.signal_log)}\n"
        f"Bets Placed: {len(state.bet_log)}"
    )
    await msg.reply_text(text, parse_mode="Markdown")


# ── /account ──────────────────────────────────────────────────────────────────

@auth
async def cmd_account(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("⏳ Fetching Hyperliquid account…")
    try:
        summary = hl.get_account_summary()
        positions = summary.get("positions", [])
        pos_lines = ""
        for p in positions:
            pos_lines += (
                f"\n  {p['side']} {p['size']} {p['coin']} "
                f"@ ${p.get('entry_px','?')} | PnL: {p.get('unrealized_pnl','?')}"
            )
        text = (
            f"*Hyperliquid Account*\n"
            f"Value: `${summary.get('account_value','?')}`\n"
            f"Margin Used: `${summary.get('total_margin_used','?')}`\n"
            f"Notional: `${summary.get('total_ntl_pos','?')}`\n"
            f"Positions ({len(positions)}):{pos_lines or ' none'}"
        )
        await msg.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}")


# ── /hlpos ────────────────────────────────────────────────────────────────────

@auth
async def cmd_hlpos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    try:
        summary = hl.get_account_summary()
        positions = summary.get("positions", [])
        if not positions:
            await msg.reply_text("No open Hyperliquid positions.")
            return
        lines = []
        for p in positions:
            lines.append(
                f"*{p['coin']}* {p['side']} ×{p.get('leverage','?')}\n"
                f"  Size: {p['size']} | Entry: ${p.get('entry_px','?')}\n"
                f"  uPnL: {p.get('unrealized_pnl','?')}"
            )
        await msg.reply_text("\n\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ Error: {e}")


# ── /signals ──────────────────────────────────────────────────────────────────

@auth
async def cmd_signals(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    logs = state.signal_log[:5]
    if not logs:
        await msg.reply_text("No signals received yet.")
        return
    lines = [
        f"[{s['indicator']}] {s['action'].upper()} {s['symbol']} @ {s['price']} ({s['tf']})"
        for s in logs
    ]
    await msg.reply_text("*Last 5 Signals:*\n" + "\n".join(lines), parse_mode="Markdown")


# ── Auto-trade / auto-bet toggles ─────────────────────────────────────────────

@auth
async def cmd_toggle_trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    state.auto_trade = not state.auto_trade
    status = "✅ ON" if state.auto_trade else "❌ OFF"
    note   = "\n_Signals will still require your Telegram approval._" if state.auto_trade else ""
    await msg.reply_text(f"Auto-Trade is now {status}{note}", parse_mode="Markdown")


@auth
async def cmd_toggle_bet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    state.auto_bet = not state.auto_bet
    status = "✅ ON" if state.auto_bet else "❌ OFF"
    await msg.reply_text(f"Auto-Bet is now {status}", parse_mode="Markdown")


# ── /long <coin> <size> [leverage] — approval-gated ──────────────────────────

@auth
async def cmd_long(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /long <coin> <size> [leverage]")
        return
    coin = ctx.args[0].upper()
    size = float(ctx.args[1])
    leverage = int(ctx.args[2]) if len(ctx.args) > 2 else None
    await update.message.reply_text(f"⏳ Requesting approval for LONG {size} {coin}…")

    def _run():
        from trading.executor import manual_long
        import asyncio
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(manual_long(coin, size, leverage))
        loop.close()
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown"),
            asyncio.get_event_loop(),
        )
    threading.Thread(target=_run, daemon=True).start()


# ── /short <coin> <size> [leverage] — approval-gated ─────────────────────────

@auth
async def cmd_short(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /short <coin> <size> [leverage]")
        return
    coin = ctx.args[0].upper()
    size = float(ctx.args[1])
    leverage = int(ctx.args[2]) if len(ctx.args) > 2 else None
    await update.message.reply_text(f"⏳ Requesting approval for SHORT {size} {coin}…")

    async def _do():
        from trading.executor import manual_short
        result = await manual_short(coin, size, leverage)
        await _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown")
    asyncio.create_task(_do())


# ── /close <coin> — approval-gated ────────────────────────────────────────────

@auth
async def cmd_close(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /close <coin>")
        return
    coin = ctx.args[0].upper()
    await update.message.reply_text(f"⏳ Requesting approval to close {coin}…")

    async def _do():
        from trading.executor import manual_close
        result = await manual_close(coin)
        await _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown")
    asyncio.create_task(_do())


# ── /leverage <coin> <n> ──────────────────────────────────────────────────────

@auth
async def cmd_leverage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /leverage <coin> <n>")
        return
    coin, lev = ctx.args[0].upper(), int(ctx.args[1])
    try:
        hl.set_leverage(coin, lev)
        await update.message.reply_text(f"✅ Leverage set to {lev}× for {coin}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /price <coin> ─────────────────────────────────────────────────────────────

@auth
async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /price <coin>")
        return
    coin = ctx.args[0].upper()
    try:
        mids = hl.get_all_mids()
        p = mids.get(coin)
        if p:
            await update.message.reply_text(f"*{coin}*: `${p:,.4f}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"Unknown coin: {coin}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /analyze <coin> [tf] ──────────────────────────────────────────────────────

@auth
async def cmd_analyze(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /analyze <coin> [tf]  e.g. /analyze BTC 1h")
        return
    coin = ctx.args[0].upper()
    tf   = ctx.args[1] if len(ctx.args) > 1 else "1h"
    await update.message.reply_text(f"⏳ Analyzing {coin} {tf}…")
    try:
        report = ma.analyze(coin, tf)
        await update.message.reply_text(report.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


# ── /bugcheck / /bugfix ───────────────────────────────────────────────────────

@auth
async def cmd_bugcheck(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    await msg.reply_text("🔍 Running bug check…")
    try:
        result = run_bug_check(auto_remediate=False)
        await msg.reply_text(result.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await msg.reply_text(f"❌ {e}")


@auth
async def cmd_bugfix(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 Running bug check with auto-fix…")
    try:
        result = run_bug_check(auto_remediate=True)
        await update.message.reply_text(result.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


# ── /prob ─────────────────────────────────────────────────────────────────────

@auth
async def cmd_prob(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /prob <mkt_price> <our_est> [YES|NO] [platform]\n"
            "Example: /prob 0.35 0.55 YES polymarket"
        )
        return
    market_raw = float(ctx.args[0])
    our_est    = float(ctx.args[1])
    side       = ctx.args[2].upper() if len(ctx.args) > 2 else "YES"
    platform   = ctx.args[3].lower() if len(ctx.args) > 3 else "polymarket"
    opp = prob.score_opportunity(platform, "manual", "Manual analysis", market_raw, our_est, side)
    await update.message.reply_text(opp.to_telegram(), parse_mode="Markdown")


# ── /cryptoprob ───────────────────────────────────────────────────────────────

@auth
async def cmd_cryptoprob(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 3:
        await update.message.reply_text("Usage: /cryptoprob <coin> <target> <days>")
        return
    coin, target, days = ctx.args[0].upper(), float(ctx.args[1]), int(ctx.args[2])
    try:
        mids = hl.get_all_mids()
        current = mids.get(coin, 0)
        p = prob.estimate_crypto_market_prob(current, target, days)
        direction = "above" if target > current else "below"
        await update.message.reply_text(
            f"*{coin} Probability*\n"
            f"Current: `${current:,.2f}` → Target: `${target:,.2f}` ({direction})\n"
            f"Timeframe: `{days} days`\n"
            f"Estimated probability: `{p*100:.1f}%`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


# ── Polymarket — approval-gated ───────────────────────────────────────────────

@auth
async def cmd_poly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args) if ctx.args else "crypto"
    try:
        markets = polymarket.search_markets(query, limit=5)
        if not markets:
            await update.message.reply_text("No markets found.")
            return
        lines = [
            f"*{m['question']}*\nYES: {m['yes_price']} | NO: {m['no_price']}\nID: `{m['id']}`\n"
            for m in markets
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


@auth
async def cmd_polybuy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 4:
        await update.message.reply_text("Usage: /polybuy <token_id> <YES|NO> <price> <size_usdc>")
        return
    token_id, side, price, size = ctx.args[0], ctx.args[1], float(ctx.args[2]), float(ctx.args[3])
    await update.message.reply_text(f"⏳ Requesting approval for Polymarket {side} bet…")

    async def execute():
        result = polymarket.place_order(token_id, side, price, size)
        oid = result.get("orderID") or "?"
        state.log_bet({"platform": "polymarket", "token_id": token_id, "side": side})
        return f"✅ Polymarket order placed\nOrder ID: `{oid}`"

    async def _do():
        from trading.executor import request_bet_approval
        result = await request_bet_approval(
            "polymarket", token_id, f"{side} @ {price}", side, price, size, execute
        )
        await _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown")
    asyncio.create_task(_do())


# ── Kalshi — approval-gated ───────────────────────────────────────────────────

@auth
async def cmd_kalshi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args) if ctx.args else ""
    try:
        markets = kalshi.search_markets(query, limit=5)
        if not markets:
            await update.message.reply_text("No markets found.")
            return
        lines = [
            f"*{m['title']}*\nYES ask: {m['yes_ask']}¢ | NO ask: {m['no_ask']}¢\nTicker: `{m['ticker']}`\n"
            for m in markets
        ]
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


@auth
async def cmd_kalshiorder(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 5:
        await update.message.reply_text("Usage: /kalshiorder <ticker> <yes|no> <buy|sell> <count> <cents>")
        return
    ticker, side, action = ctx.args[0], ctx.args[1], ctx.args[2]
    count, price = int(ctx.args[3]), int(ctx.args[4])
    await update.message.reply_text(f"⏳ Requesting approval for Kalshi {side} order…")

    async def execute():
        result = kalshi.place_order(ticker, side, action, count, price)
        oid = result.get("order", {}).get("id", "?")
        state.log_bet({"platform": "kalshi", "ticker": ticker, "side": side})
        return f"✅ Kalshi order placed\nOrder ID: `{oid}`"

    async def _do():
        from trading.executor import request_bet_approval
        result = await request_bet_approval(
            "kalshi", ticker, f"{ticker} {side} {action} ×{count} @ {price}¢",
            side, price / 100, count, execute
        )
        await _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown")
    asyncio.create_task(_do())


# ── Metaculus ─────────────────────────────────────────────────────────────────

@auth
async def cmd_meta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args) if ctx.args else "crypto"
    try:
        questions = metaculus.search_questions(query, limit=5)
        if not questions:
            await update.message.reply_text("No questions found.")
            return
        lines = []
        for q in questions:
            p_val = q["community_prediction"]
            p_str = f"{p_val*100:.1f}%" if p_val else "N/A"
            lines.append(
                f"*{q['title']}*\nCommunity: {p_str}\n"
                f"ID: `{q['id']}` | [View]({q['url']})\n"
            )
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True
        )
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


@auth
async def cmd_metapredict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /metapredict <question_id> <probability 0-1>")
        return
    qid, p = int(ctx.args[0]), float(ctx.args[1])
    await update.message.reply_text(f"⏳ Requesting approval for Metaculus forecast…")

    async def execute():
        metaculus.submit_prediction(qid, p)
        return f"✅ Metaculus forecast submitted: Q{qid} = {p*100:.1f}%"

    async def _do():
        from trading.executor import request_bet_approval
        result = await request_bet_approval(
            "metaculus", str(qid), f"Q{qid} forecast = {p*100:.1f}%",
            "forecast", p, 0, execute
        )
        await _bot_app.bot.send_message(cfg.TELEGRAM_ALLOWED_USER_ID, result, parse_mode="Markdown")
    asyncio.create_task(_do())


# ── /help ─────────────────────────────────────────────────────────────────────

@auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*All trades and bets require Telegram approval.*\n\n"
        "*Approval:*\n"
        "/pending — view pending approvals\n\n"
        "*Hyperliquid Perps:*\n"
        "/account /hlpos /price <coin>\n"
        "/long <coin> <size> [lev]\n"
        "/short <coin> <size> [lev]\n"
        "/close <coin>\n"
        "/leverage <coin> <n>\n\n"
        "*Auto-Trading:*\n"
        "/autotrade /autobet /signals\n\n"
        "*Analysis:*\n"
        "/analyze <coin> [tf]\n"
        "/cryptoprob <coin> <target> <days>\n"
        "/prob <mkt> <est> [YES|NO] [platform]\n\n"
        "*Bug Checker:*\n"
        "/bugcheck /bugfix\n\n"
        "*Prediction Markets:*\n"
        "/poly <query>\n"
        "/polybuy <id> <YES|NO> <price> <size>\n"
        "/kalshi <query>\n"
        "/kalshiorder <ticker> <yes|no> <buy|sell> <count> <¢>\n"
        "/meta <query>\n"
        "/metapredict <id> <0-1>",
        parse_mode="Markdown",
    )


# ── App builder ───────────────────────────────────────────────────────────────

def build_app():
    global _bot_app
    app = ApplicationBuilder().token(cfg.TELEGRAM_BOT_TOKEN).build()
    _bot_app = app

    # Register approval notifier with the queue
    approval_queue.set_notifier(_send_approval_request)

    handlers = [
        ("start",        cmd_start),
        ("help",         cmd_help),
        ("pending",      cmd_pending),
        ("status",       cmd_status),
        ("account",      cmd_account),
        ("hlpos",        cmd_hlpos),
        ("long",         cmd_long),
        ("short",        cmd_short),
        ("close",        cmd_close),
        ("leverage",     cmd_leverage),
        ("price",        cmd_price),
        ("analyze",      cmd_analyze),
        ("bugcheck",     cmd_bugcheck),
        ("bugfix",       cmd_bugfix),
        ("prob",         cmd_prob),
        ("cryptoprob",   cmd_cryptoprob),
        ("autotrade",    cmd_toggle_trade),
        ("autobet",      cmd_toggle_bet),
        ("signals",      cmd_signals),
        ("poly",         cmd_poly),
        ("polybuy",      cmd_polybuy),
        ("kalshi",       cmd_kalshi),
        ("kalshiorder",  cmd_kalshiorder),
        ("meta",         cmd_meta),
        ("metapredict",  cmd_metapredict),
    ]
    for name, handler in handlers:
        app.add_handler(CommandHandler(name, handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app
