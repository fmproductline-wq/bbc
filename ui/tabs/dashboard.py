"""Dashboard tab — live account summary, positions, signal feed."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.stat_tile import StatTile
from ui.components.log_box import LogBox


class DashboardTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        # ── Top row: stat tiles ───────────────────────────────────────────────
        tiles_row = ctk.CTkFrame(self, fg_color="transparent")
        tiles_row.pack(fill="x", padx=PAD, pady=(PAD, 0))
        for c in range(5):
            tiles_row.columnconfigure(c, weight=1, uniform="tile")

        self.tile_value  = StatTile(tiles_row, "Account Value",   "—")
        self.tile_pnl    = StatTile(tiles_row, "Unrealized PnL",  "—")
        self.tile_margin = StatTile(tiles_row, "Margin Used",     "—")
        self.tile_pos    = StatTile(tiles_row, "Open Positions",  "—")
        self.tile_sigs   = StatTile(tiles_row, "Signals (total)", "—")

        for col, tile in enumerate([self.tile_value, self.tile_pnl, self.tile_margin, self.tile_pos, self.tile_sigs]):
            tile.grid(row=0, column=col, padx=6, pady=0, sticky="nsew")

        # ── Middle: positions table + bot controls ────────────────────────────
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(0, weight=1)

        # Positions table
        pos_card = Card(mid, title="Open Positions")
        pos_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        headers = ["Coin", "Side", "Size", "Entry", "uPnL", "Stop Loss", "Chain"]
        header_frame = ctk.CTkFrame(pos_card, fg_color="transparent")
        header_frame.pack(fill="x", padx=PAD, pady=(0, 4))
        for i, h in enumerate(headers):
            header_frame.columnconfigure(i, weight=1)
            ctk.CTkLabel(header_frame, text=h, font=("Inter", 11, "bold"),
                         text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=i, sticky="w", padx=4)

        self.pos_scroll = ctk.CTkScrollableFrame(pos_card, fg_color="transparent", height=200)
        self.pos_scroll.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
        self.pos_rows: list[list[ctk.CTkLabel]] = []

        # Bot controls
        ctrl_card = Card(mid, title="Bot Controls")
        ctrl_card.grid(row=0, column=1, sticky="nsew")

        self.auto_trade_var = ctk.BooleanVar(value=False)
        self.auto_bet_var   = ctk.BooleanVar(value=False)

        ctk.CTkLabel(ctrl_card, text="Auto-Trade", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(anchor="w", padx=PAD)
        ctk.CTkSwitch(ctrl_card, text="", variable=self.auto_trade_var,
                      command=self._toggle_trade,
                      progress_color=GREEN, button_color=ACCENT).pack(anchor="w", padx=PAD, pady=(0, 12))

        ctk.CTkLabel(ctrl_card, text="Auto-Bet", font=FONT_BODY, text_color=TEXT_PRIMARY).pack(anchor="w", padx=PAD)
        ctk.CTkSwitch(ctrl_card, text="", variable=self.auto_bet_var,
                      command=self._toggle_bet,
                      progress_color=GREEN, button_color=ACCENT).pack(anchor="w", padx=PAD, pady=(0, 12))

        ctk.CTkButton(ctrl_card, text="🔍  Run Bug Check", fg_color=BG_INPUT,
                      text_color=ACCENT, hover_color=BORDER,
                      command=self._run_bugcheck).pack(fill="x", padx=PAD, pady=4)

        ctk.CTkButton(ctrl_card, text="🔄  Refresh", fg_color=ACCENT,
                      text_color=BG_DARK,
                      command=self.refresh).pack(fill="x", padx=PAD, pady=(4, PAD))

        # ── Bottom: live log ──────────────────────────────────────────────────
        log_card = Card(self, title="Live Log")
        log_card.pack(fill="both", expand=False, padx=PAD, pady=(0, PAD))
        self.log = LogBox(log_card, height=130)
        self.log.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_trade(self):
        from trading.state import state
        state.auto_trade = self.auto_trade_var.get()
        self.log.append(f"Auto-trade {'ON' if state.auto_trade else 'OFF'}", "SUCCESS" if state.auto_trade else "WARNING")

    def _toggle_bet(self):
        from trading.state import state
        state.auto_bet = self.auto_bet_var.get()
        self.log.append(f"Auto-bet {'ON' if state.auto_bet else 'OFF'}", "SUCCESS" if state.auto_bet else "WARNING")

    def _run_bugcheck(self):
        self.log.append("Running bug check…", "INFO")
        def _do():
            from agents.bug_checker import run_bug_check
            result = run_bug_check()
            for r in result.reports:
                level = {"CRITICAL": "ERROR", "WARNING": "WARNING", "INFO": "INFO"}.get(r.severity, "DEFAULT")
                self.after(0, self.log.append, f"[{r.severity}] {r.category}: {r.message}", level)
            if not result.reports:
                self.after(0, self.log.append, "Bug check passed — no issues.", "SUCCESS")
        threading.Thread(target=_do, daemon=True).start()

    def refresh(self):
        """Refresh account stats and positions in a background thread."""
        threading.Thread(target=self._fetch_and_update, daemon=True).start()

    def _fetch_and_update(self):
        from trading.state import state
        self.after(0, self.tile_sigs.update_value, str(len(state.signal_log)))
        try:
            from trading import hyperliquid as hl
            summary = hl.get_account_summary()
            val   = f"${float(summary.get('account_value') or 0):,.2f}"
            margin = f"${float(summary.get('total_margin_used') or 0):,.2f}"
            ntl   = f"${float(summary.get('total_ntl_pos') or 0):,.2f}"
            positions = summary.get("positions", [])

            # Calculate total uPnL
            total_pnl = sum(float(p.get("unrealized_pnl") or 0) for p in positions)
            pnl_color = GREEN if total_pnl >= 0 else RED
            pnl_str = f"${total_pnl:+,.2f}"

            self.after(0, self.tile_value.update_value, val)
            self.after(0, self.tile_pnl.update_value, pnl_str, pnl_color)
            self.after(0, self.tile_margin.update_value, margin)
            self.after(0, self.tile_pos.update_value, str(len(positions)))
            self.after(0, self._render_positions, positions)
            self.after(0, self.log.append, "Dashboard refreshed", "SUCCESS")
        except Exception as e:
            self.after(0, self.log.append, f"Refresh failed: {e}", "ERROR")

    def _render_positions(self, positions: list[dict]):
        for widget in self.pos_scroll.winfo_children():
            widget.destroy()
        self.pos_rows.clear()

        if not positions:
            ctk.CTkLabel(self.pos_scroll, text="No open positions",
                         text_color=TEXT_MUTED, font=FONT_SMALL).pack(pady=20)
            return

        for pos in positions:
            row_frame = ctk.CTkFrame(self.pos_scroll, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            for i in range(7):
                row_frame.columnconfigure(i, weight=1)

            pnl_val = float(pos.get("unrealized_pnl") or 0)
            pnl_color = GREEN if pnl_val >= 0 else RED
            side_color = GREEN if pos.get("side") == "LONG" else RED

            values = [
                (pos.get("coin", "?"),             TEXT_PRIMARY),
                (pos.get("side", "?"),             side_color),
                (str(pos.get("size", "?")),        TEXT_PRIMARY),
                (f"${float(pos.get('entry_px') or 0):,.4f}", TEXT_PRIMARY),
                (f"${pnl_val:+,.2f}",              pnl_color),
                ("—",                              TEXT_SECONDARY),
                ("Hyperliquid",                    ACCENT),
            ]
            for col, (text, color) in enumerate(values):
                ctk.CTkLabel(row_frame, text=text, font=FONT_SMALL,
                             text_color=color, anchor="w").grid(row=0, column=col, sticky="w", padx=4)
