"""Trading tab — manual Hyperliquid perp orders."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox


class TradingTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Price bar ─────────────────────────────────────────────────────────
        price_bar = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_RADIUS,
                                  border_width=1, border_color=BORDER)
        price_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(PAD, 8))

        inner = ctk.CTkFrame(price_bar, fg_color="transparent")
        inner.pack(fill="x", padx=PAD, pady=10)

        ctk.CTkLabel(inner, text="Coin", text_color=TEXT_SECONDARY, font=FONT_SMALL).pack(side="left")
        self.price_coin = ctk.CTkEntry(inner, width=80, fg_color=BG_INPUT, border_color=BORDER,
                                        text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.price_coin.insert(0, "BTC")
        self.price_coin.pack(side="left", padx=(4, 12))

        ctk.CTkButton(inner, text="Get Price", width=90, fg_color=BG_INPUT,
                      text_color=ACCENT, hover_color=BORDER,
                      command=self._fetch_price).pack(side="left")

        self.price_label = ctk.CTkLabel(inner, text="—", font=("Inter", 18, "bold"),
                                         text_color=TEXT_PRIMARY)
        self.price_label.pack(side="left", padx=20)

        self.price_change = ctk.CTkLabel(inner, text="", font=FONT_BODY, text_color=TEXT_SECONDARY)
        self.price_change.pack(side="left")

        # ── Order form ────────────────────────────────────────────────────────
        order_card = Card(self, title="Place Order")
        order_card.grid(row=1, column=0, sticky="nsew", padx=(PAD, 4), pady=(0, PAD))

        form = ctk.CTkFrame(order_card, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        def lbl(text): return ctk.CTkLabel(form, text=text, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        def ent(default=""):
            e = ctk.CTkEntry(form, fg_color=BG_INPUT, border_color=BORDER,
                             text_color=TEXT_PRIMARY, font=FONT_BODY)
            if default: e.insert(0, default)
            return e

        lbl("Coin").pack(fill="x", pady=(8, 2))
        self.coin_entry = ent("BTC"); self.coin_entry.pack(fill="x")

        lbl("Size (coin units)").pack(fill="x", pady=(8, 2))
        self.size_entry = ent("0.001"); self.size_entry.pack(fill="x")

        lbl("Leverage").pack(fill="x", pady=(8, 2))
        self.lev_entry = ent("5"); self.lev_entry.pack(fill="x")

        lbl("Order Type").pack(fill="x", pady=(8, 2))
        self.order_type = ctk.CTkSegmentedButton(form, values=["Market", "Limit"],
                                                  fg_color=BG_INPUT, selected_color=ACCENT,
                                                  text_color=TEXT_PRIMARY, font=FONT_SMALL)
        self.order_type.set("Market")
        self.order_type.pack(fill="x")
        self.order_type.configure(command=self._on_order_type)

        lbl("Limit Price (Market orders: ignored)").pack(fill="x", pady=(8, 2))
        self.limit_price = ent(""); self.limit_price.pack(fill="x")

        lbl("Stop Loss Price (optional)").pack(fill="x", pady=(8, 2))
        self.sl_entry = ent(""); self.sl_entry.pack(fill="x")

        # Buttons
        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", pady=16)
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)

        ctk.CTkButton(btn_row, text="▲  LONG", fg_color=GREEN,
                      text_color="black", font=("Inter", 13, "bold"),
                      command=lambda: self._place_order("long")).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btn_row, text="▼  SHORT", fg_color=RED,
                      text_color="white", font=("Inter", 13, "bold"),
                      command=lambda: self._place_order("short")).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(btn_row, text="✕  CLOSE", fg_color=BG_INPUT,
                      text_color=TEXT_PRIMARY, font=("Inter", 13, "bold"),
                      hover_color=BORDER,
                      command=self._close_position).grid(row=0, column=2, padx=4, sticky="ew")

        # ── Open orders / positions ────────────────────────────────────────────
        right_card = Card(self, title="Live Positions & Orders")
        right_card.grid(row=1, column=1, sticky="nsew", padx=(4, PAD), pady=(0, PAD))

        self.pos_box = LogBox(right_card, height=300)
        self.pos_box.pack(fill="both", expand=True, padx=PAD, pady=(0, 8))

        btn_r = ctk.CTkFrame(right_card, fg_color="transparent")
        btn_r.pack(fill="x", padx=PAD, pady=(0, PAD))
        ctk.CTkButton(btn_r, text="🔄 Refresh", fg_color=ACCENT, text_color=BG_DARK,
                      command=self._refresh_positions).pack(side="left")
        ctk.CTkButton(btn_r, text="🛑 Set Leverage", fg_color=BG_INPUT,
                      text_color=TEXT_PRIMARY, hover_color=BORDER,
                      command=self._set_leverage).pack(side="left", padx=8)

        # Log at bottom
        log_card = Card(self, title="Order Log")
        log_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=PAD, pady=(0, PAD))
        self.log = LogBox(log_card, height=100)
        self.log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _on_order_type(self, value):
        pass  # could grey out limit price field

    def _fetch_price(self):
        coin = self.price_coin.get().strip().upper()
        def _do():
            try:
                from trading import hyperliquid as hl
                mids = hl.get_all_mids()
                p = mids.get(coin)
                if p:
                    self.after(0, self.price_label.configure, {"text": f"${p:,.4f}"})
                else:
                    self.after(0, self.price_label.configure, {"text": "Not found"})
            except Exception as e:
                self.after(0, self.log.append, f"Price fetch failed: {e}", "ERROR")
        threading.Thread(target=_do, daemon=True).start()

    def _place_order(self, side: str):
        coin = self.coin_entry.get().strip().upper()
        try:
            size = float(self.size_entry.get())
        except ValueError:
            self.log.append("Invalid size", "ERROR"); return

        lev_str = self.lev_entry.get().strip()
        sl_str  = self.sl_entry.get().strip()
        limit_str = self.limit_price.get().strip()
        order_type = self.order_type.get()

        self.log.append(f"Placing {side.upper()} {size} {coin}…", "INFO")

        def _do():
            try:
                from trading import hyperliquid as hl
                if lev_str:
                    hl.set_leverage(coin, int(lev_str))
                if order_type == "Market":
                    result = hl.market_open(coin, is_buy=(side == "long"), size=size)
                else:
                    price = float(limit_str)
                    result = hl.limit_open(coin, is_buy=(side == "long"), size=size, price=price)
                if sl_str:
                    hl.set_stop_loss(coin, float(sl_str), size)
                self.after(0, self.log.append, f"Order placed: {result}", "SUCCESS")
                self.after(0, self._refresh_positions)
            except Exception as e:
                self.after(0, self.log.append, f"Order failed: {e}", "ERROR")
        threading.Thread(target=_do, daemon=True).start()

    def _close_position(self):
        coin = self.coin_entry.get().strip().upper()
        self.log.append(f"Closing {coin}…", "INFO")
        def _do():
            try:
                from trading import hyperliquid as hl
                result = hl.market_close(coin)
                self.after(0, self.log.append, f"Closed: {result}", "SUCCESS")
                self.after(0, self._refresh_positions)
            except Exception as e:
                self.after(0, self.log.append, f"Close failed: {e}", "ERROR")
        threading.Thread(target=_do, daemon=True).start()

    def _set_leverage(self):
        coin = self.coin_entry.get().strip().upper()
        lev_str = self.lev_entry.get().strip()
        if not lev_str:
            self.log.append("Enter leverage first", "WARNING"); return
        def _do():
            try:
                from trading import hyperliquid as hl
                hl.set_leverage(coin, int(lev_str))
                self.after(0, self.log.append, f"Leverage set: {coin} {lev_str}x", "SUCCESS")
            except Exception as e:
                self.after(0, self.log.append, f"Leverage failed: {e}", "ERROR")
        threading.Thread(target=_do, daemon=True).start()

    def _refresh_positions(self):
        self.pos_box.clear()
        def _do():
            try:
                from trading import hyperliquid as hl
                summary = hl.get_account_summary()
                positions = summary.get("positions", [])
                if not positions:
                    self.after(0, self.pos_box.append, "No open positions", "INFO")
                for p in positions:
                    pnl = float(p.get("unrealized_pnl") or 0)
                    level = "SUCCESS" if pnl >= 0 else "ERROR"
                    line = (f"{p['side']:5} {p['size']} {p['coin']:6} "
                            f"@ ${float(p.get('entry_px') or 0):,.4f}  "
                            f"uPnL: ${pnl:+,.2f}")
                    self.after(0, self.pos_box.append, line, level)
                orders = hl.get_open_orders()
                if orders:
                    self.after(0, self.pos_box.append, f"\nOpen orders ({len(orders)}):", "INFO")
                    for o in orders:
                        self.after(0, self.pos_box.append,
                                   f"  {o.get('side')} {o.get('sz')} {o.get('coin')} @ {o.get('limitPx')}", "DEFAULT")
            except Exception as e:
                self.after(0, self.pos_box.append, f"Fetch failed: {e}", "ERROR")
        threading.Thread(target=_do, daemon=True).start()
