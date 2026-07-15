# Best Brand — Trading & Prediction Bot

A Telegram-controlled automated trading and prediction market bot that:
- **Executes perpetuals trades** on Hyperliquid, triggered by TradingView signals
- **Supports proprietary indicators**: sig_a, sig_b, sig_c (1h/1m timeframes)
- **Bets on prediction markets**: Polymarket, Kalshi, Metaculus
- **Telegram approval gateway** — no trade or bet executes without your tap
- **Desktop UI** (CustomTkinter dark-mode) with live charts and market analysis
- **Bug-checker agent** runs every 30 minutes; auto-remediates runaway losses
- **18+ age gate** and T&C acceptance recorded per install device

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
| `WALLET_ADDRESS` | Your 0x address |
| `ETH_RPC_URL` / `POLYGON_RPC_URL` | [alchemy.com](https://alchemy.com) free tier |
| `ONEINCH_API_KEY` | [portal.1inch.dev](https://portal.1inch.dev) |
| `TRADINGVIEW_WEBHOOK_SECRET` | Any random string you choose |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_ALLOWED_USER_ID` | Your Telegram user ID from [@userinfobot](https://t.me/userinfobot) |
| `POLYMARKET_API_KEY` | Polymarket CLOB API |
| `KALSHI_EMAIL` + `KALSHI_PASSWORD` | Your Kalshi account |
| `FEE_WALLET_ADDRESS` | Creator wallet to receive 0.02% platform fee |

### 3. Run the desktop app

```bash
python desktop_app.py
```

### 4. Run the bot server only (headless)

```bash
python main.py
```

The server runs on port 8000. Use [ngrok](https://ngrok.com) for TradingView webhooks:

```bash
ngrok http 8000
# Copy the https URL → paste into TradingView alert webhook URL
```

---

## TradingView Alert Setup

1. Open your chart with the indicator
2. Click the **Alert** button → set **Webhook URL**: `https://yourserver.com/webhook/tradingview`
3. Set **Message** to the JSON template from `pine_script_alerts/`:

```json
{"secret":"YOUR_WEBHOOK_SECRET","indicator":"sig_a","action":"buy","symbol":"{{ticker}}","timeframe":"{{interval}}","price":{{close}}}
```

---

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Main menu |
| `/status` | Bot status + toggle switches |
| `/balance` | Account value & margin |
| `/positions` | Open Hyperliquid positions |
| `/signals` | Last 5 TradingView signals |
| `/pending` | Pending approval requests |
| `/autotrade` | Toggle auto-trade on/off |
| `/autobet` | Toggle auto-bet on/off |
| `/long <coin> <size>` | Manual long (requires approval) |
| `/short <coin> <size>` | Manual short (requires approval) |
| `/close <coin>` | Close position (requires approval) |
| `/poly <keyword>` | Search Polymarket markets |
| `/polybuy <token_id> <YES\|NO> <price> <size>` | Place Polymarket order |
| `/kalshi <keyword>` | Search Kalshi markets |
| `/kalshiorder <ticker> <yes\|no> <buy\|sell> <count> <cents>` | Place Kalshi order |
| `/meta <keyword>` | Search Metaculus questions |
| `/metapredict <question_id> <0.0-1.0>` | Submit forecast |
| `/analyze <coin> [interval]` | Run market analysis |
| `/bugcheck` | Run diagnostic checks |
| `/uhrpwallet` | Check the connected BRC-100 wallet (e.g. Metanet Client) — no funds moved |
| `/uhrpupload [minutes]` | Reply to a photo/document to publish it to UHRP storage |
| `/uhrpdownload <uhrp_url>` | Fetch, hash-verify, and log a UHRP file, then send it back |
| `/uhrpresolve <uhrp_url>` | Refresh the direct download link for a ledger entry |
| `/uhrpledger` | Send the Excel ledger file (`~/.bestbrand/uhrp_ledger.xlsx`) |
| `/uhrplist [n]` | Show the last n ledger entries |
| `/uhrpsync` | Reconcile the ledger against your actual hosted files (adds anything missing, refreshes expiry) |
| `/uhrprenew <uhrp_url> <minutes>` | Extend a file's hosting commitment, pays via the wallet |

---

## Architecture

```
TradingView (signal alerts)
        │  Webhook (JSON)
        ▼
FastAPI Server (/webhook/tradingview)
        │
        ├─→ trading/signals.py      parse & obfuscate indicator
        ├─→ trading/executor.py     size position, build detail
        └─→ trading/approval.py     ← suspend here (asyncio.Event)
                │
                ▼
        Telegram Bot (owner taps ✅ / ❌)
                │
                ├── Approve → trading/hyperliquid.py (market_open/close)
                │            trading/fees.py (0.02% fee transfer)
                └── Reject  → cancelled, notification sent

Desktop UI (CustomTkinter)
  Dashboard | Trading | Analysis | Predictions | UHRP | Bug Checker | Settings
```

---

## UHRP Document Ledger

Upload and download documents/images to [UHRP](https://hub.bsvblockchain.org/brc/overlays/0026) (Universal Hash Resolution Protocol) storage from Telegram or the desktop app's **UHRP** tab. Every upload/download is logged as a row in an Excel ledger with the filename, content type, size, SHA-256 hash, the `uhrp://` URL, a clickable direct link back to the file, expiry time + status, and an embedded thumbnail for images.

Note on scale: UHRP prices per file — one paid invoice and one URL per upload, no batching in the protocol itself. The desktop app's file queue (Add Files/Add Folder → Upload All) and the ledger's auto-logging remove the manual copy-paste work around that; `/uhrpsync` (or the "Sync from Host" button) reconciles the ledger against your wallet's actual hosted file list in one call, so you never have to cross-check against the storage host's website by hand.

**Why there's a `uhrp_node/` folder:** publishing a file to UHRP pays the storage host's invoice, which requires signing a BSV transaction through a BRC-100 wallet. That payment/signing logic is only implemented in Babbage's `@bsv/sdk` (JS/TS) — there's no Python equivalent — so the bot shells out to a small Node.js helper for the actual upload/resolve/download calls. Everything else (Telegram commands, the ledger, file handling) is Python.

### Setup

```bash
cd uhrp_node
npm install
```

**Uploading** (`/uhrpupload`) requires a running, funded [BRC-100 wallet](https://github.com/bsv-blockchain/wallet-toolbox-examples) — e.g. [Metanet Client](https://metanetapps.com/) — running on the **same machine** as this bot. It's what actually pays the storage host's invoice. **Downloading** (`/uhrpdownload`) needs no wallet; it's a free overlay-network lookup + hash-verified fetch.

Open and unlock Metanet Client, then run `/uhrpwallet` from Telegram to confirm the bot can reach it before trying a real upload — no funds move on that check. The first real upload will likely trigger a permission prompt inside Metanet Client; approve it there.

By default the bot publishes to `https://nanostore.babbage.systems` (override with `UHRP_STORAGE_URL` in `.env`). `UHRP_WALLET_ORIGINATOR` (default `bestbrand.ca`) is the app name shown in the wallet's permission prompt — any domain-shaped string works.

### Usage

- `/uhrpwallet` — verify the bot can reach your wallet.
- Send or reply to a photo/document with `/uhrpupload` to publish it and log it.
- `/uhrpdownload <uhrp_url>` fetches a file by its UHRP URL, verifies its hash, logs it, and sends it back.
- `/uhrpledger` sends you the ledger spreadsheet itself.
- Direct links resolve right after upload when possible; if the advertisement hasn't propagated yet, run `/uhrpresolve <uhrp_url>` to backfill the clickable link once it's ready.

---

## Data stored locally

All data is kept on your device under `~/.bestbrand/`:

| File | Contents |
|------|----------|
| `registry.json` | Install ID, age verification, T&C acceptance |
| `installs.log` | Per-event acceptance log |
| `fees.jsonl` | Fee ledger (one JSON line per trade) |
| `uhrp_ledger.xlsx` | UHRP upload/download ledger (hash, URL, thumbnail) |
| `uhrp_files/` | Local cache of uploaded/downloaded UHRP files |

---

## Security

- **Never commit** your `.env` file or private key
- Webhook validates `secret` field on every request
- Only your Telegram user ID can control the bot
- Every trade requires explicit Telegram approval — nothing auto-executes without your tap
- Test with small amounts first (`MAX_TRADE_PCT=1`)
