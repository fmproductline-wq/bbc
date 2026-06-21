"""Telegram bot frontend — trading, prediction markets, analysis, bug checker."""
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
from predictions import polymarket, kalshi, metaculus
from analysis import market_analyzer as ma
from analysis import probability as prob
from agents.bug_checker import run_bug_check


def auth(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != cfg.TELEGRAM_ALLOWED_USER_ID:
            await update.message.reply_text("⛔ Unauthorized")
            return
        return await func(update, ctx)
    return wrapper


# ── /start ──────────────────────────────────────────────────────────────────

@auth
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📊 Status", callback_data="status"),
         InlineKeyboardButton("💼 HL Positions", callback_data="hlpos")],
        [InlineKeyboardButton("🤖 Auto-Trade ON/OFF", callback_data="toggle_trade"),
         InlineKeyboardButton("🎰 Auto-Bet ON/OFF", callback_data="toggle_bet")],
        [InlineKeyboardButton("💰 Account Summary", callback_data="account"),
         InlineKeyboardButton("📜 Signal Log", callback_data="signals")],
        [InlineKeyboardButton("📈 Analyze Market", callback_data="analyze_prompt"),
         InlineKeyboardButton("🔍 Bug Check", callback_data="bugcheck")],
        [InlineKeyboardButton("🔮 Polymarket", callback_data="poly_search"),
         InlineKeyboardButton("📊 Kalshi", callback_data="kalshi_search")],
        [InlineKeyboardButton("🧠 Metaculus", callback_data="meta_search"),
         InlineKeyboardButton("📐 Prob Analyzer", callback_data="prob_prompt")],
    ]
    await update.message.reply_text(
        "🤖 *Trading & Prediction Bot*\n\nChoose an action:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown",
    )


# ── /status ─────────────────────────────────────────────────────────────────

@auth
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    open_pos = state.open_positions()
    text = (
        f"*Bot Status*\n"
        f"Auto-Trade: {'✅ ON' if state.auto_trade else '❌ OFF'}\n"
        f"Auto-Bet:   {'✅ ON' if state.auto_bet else '❌ OFF'}\n"
        f"Open Positions: {len(open_pos)}\n"
        f"Signals Received: {len(state.signal_log)}\n"
        f"Bets Placed: {len(state.bet_log)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── /account — Hyperliquid account summary ────────────────────────────────────

@auth
async def cmd_account(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching Hyperliquid account…")
    try:
        summary = hl.get_account_summary()
        positions = summary.get("positions", [])
        pos_lines = ""
        for p in positions:
            pnl = p.get("unrealized_pnl", "?")
            pos_lines += (
                f"\n  {p['side']} {p['size']} {p['coin']} "
                f"@ ${p.get('entry_px', '?')} | PnL: {pnl}"
            )
        text = (
            f"*Hyperliquid Account*\n"
            f"Value: `${summary.get('account_value', '?')}`\n"
            f"Margin Used: `${summary.get('total_margin_used', '?')}`\n"
            f"Notional: `${summary.get('total_ntl_pos', '?')}`\n"
            f"Positions ({len(positions)}):{pos_lines or ' none'}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /hlpos — live Hyperliquid positions ───────────────────────────────────────

@auth
async def cmd_hlpos(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        summary = hl.get_account_summary()
        positions = summary.get("positions", [])
        if not positions:
            await update.message.reply_text("No open Hyperliquid positions.")
            return
        lines = []
        for p in positions:
            lines.append(
                f"*{p['coin']}* {p['side']} x{p.get('leverage', '?')}\n"
                f"  Size: {p['size']} | Entry: ${p.get('entry_px', '?')}\n"
                f"  uPnL: {p.get('unrealized_pnl', '?')}"
            )
        await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /signals ──────────────────────────────────────────────────────────────────

@auth
async def cmd_signals(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logs = state.signal_log[:5]
    if not logs:
        await update.message.reply_text("No signals received yet.")
        return
    lines = [
        f"[{s['indicator']}] {s['action'].upper()} {s['symbol']} @ {s['price']} ({s['tf']})"
        for s in logs
    ]
    await update.message.reply_text("*Last 5 Signals:*\n" + "\n".join(lines), parse_mode="Markdown")


# ── /autotrade / /autobet ─────────────────────────────────────────────────────

@auth
async def cmd_toggle_trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state.auto_trade = not state.auto_trade
    await update.message.reply_text(f"Auto-Trade is now {'✅ ON' if state.auto_trade else '❌ OFF'}")


@auth
async def cmd_toggle_bet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state.auto_bet = not state.auto_bet
    await update.message.reply_text(f"Auto-Bet is now {'✅ ON' if state.auto_bet else '❌ OFF'}")


# ── /long <coin> <size> [leverage] ────────────────────────────────────────────

@auth
async def cmd_long(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /long <coin> <size>  e.g. /long BTC 0.001")
        return
    coin, size = ctx.args[0].upper(), float(ctx.args[1])
    if len(ctx.args) >= 3:
        try:
            hl.set_leverage(coin, int(ctx.args[2]))
        except Exception:
            pass
    await update.message.reply_text(f"⏳ Opening LONG {size} {coin}…")
    try:
        result = hl.market_open(coin, True, size)
        await update.message.reply_text(f"✅ LONG opened\n`{result}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /short <coin> <size> ──────────────────────────────────────────────────────

@auth
async def cmd_short(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /short <coin> <size>  e.g. /short ETH 0.1")
        return
    coin, size = ctx.args[0].upper(), float(ctx.args[1])
    await update.message.reply_text(f"⏳ Opening SHORT {size} {coin}…")
    try:
        result = hl.market_open(coin, False, size)
        await update.message.reply_text(f"✅ SHORT opened\n`{result}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /close <coin> ─────────────────────────────────────────────────────────────

@auth
async def cmd_close(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /close <coin>  e.g. /close BTC")
        return
    coin = ctx.args[0].upper()
    await update.message.reply_text(f"⏳ Closing {coin} position…")
    try:
        result = hl.market_close(coin)
        for pos in state.open_positions():
            if pos.token_out == coin:
                pos.closed = True
        await update.message.reply_text(f"✅ Position closed\n`{result}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /leverage <coin> <n> ──────────────────────────────────────────────────────

@auth
async def cmd_leverage(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /leverage <coin> <n>  e.g. /leverage BTC 5")
        return
    coin, lev = ctx.args[0].upper(), int(ctx.args[1])
    try:
        hl.set_leverage(coin, lev)
        await update.message.reply_text(f"✅ Leverage set to {lev}x for {coin}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /price <coin> ─────────────────────────────────────────────────────────────

@auth
async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Usage: /price <coin>  e.g. /price BTC")
        return
    coin = ctx.args[0].upper()
    try:
        mids = hl.get_all_mids()
        price = mids.get(coin)
        if price is None:
            await update.message.reply_text(f"Unknown coin: {coin}")
        else:
            await update.message.reply_text(f"*{coin}* mid price: `${price:,.4f}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /analyze <coin> [timeframe] ───────────────────────────────────────────────

@auth
async def cmd_analyze(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /analyze <coin> [timeframe]\n"
            "Example: /analyze BTC 1h\n"
            "Timeframes: 1m 5m 15m 1h 4h 1d"
        )
        return
    coin = ctx.args[0].upper()
    interval = ctx.args[1] if len(ctx.args) > 1 else "1h"
    await update.message.reply_text(f"⏳ Analyzing {coin} {interval}…")
    try:
        report = ma.analyze(coin, interval)
        await update.message.reply_text(report.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Analysis failed: {e}")


# ── /bugcheck ─────────────────────────────────────────────────────────────────

@auth
async def cmd_bugcheck(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Running bug check…")
    try:
        result = run_bug_check(auto_remediate=False)
        await update.message.reply_text(result.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Bug check error: {e}")


# ── /bugfix ────────────────────────────────────────────────────────────────────

@auth
async def cmd_bugfix(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔧 Running bug check with auto-remediation…")
    try:
        result = run_bug_check(auto_remediate=True)
        await update.message.reply_text(result.to_telegram(), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /prob <market_price 0-1> <our_estimate 0-1> [YES|NO] ─────────────────────

@auth
async def cmd_prob(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /prob <market_price> <our_estimate> [YES|NO] [platform]\n"
            "Example: /prob 0.35 0.55 YES polymarket\n"
            "         /prob 42 60 YES kalshi   ← kalshi uses cents"
        )
        return
    market_raw = float(ctx.args[0])
    our_est = float(ctx.args[1])
    side = ctx.args[2].upper() if len(ctx.args) > 2 else "YES"
    platform = ctx.args[3].lower() if len(ctx.args) > 3 else "polymarket"

    opp = prob.score_opportunity(
        platform=platform,
        market_id="manual",
        question="Manual analysis",
        market_price_raw=market_raw,
        our_estimate=our_est,
        side=side,
    )
    await update.message.reply_text(opp.to_telegram(), parse_mode="Markdown")


# ── /cryptoprob <coin> <target_price> <days> ─────────────────────────────────

@auth
async def cmd_cryptoprob(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 3:
        await update.message.reply_text(
            "Usage: /cryptoprob <coin> <target_price> <days>\n"
            "Example: /cryptoprob BTC 100000 180"
        )
        return
    coin = ctx.args[0].upper()
    target = float(ctx.args[1])
    days = int(ctx.args[2])

    try:
        mids = hl.get_all_mids()
        current = mids.get(coin, 0)
        if current <= 0:
            await update.message.reply_text(f"Cannot get price for {coin}")
            return
        p = prob.estimate_crypto_market_prob(current, target, days)
        direction = "above" if target > current else "below"
        await update.message.reply_text(
            f"*{coin} Probability Estimate*\n"
            f"Current: `${current:,.2f}`\n"
            f"Target: `${target:,.2f}` ({direction})\n"
            f"Timeframe: `{days} days`\n\n"
            f"📊 Estimated probability: `{p*100:.1f}%`\n"
            f"_(log-normal model, 80% annualized vol assumed)_",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── Polymarket commands ───────────────────────────────────────────────────────

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
        await update.message.reply_text(f"❌ Polymarket error: {e}")


@auth
async def cmd_polybuy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 4:
        await update.message.reply_text("Usage: /polybuy <token_id> <YES|NO> <price 0-1> <size_usdc>")
        return
    token_id, side, price, size = ctx.args[0], ctx.args[1], float(ctx.args[2]), float(ctx.args[3])
    try:
        result = polymarket.place_order(token_id, side, price, size)
        order_id = result.get("orderID") or result.get("order_id") or "?"
        await update.message.reply_text(f"✅ Polymarket order placed\nOrder ID: `{order_id}`", parse_mode="Markdown")
        state.log_bet({"platform": "polymarket", "token_id": token_id, "side": side, "price": price, "size": size})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── Kalshi commands ───────────────────────────────────────────────────────────

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
        await update.message.reply_text(f"❌ Kalshi error: {e}")


@auth
async def cmd_kalshiorder(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 5:
        await update.message.reply_text("Usage: /kalshiorder <ticker> <yes|no> <buy|sell> <count> <price_cents>")
        return
    ticker, side, action, count, price = ctx.args[0], ctx.args[1], ctx.args[2], int(ctx.args[3]), int(ctx.args[4])
    try:
        result = kalshi.place_order(ticker, side, action, count, price)
        order_id = result.get("order", {}).get("id", "?")
        await update.message.reply_text(f"✅ Kalshi order placed\nOrder ID: `{order_id}`", parse_mode="Markdown")
        state.log_bet({"platform": "kalshi", "ticker": ticker, "side": side, "count": count, "price": price})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── Metaculus commands ────────────────────────────────────────────────────────

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
            prob_val = q["community_prediction"]
            prob_str = f"{prob_val*100:.1f}%" if prob_val else "N/A"
            lines.append(
                f"*{q['title']}*\nCommunity: {prob_str}\n"
                f"ID: `{q['id']}` | [View]({q['url']})\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Metaculus error: {e}")


@auth
async def cmd_metapredict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /metapredict <question_id> <probability 0-1>")
        return
    qid, p = int(ctx.args[0]), float(ctx.args[1])
    try:
        metaculus.submit_prediction(qid, p)
        await update.message.reply_text(f"✅ Forecast submitted: Q{qid} = {p*100:.1f}%")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /help ─────────────────────────────────────────────────────────────────────

@auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Hyperliquid Perps:*\n"
        "/account — account summary & positions\n"
        "/hlpos — live open positions\n"
        "/long <coin> <size> [lev] — open long\n"
        "/short <coin> <size> — open short\n"
        "/close <coin> — close position\n"
        "/leverage <coin> <n> — set leverage\n"
        "/price <coin> — mid price\n\n"
        "*Auto-Trading:*\n"
        "/autotrade — toggle auto-trade\n"
        "/autobet — toggle auto-bet\n"
        "/signals — last 5 TV signals\n\n"
        "*Analysis:*\n"
        "/analyze <coin> [tf] — full TA report\n"
        "/cryptoprob <coin> <target> <days> — log-normal price probability\n\n"
        "*Probability Analyzer:*\n"
        "/prob <mkt_price> <our_est> [YES|NO] [platform]\n\n"
        "*Bug Checker Agent:*\n"
        "/bugcheck — scan for issues\n"
        "/bugfix — scan + auto-remediate\n\n"
        "*Prediction Markets:*\n"
        "/poly <query> | /polybuy <id> <YES|NO> <price> <size>\n"
        "/kalshi <query> | /kalshiorder <ticker> <yes|no> <buy|sell> <count> <¢>\n"
        "/meta <query> | /metapredict <id> <0-1>\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Inline callbacks ──────────────────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    dispatch = {
        "status": cmd_status,
        "hlpos": cmd_hlpos,
        "account": cmd_account,
        "signals": cmd_signals,
        "toggle_trade": cmd_toggle_trade,
        "toggle_bet": cmd_toggle_bet,
        "bugcheck": cmd_bugcheck,
    }
    if data in dispatch:
        await dispatch[data](update, ctx)
    elif data == "analyze_prompt":
        await query.message.reply_text("Send: /analyze <coin> [tf]  e.g. /analyze BTC 1h")
    elif data == "prob_prompt":
        await query.message.reply_text("Send: /prob <mkt_price> <our_est> [YES|NO] [platform]")
    elif data == "poly_search":
        await query.message.reply_text("Send: /poly <keyword>  e.g. /poly bitcoin")
    elif data == "kalshi_search":
        await query.message.reply_text("Send: /kalshi <keyword>  e.g. /kalshi bitcoin")
    elif data == "meta_search":
        await query.message.reply_text("Send: /meta <keyword>  e.g. /meta inflation")


# ── App builder ───────────────────────────────────────────────────────────────

def build_app():
    app = ApplicationBuilder().token(cfg.TELEGRAM_BOT_TOKEN).build()

    handlers = [
        ("start", cmd_start), ("help", cmd_help), ("status", cmd_status),
        ("account", cmd_account), ("hlpos", cmd_hlpos),
        ("long", cmd_long), ("short", cmd_short), ("close", cmd_close),
        ("leverage", cmd_leverage), ("price", cmd_price),
        ("analyze", cmd_analyze),
        ("bugcheck", cmd_bugcheck), ("bugfix", cmd_bugfix),
        ("prob", cmd_prob), ("cryptoprob", cmd_cryptoprob),
        ("autotrade", cmd_toggle_trade), ("autobet", cmd_toggle_bet),
        ("signals", cmd_signals),
        ("poly", cmd_poly), ("polybuy", cmd_polybuy),
        ("kalshi", cmd_kalshi), ("kalshiorder", cmd_kalshiorder),
        ("meta", cmd_meta), ("metapredict", cmd_metapredict),
    ]
    for name, handler in handlers:
        app.add_handler(CommandHandler(name, handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app
