"""Backtesting tab — run pattern engine on any coin/timeframe (#9)."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox


_COINS = [
    "BTC", "ETH", "SOL", "DOGE", "SUI",
    "CL", "GC", "SI", "ES", "NQ", "NG",
]
_TIMEFRAMES = ["1h", "4h", "1d"]
_LIMITS = {
    "1h":  1000,
    "4h":  500,
    "1d":  500,
}


class BacktestTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._running = False
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(top, text="Backtesting", font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(side="left")

        # ── Controls ──────────────────────────────────────────────────────────
        ctrl = Card(self, title="Run Backtest")
        ctrl.grid(row=1, column=0, sticky="ew", padx=PAD, pady=PAD)
        inner = ctk.CTkFrame(ctrl, fg_color="transparent")
        inner.pack(fill="x", padx=PAD, pady=(0, PAD))
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(2, weight=2)
        inner.columnconfigure(3, weight=1)

        ctk.CTkLabel(inner, text="Asset", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._coin_var = ctk.StringVar(value="BTC")
        self._coin_menu = ctk.CTkOptionMenu(
            inner, values=_COINS, variable=self._coin_var,
            fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=PURPLE,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
        )
        self._coin_menu.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(inner, text="Timeframe", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).grid(row=0, column=1, sticky="w", pady=(0, 2))
        self._tf_var = ctk.StringVar(value="1h")
        self._tf_menu = ctk.CTkOptionMenu(
            inner, values=_TIMEFRAMES, variable=self._tf_var,
            fg_color=BG_INPUT, button_color=ACCENT, button_hover_color=PURPLE,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
        )
        self._tf_menu.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        # Custom ticker entry
        ctk.CTkLabel(inner, text="Custom Ticker (optional)", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).grid(row=0, column=2, sticky="w", pady=(0, 2))
        self._custom_entry = ctk.CTkEntry(
            inner, fg_color=BG_INPUT, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_MONO,
            placeholder_text="e.g. AVAX, WIF, RTY …",
        )
        self._custom_entry.grid(row=1, column=2, sticky="ew", padx=(0, 8))

        self._run_btn = ctk.CTkButton(
            inner, text="▶  Run Backtest",
            fg_color=ACCENT, text_color=BG_DARK, font=("Inter", 13, "bold"),
            command=self._run,
        )
        self._run_btn.grid(row=1, column=3, sticky="ew")

        # ── Results ───────────────────────────────────────────────────────────
        results_card = Card(self, title="Backtest Results")
        results_card.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        self.log = LogBox(results_card, height=420)
        self.log.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    def _run(self):
        if self._running:
            return
        coin = self._custom_entry.get().strip().upper() or self._coin_var.get()
        tf   = self._tf_var.get()
        limit = _LIMITS.get(tf, 500)

        self._running = True
        self._run_btn.configure(state="disabled", text="⏳  Running…")
        self.log.clear()
        self.log.append(f"Running backtest — {coin} {tf} ({limit} bars)…", "INFO")

        threading.Thread(target=self._do_backtest, args=(coin, tf, limit), daemon=True).start()

    def _do_backtest(self, coin: str, tf: str, limit: int):
        try:
            from trading.pattern_engine import full_report, BUY_LABELS, SELL_LABELS
            verdict, stats = full_report(coin, tf, limit)
            self.after(0, self._show_results, coin, tf, verdict, stats)
        except Exception as e:
            self.after(0, self._show_error, str(e))
        finally:
            self.after(0, self._reset_btn)

    def _show_results(self, coin: str, tf: str, verdict, stats: dict):
        self.log.clear()
        self.log.append(f"═══  {coin} / {tf}  ═══", "INFO")
        self.log.append("", "INFO")

        # Current signal verdict
        action_color = "SUCCESS" if verdict.action == "LONG" \
                       else "ERROR" if verdict.action == "SHORT" else "INFO"
        self.log.append(f"CURRENT SIGNAL: {verdict.action}  ({verdict.confidence:.0f}% confidence)", action_color)
        if verdict.action != "WAIT":
            self.log.append(f"  Setup:      {verdict.label}", "INFO")
            self.log.append(f"  Entry:      ${verdict.entry_price:,.4f}", "INFO")
            self.log.append(f"  Stop Loss:  ${verdict.stop_loss:,.4f}", "ERROR")
            self.log.append(f"  Take Profit 1: ${verdict.take_profit_1:,.4f}", "SUCCESS")
            self.log.append(f"  Take Profit 2: ${verdict.take_profit_2:,.4f}", "SUCCESS")
            self.log.append(f"  Win Rate:   {verdict.win_rate*100:.0f}%  ({verdict.sample_size} signals)", "INFO")
            self.log.append(f"  Expectancy: {verdict.expectancy:+.2f}% per trade", "INFO")
            self.log.append(f"  R:R:        1:{verdict.rr:.1f}", "INFO")
        self.log.append(f"  Reasoning: {verdict.reasoning}", "INFO")

        self.log.append("", "INFO")
        self.log.append("─── HISTORICAL PATTERN STATS ───", "INFO")

        if not stats:
            self.log.append("No signals detected in this data window.", "WARNING")
        else:
            # Sort by count descending
            for lbl, s in sorted(stats.items(), key=lambda x: -x[1].count):
                is_buy  = lbl in {"BOTH_BUY", "HL_BUY", "XT_BUY"}
                is_sell = lbl in {"BOTH_SELL", "HL_SELL", "XT_SELL"}
                color = "SUCCESS" if is_buy else "ERROR" if is_sell else "INFO"
                wr_str = f"{s.win_rate*100:.0f}%" if s.count else "—"
                ev_str = f"{s.expectancy:+.2f}%" if s.count else "—"
                rr_str = f"1:{s.rr:.1f}" if s.avg_loss > 0 else "—"
                self.log.append(
                    f"  {lbl:12s}  {s.count:3d}×  WR:{wr_str:5s}  EV:{ev_str:7s}  "
                    f"R:R:{rr_str:6s}  "
                    f"avg+{s.avg_win:.2f}% / avg-{s.avg_loss:.2f}%",
                    color,
                )

        self.log.append("", "INFO")
        self.log.append("Backtest complete.", "SUCCESS")

    def _show_error(self, msg: str):
        self.log.append(f"Error: {msg}", "ERROR")

    def _reset_btn(self):
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Run Backtest")
