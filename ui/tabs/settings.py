"""Settings tab — edit .env config values from within the UI."""
from __future__ import annotations
import os
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._build()
        self._load_env()

    # ── Fields definition ─────────────────────────────────────────────────────

    SECTIONS = {
        "Wallet": [
            ("WALLET_ADDRESS",      "Wallet Address (0x…)", False),
            ("WALLET_PRIVATE_KEY",  "Private Key (keep secret!)", True),
            ("DEFAULT_CHAIN",       "Default Chain (polygon/ethereum/bsc)", False),
        ],
        "RPC Endpoints": [
            ("POLYGON_RPC_URL", "Polygon RPC URL", False),
            ("ETH_RPC_URL",     "Ethereum RPC URL", False),
            ("BSC_RPC_URL",     "BSC RPC URL", False),
        ],
        "1inch / DEX": [
            ("ONEINCH_API_KEY", "1inch API Key", True),
        ],
        "TradingView": [
            ("TRADINGVIEW_WEBHOOK_SECRET", "Webhook Secret", True),
        ],
        "Telegram": [
            ("TELEGRAM_BOT_TOKEN",      "Bot Token", True),
            ("TELEGRAM_ALLOWED_USER_ID","Allowed User ID", False),
        ],
        "Polymarket": [
            ("POLYMARKET_API_KEY",        "API Key", True),
            ("POLYMARKET_API_SECRET",     "API Secret", True),
            ("POLYMARKET_API_PASSPHRASE", "Passphrase", True),
        ],
        "Kalshi": [
            ("KALSHI_EMAIL",    "Email", False),
            ("KALSHI_PASSWORD", "Password", True),
            ("KALSHI_BASE_URL", "API Base URL", False),
        ],
        "Metaculus": [
            ("METACULUS_TOKEN", "API Token", True),
        ],
        "Risk Management": [
            ("MAX_TRADE_PCT",  "Max Trade % of Account", False),
            ("MAX_BET_PCT",    "Max Bet % of Account", False),
            ("SLIPPAGE_PCT",   "Slippage %", False),
            ("STOP_LOSS_PCT",  "Stop Loss %", False),
        ],
    }

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(top_bar, text="Settings", font=FONT_TITLE, text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(top_bar, text="💾  Save to .env", fg_color=GREEN, text_color="black",
                      font=("Inter", 13, "bold"), command=self._save).pack(side="right")
        ctk.CTkButton(top_bar, text="🔄  Reload", fg_color=BG_INPUT,
                      text_color=ACCENT, hover_color=BORDER,
                      command=self._load_env).pack(side="right", padx=8)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=PAD, pady=PAD)
        self.rowconfigure(1, weight=1)

        scroll.columnconfigure(0, weight=1)
        scroll.columnconfigure(1, weight=1)

        sections = list(self.SECTIONS.items())
        for idx, (section_name, fields) in enumerate(sections):
            col = idx % 2
            card = Card(scroll, title=section_name)
            card.grid(row=idx // 2, column=col, sticky="nsew", padx=6, pady=6)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=PAD, pady=(0, PAD))

            for key, label, secret in fields:
                ctk.CTkLabel(inner, text=label, font=FONT_SMALL,
                             text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(6, 2))
                e = ctk.CTkEntry(inner, fg_color=BG_INPUT, border_color=BORDER,
                                 text_color=TEXT_PRIMARY, font=FONT_MONO,
                                 show="•" if secret else "")
                e.pack(fill="x")
                self._entries[key] = e

        # Status log at bottom
        log_card = Card(self, title="Save Log")
        log_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(0, PAD))
        self.log = LogBox(log_card, height=70)
        self.log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _load_env(self):
        env_vals: dict[str, str] = {}
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, _, v = line.partition("=")
                        env_vals[k.strip()] = v.strip()

        for key, entry in self._entries.items():
            entry.delete(0, "end")
            if key in env_vals:
                entry.insert(0, env_vals[key])
        self.log.append("Settings loaded from .env", "SUCCESS")

    def _save(self):
        # Read existing .env to preserve comments and unknown keys
        existing_lines: list[str] = []
        existing_keys: set[str] = set()
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH) as f:
                existing_lines = f.readlines()
            for line in existing_lines:
                if "=" in line and not line.strip().startswith("#"):
                    existing_keys.add(line.split("=")[0].strip())

        # Build new .env: update known keys, append new ones
        new_lines: list[str] = []
        updated: set[str] = set()
        for line in existing_lines:
            if "=" in line and not line.strip().startswith("#"):
                k = line.split("=")[0].strip()
                if k in self._entries:
                    new_lines.append(f"{k}={self._entries[k].get()}\n")
                    updated.add(k)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Append keys not previously in .env
        for key, entry in self._entries.items():
            if key not in updated:
                new_lines.append(f"{key}={entry.get()}\n")

        with open(ENV_PATH, "w") as f:
            f.writelines(new_lines)

        self.log.append(f"Saved {len(self._entries)} settings to .env", "SUCCESS")
        self.log.append("Restart the app / server for changes to take effect.", "WARNING")
