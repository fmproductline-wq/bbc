"""Telegram bot frontend for the trading + prediction bot."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from loguru import logger
from config import cfg
from trading.state import state
from trading.wallet import get_balance_native, get_token_balance
from trading.dex import execute_swap
from predictions import polymarket, kalshi, metaculus


def auth(func):
    """Decorator: only allow configured user."""
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
         InlineKeyboardButton("💼 Positions", callback_data="positions")],
        [InlineKeyboardButton("🤖 Auto-Trade ON/OFF", callback_data="toggle_trade"),
         InlineKeyboardButton("🎰 Auto-Bet ON/OFF", callback_data="toggle_bet")],
        [InlineKeyboardButton("💰 Wallet Balance", callback_data="balance"),
         InlineKeyboardButton("📜 Signal Log", callback_data="signals")],
        [InlineKeyboardButton("🔮 Search Polymarket", callback_data="poly_search"),
         InlineKeyboardButton("📈 Search Kalshi", callback_data="kalshi_search")],
        [InlineKeyboardButton("🧠 Metaculus", callback_data="meta_search")],
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


# ── /balance ─────────────────────────────────────────────────────────────────

@auth
async def cmd_balance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        bal = get_balance_native()
        chain = cfg.DEFAULT_CHAIN
        native_sym = {"ethereum": "ETH", "polygon": "MATIC", "bsc": "BNB"}.get(chain, "ETH")
        await update.message.reply_text(
            f"💰 Wallet Balance\n`{cfg.WALLET_ADDRESS[:8]}...`\n"
            f"{chain.capitalize()}: `{bal:.6f} {native_sym}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /positions ────────────────────────────────────────────────────────────────

@auth
async def cmd_positions(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    open_pos = state.open_positions()
    if not open_pos:
        await update.message.reply_text("No open positions.")
        return
    lines = []
    for i, p in enumerate(open_pos, 1):
        lines.append(
            f"{i}. {p.token_out[:8]}… on {p.chain}\n"
            f"   Entry: {p.entry_price} | Stop: {p.stop_loss:.4f}\n"
            f"   Tx: `{p.tx_hash[:16]}…`"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


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


# ── /autotrade toggle ─────────────────────────────────────────────────────────

@auth
async def cmd_toggle_trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state.auto_trade = not state.auto_trade
    status = "✅ ON" if state.auto_trade else "❌ OFF"
    await update.message.reply_text(f"Auto-Trade is now {status}")


# ── /autobet toggle ───────────────────────────────────────────────────────────

@auth
async def cmd_toggle_bet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    state.auto_bet = not state.auto_bet
    status = "✅ ON" if state.auto_bet else "❌ OFF"
    await update.message.reply_text(f"Auto-Bet is now {status}")


# ── /poly <query> ─────────────────────────────────────────────────────────────

@auth
async def cmd_poly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args) if ctx.args else "crypto"
    try:
        markets = polymarket.search_markets(query, limit=5)
        if not markets:
            await update.message.reply_text("No markets found.")
            return
        lines = []
        for m in markets:
            lines.append(
                f"*{m['question']}*\n"
                f"YES: {m['yes_price']} | NO: {m['no_price']}\n"
                f"ID: `{m['id']}`\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Polymarket error: {e}")


# ── /polybuy <token_id> <YES|NO> <price 0-1> <size USDC> ─────────────────────

@auth
async def cmd_polybuy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 4:
        await update.message.reply_text("Usage: /polybuy <token_id> <YES|NO> <price> <size>")
        return
    token_id, side, price, size = ctx.args[0], ctx.args[1], float(ctx.args[2]), float(ctx.args[3])
    try:
        result = polymarket.place_order(token_id, side, price, size)
        order_id = result.get("orderID") or result.get("order_id") or "?"
        await update.message.reply_text(f"✅ Polymarket order placed\nOrder ID: `{order_id}`", parse_mode="Markdown")
        state.log_bet({"platform": "polymarket", "token_id": token_id, "side": side, "price": price, "size": size})
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /kalshi <query> ───────────────────────────────────────────────────────────

@auth
async def cmd_kalshi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args) if ctx.args else ""
    try:
        markets = kalshi.search_markets(query, limit=5)
        if not markets:
            await update.message.reply_text("No markets found.")
            return
        lines = []
        for m in markets:
            lines.append(
                f"*{m['title']}*\n"
                f"YES ask: {m['yes_ask']}¢ | NO ask: {m['no_ask']}¢\n"
                f"Ticker: `{m['ticker']}`\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Kalshi error: {e}")


# ── /kalshiorder <ticker> <yes|no> <buy|sell> <count> <price_cents> ───────────

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


# ── /meta <query> ─────────────────────────────────────────────────────────────

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
            prob = q["community_prediction"]
            prob_str = f"{prob*100:.1f}%" if prob else "N/A"
            lines.append(
                f"*{q['title']}*\n"
                f"Community: {prob_str}\n"
                f"ID: `{q['id']}` | [View]({q['url']})\n"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"❌ Metaculus error: {e}")


# ── /metapredict <question_id> <probability 0-1> ─────────────────────────────

@auth
async def cmd_metapredict(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("Usage: /metapredict <question_id> <probability>")
        return
    qid, prob = int(ctx.args[0]), float(ctx.args[1])
    try:
        metaculus.submit_prediction(qid, prob)
        await update.message.reply_text(f"✅ Forecast submitted: question {qid} = {prob*100:.1f}%")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ── /swap <token_in> <token_out> <amount> [chain] ────────────────────────────

@auth
async def cmd_swap(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args or len(ctx.args) < 3:
        await update.message.reply_text(
            "Usage: /swap <token_in> <token_out> <amount> [chain]\n"
            "Example: /swap NATIVE WBTC 0.5 polygon"
        )
        return
    token_in = ctx.args[0]
    token_out = ctx.args[1]
    amount = float(ctx.args[2])
    chain = ctx.args[3] if len(ctx.args) > 3 else cfg.DEFAULT_CHAIN
    await update.message.reply_text(f"⏳ Executing swap {amount} {token_in} → {token_out} on {chain}…")
    try:
        from trading.executor import resolve_token
        from trading.dex import NATIVE_TOKEN
        t_in = NATIVE_TOKEN if token_in.upper() == "NATIVE" else resolve_token(token_in, chain)
        t_out = NATIVE_TOKEN if token_out.upper() == "NATIVE" else resolve_token(token_out, chain)
        tx = execute_swap(t_in, t_out, amount, chain=chain)
        await update.message.reply_text(f"✅ Swap confirmed\nTx: `{tx}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Swap failed: {e}")


# ── Inline button callbacks ───────────────────────────────────────────────────

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    fake_update = update
    if data == "status":
        await cmd_status(fake_update, ctx)
    elif data == "positions":
        await cmd_positions(fake_update, ctx)
    elif data == "balance":
        await cmd_balance(fake_update, ctx)
    elif data == "signals":
        await cmd_signals(fake_update, ctx)
    elif data == "toggle_trade":
        await cmd_toggle_trade(fake_update, ctx)
    elif data == "toggle_bet":
        await cmd_toggle_bet(fake_update, ctx)
    elif data == "poly_search":
        await query.message.reply_text("Send: /poly <keyword>  e.g. /poly bitcoin")
    elif data == "kalshi_search":
        await query.message.reply_text("Send: /kalshi <keyword>  e.g. /kalshi bitcoin")
    elif data == "meta_search":
        await query.message.reply_text("Send: /meta <keyword>  e.g. /meta inflation")


# ── help ──────────────────────────────────────────────────────────────────────

@auth
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Commands:*\n"
        "/start — main menu\n"
        "/status — bot status\n"
        "/balance — wallet balance\n"
        "/positions — open positions\n"
        "/signals — last 5 TradingView signals\n"
        "/autotrade — toggle auto-trading\n"
        "/autobet — toggle auto-betting\n"
        "/swap <in> <out> <amount> [chain] — manual swap\n\n"
        "*Polymarket:*\n"
        "/poly <query> — search markets\n"
        "/polybuy <token_id> <YES|NO> <price> <size_usdc>\n\n"
        "*Kalshi:*\n"
        "/kalshi <query> — search markets\n"
        "/kalshiorder <ticker> <yes|no> <buy|sell> <count> <cents>\n\n"
        "*Metaculus:*\n"
        "/meta <query> — search questions\n"
        "/metapredict <question_id> <0.0-1.0>\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


def build_app():
    app = ApplicationBuilder().token(cfg.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("positions", cmd_positions))
    app.add_handler(CommandHandler("signals", cmd_signals))
    app.add_handler(CommandHandler("autotrade", cmd_toggle_trade))
    app.add_handler(CommandHandler("autobet", cmd_toggle_bet))
    app.add_handler(CommandHandler("swap", cmd_swap))
    app.add_handler(CommandHandler("poly", cmd_poly))
    app.add_handler(CommandHandler("polybuy", cmd_polybuy))
    app.add_handler(CommandHandler("kalshi", cmd_kalshi))
    app.add_handler(CommandHandler("kalshiorder", cmd_kalshiorder))
    app.add_handler(CommandHandler("meta", cmd_meta))
    app.add_handler(CommandHandler("metapredict", cmd_metapredict))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app
