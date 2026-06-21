"""
Watchlist panel — click any symbol to sync it across Trading + Analysis tabs
and open TradingView at that symbol with your saved indicators.
"""
from __future__ import annotations
import customtkinter as ctk
from ui.theme import (
    BG_CARD, BG_INPUT, BORDER, ACCENT, PURPLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, FONT_SMALL, FONT_BODY,
    GREEN, RED, PAD, CORNER_RADIUS,
)

# ── Symbol groups shown in the watchlist ─────────────────────────────────────

WATCHLIST: list[tuple[str, str, str]] = [
    # (display name, ticker, group)
    ("BTC / USDT",   "BTC",    "Crypto"),
    ("ETH / USDT",   "ETH",    "Crypto"),
    ("SOL / USDT",   "SOL",    "Crypto"),
    ("DOGE / USDT",  "DOGE",   "Crypto"),
    ("SUI / USDT",   "SUI",    "Crypto"),
    ("WIF / USDT",   "WIF",    "Crypto"),
    ("Crude Oil CL", "CL",     "Futures"),
    ("Gold GC",      "GC",     "Futures"),
    ("Silver SI",    "SI",     "Futures"),
    ("Nat Gas NG",   "NG",     "Futures"),
    ("S&P 500 ES",   "ES",     "Futures"),
    ("NASDAQ NQ",    "NQ",     "Futures"),
]


class WatchlistPanel(ctk.CTkFrame):
    """
    Compact watchlist.  Call set_on_select(callback) to receive
    (ticker, display_name) when the user clicks a symbol.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", BG_CARD)
        kwargs.setdefault("corner_radius", CORNER_RADIUS)
        super().__init__(master, **kwargs)
        self._on_select = None
        self._active_ticker: str = ""
        self._btn_map: dict[str, ctk.CTkButton] = {}
        self._build()

    def set_on_select(self, callback):
        """callback(ticker: str, display_name: str)"""
        self._on_select = callback

    def _build(self):
        ctk.CTkLabel(
            self, text="WATCHLIST",
            font=("Inter", 10, "bold"), text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=10, pady=(10, 2))

        current_group = ""
        for display, ticker, group in WATCHLIST:
            if group != current_group:
                current_group = group
                ctk.CTkLabel(
                    self, text=group.upper(),
                    font=("Inter", 9, "bold"), text_color=PURPLE,
                ).pack(anchor="w", padx=10, pady=(6, 0))

            btn = ctk.CTkButton(
                self,
                text=display,
                anchor="w",
                height=28,
                corner_radius=4,
                fg_color="transparent",
                text_color=TEXT_SECONDARY,
                hover_color=BG_INPUT,
                font=FONT_SMALL,
                command=lambda d=display, t=ticker: self._click(d, t),
            )
            btn.pack(fill="x", padx=6, pady=1)
            self._btn_map[ticker] = btn

    def _click(self, display: str, ticker: str):
        # Highlight selected
        for t, b in self._btn_map.items():
            b.configure(
                fg_color=ACCENT if t == ticker else "transparent",
                text_color=TEXT_PRIMARY if t == ticker else TEXT_SECONDARY,
            )
        self._active_ticker = ticker

        if self._on_select:
            self._on_select(ticker, display)

    def set_active(self, ticker: str):
        """Programmatically highlight a ticker without firing the callback."""
        for t, b in self._btn_map.items():
            b.configure(
                fg_color=ACCENT if t == ticker else "transparent",
                text_color=TEXT_PRIMARY if t == ticker else TEXT_SECONDARY,
            )
        self._active_ticker = ticker
