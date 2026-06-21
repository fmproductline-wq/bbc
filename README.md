# Trading & Prediction Bot

A Telegram-controlled trading bot that:
- **Executes on-chain trades** via your Rabby wallet (EVM) + 1inch DEX, triggered by TradingView signals
- **Supports indicators**: Xtreme Trend, HOTT LOTT (High & Low Optimized Trend Tracker)
- **Bets on prediction markets**: Polymarket, Kalshi, Metaculus
- **Telegram bot** as your full control panel

---

## Setup

### 1. Clone & install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual keys
```

Required keys:
| Key | Where to get it |
|-----|----------------|
| `WALLET_PRIVATE_KEY` | Export from Rabby wallet (Settings → Export Private Key) |
| `WALLET_ADDRESS` | Your 0x address from Rabby |
| `ETH_RPC_URL` / `POLYGON_RPC_URL` | [alchemy.com](https://alchemy.com) free tier |
| `ONEINCH_API_KEY` | [portal.1inch.dev](https://portal.1inch.dev) |
| `TRADINGVIEW_WEBHOOK_SECRET` | Any random string you choose |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram user ID from [@userinfobot](https://t.me/userinfobot) |
| `POLYMARKET_API_KEY` | [Polymarket CLOB API docs](https://docs.polymarket.com) |
| `KALSHI_EMAIL` + `KALSHI_PASSWORD` | Your Kalshi account |

### 3. Run the bot

```bash
python main.py
```

The server runs on port 8000. Use [ngrok](https://ngrok.com) for local testing:

```bash
ngrok http 8000
# Copy the https URL for TradingView webhooks
```

---

## TradingView Alert Setup

1. Open your chart with **Xtreme Trend** or **HOTT LOTT** indicator
2. Click the **Alert** button (clock icon) on a signal condition
3. Set **Webhook URL**: `https://yourserver.com/webhook/tradingview`
4. Set **Message** to the JSON template from `pine_script_alerts/`:

**For Xtreme Trend BUY:**
```json
{"secret":"YOUR_WEBHOOK_SECRET","indicator":"xtreme_trend","action":"buy","symbol":"{{ticker}}","timeframe":"{{interval}}","price":{{close}},"chain":"polygon"}
```

**For HOTT LOTT SELL:**
```json
{"secret":"YOUR_WEBHOOK_SECRET","indicator":"hott_lott","action":"sell","symbol":"{{ticker}}","timeframe":"{{interval}}","price":{{close}},"chain":"polygon"}
```

> Use `{{strategy.order.action}}` instead of hardcoded `"buy"`/`"sell"` if using a Pine Strategy.

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu with buttons |
| `/status` | Bot status, auto-trade/bet toggles |
| `/balance` | Wallet native token balance |
| `/positions` | Open DEX positions |
| `/signals` | Last 5 TradingView signals received |
| `/autotrade` | Toggle auto-trade on/off |
| `/autobet` | Toggle auto-bet on/off |
| `/swap <in> <out> <amount> [chain]` | Manual swap |
| `/poly <keyword>` | Search Polymarket markets |
| `/polybuy <token_id> <YES\|NO> <price> <size_usdc>` | Place Polymarket order |
| `/kalshi <keyword>` | Search Kalshi markets |
| `/kalshiorder <ticker> <yes\|no> <buy\|sell> <count> <cents>` | Place Kalshi order |
| `/meta <keyword>` | Search Metaculus questions |
| `/metapredict <question_id> <0.0-1.0>` | Submit forecast |

---

## Architecture

```
TradingView (Xtreme Trend / HOTT LOTT)
        │  Alert webhook (JSON)
        ▼
FastAPI Server (/webhook/tradingview)
        │
        ├─→ trading/signals.py   parse signal
        ├─→ trading/executor.py  decide buy/sell
        ├─→ trading/dex.py       1inch swap
        └─→ trading/wallet.py    Rabby wallet / Web3

Telegram Bot (python-telegram-bot)
        │
        ├─→ /status, /balance, /positions
        ├─→ /autotrade, /autobet
        ├─→ predictions/polymarket.py
        ├─→ predictions/kalshi.py
        └─→ predictions/metaculus.py
```

---

## Security

- **Never commit** your `.env` file or private key
- The webhook `/webhook/tradingview` validates the `secret` field on every request
- Only your Telegram user ID can control the bot
- Test with small amounts first (`MAX_TRADE_PCT=1`)
- Use Kalshi demo environment before going live: set `KALSHI_BASE_URL=https://demo-api.kalshi.co/trade-api/v2`
