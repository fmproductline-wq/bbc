"""Analysis tab — private in-app chart with full indicator suite."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.chart import CandleChart
from ui.components.log_box import LogBox


class AnalysisTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._last_df = None
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1, minsize=280)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        # ── Left panel: controls + report ─────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(PAD, 4), pady=PAD)

        ctrl_card = Card(left, title="Chart & Analysis")
        ctrl_card.pack(fill="x")

        form = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        form.pack(fill="x", padx=PAD, pady=(0, PAD))

        def lbl(t): return ctk.CTkLabel(form, text=t, font=FONT_SMALL,
                                         text_color=TEXT_SECONDARY, anchor="w")

        lbl("Symbol").pack(fill="x", pady=(4, 2))
        self.coin_e = ctk.CTkEntry(form, fg_color=BG_INPUT, border_color=BORDER,
                                    text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.coin_e.insert(0, "BTC")
        self.coin_e.pack(fill="x")

        lbl("Timeframe").pack(fill="x", pady=(8, 2))
        self.tf_box = ctk.CTkComboBox(
            form, values=["1m", "5m", "15m", "1h", "4h", "1d"],
            fg_color=BG_INPUT, border_color=BORDER,
            text_color=TEXT_PRIMARY, button_color=ACCENT,
            dropdown_fg_color=BG_CARD, font=FONT_BODY,
        )
        self.tf_box.set("1h")
        self.tf_box.pack(fill="x")

        lbl("Candles").pack(fill="x", pady=(8, 2))
        self.limit_e = ctk.CTkEntry(form, fg_color=BG_INPUT, border_color=BORDER,
                                     text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.limit_e.insert(0, "120")
        self.limit_e.pack(fill="x")

        # ── Built-in indicators (always on, non-removable) ────────────────────
        built_in_frame = ctk.CTkFrame(form, fg_color=BG_INPUT,
                                       corner_radius=6, border_width=1,
                                       border_color=BORDER)
        built_in_frame.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(built_in_frame, text="● BUILT-IN  (always on)",
                     font=("Inter", 9, "bold"), text_color=ACCENT).pack(anchor="w", padx=8, pady=(6, 2))
        for txt in ["  HOTT — High Optimised Trend Tracker", "  LOTT — Low  Optimised Trend Tracker",
                    "  Xtreme Trend  ▲▼  signals"]:
            ctk.CTkLabel(built_in_frame, text=txt, font=FONT_SMALL,
                         text_color=TEXT_SECONDARY).pack(anchor="w", padx=8, pady=1)
        ctk.CTkFrame(built_in_frame, height=4, fg_color="transparent").pack()

        # ── Optional overlays ─────────────────────────────────────────────────
        lbl("Optional overlays").pack(fill="x", pady=(10, 4))
        ind_row = ctk.CTkFrame(form, fg_color="transparent")
        ind_row.pack(fill="x")

        self._show_ema    = ctk.BooleanVar(value=True)
        self._show_rsi    = ctk.BooleanVar(value=True)
        self._show_macd   = ctk.BooleanVar(value=False)
        self._show_volume = ctk.BooleanVar(value=False)

        def ck(text, var):
            return ctk.CTkCheckBox(ind_row, text=text, variable=var,
                                   font=FONT_SMALL, text_color=TEXT_SECONDARY,
                                   fg_color=ACCENT, border_color=BORDER,
                                   checkmark_color=BG_DARK,
                                   command=self._redraw_if_ready)

        for w in [ck("EMA 9 / 21", self._show_ema), ck("RSI", self._show_rsi),
                  ck("MACD", self._show_macd), ck("Volume", self._show_volume)]:
            w.pack(anchor="w", pady=1)

        ctk.CTkButton(form, text="▶  Load Chart", fg_color=ACCENT, text_color=BG_DARK,
                      font=("Inter", 13, "bold"),
                      command=self._run_analysis).pack(fill="x", pady=14)

        # Source label
        self.source_lbl = ctk.CTkLabel(form, text="", font=FONT_SMALL,
                                        text_color=TEXT_MUTED)
        self.source_lbl.pack(anchor="w")

        # Report card
        report_card = Card(left, title="Pattern Verdict + Report")
        report_card.pack(fill="both", expand=True, pady=(8, 0))

        self.report_box = LogBox(report_card, height=400)
        self.report_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # ── Right panel: in-app chart ─────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, PAD), pady=PAD)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        chart_card = Card(right, title="")
        chart_card.grid(row=0, column=0, sticky="nsew")
        chart_card.rowconfigure(0, weight=1)
        chart_card.columnconfigure(0, weight=1)

        self.chart = CandleChart(chart_card)
        self.chart.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

    # ── Public API: called by watchlist click ─────────────────────────────────

    def load_symbol(self, ticker: str, timeframe: str | None = None):
        """Switch to ticker (and optional timeframe) and run analysis."""
        self.coin_e.delete(0, "end")
        self.coin_e.insert(0, ticker)
        if timeframe:
            self.tf_box.set(timeframe)
        self._run_analysis()

    # ── Analysis runner ───────────────────────────────────────────────────────

    def _run_analysis(self):
        coin = self.coin_e.get().strip().upper()
        tf   = self.tf_box.get()
        try:
            limit = int(self.limit_e.get())
        except ValueError:
            limit = 120

        self.report_box.clear()
        self.report_box.append(f"Loading {coin} {tf}…", "INFO")

        def _do():
            try:
                from analysis.data_fetcher import fetch_candles, is_crypto
                from analysis import market_analyzer as ma

                src = "Hyperliquid" if is_crypto(coin) else "Yahoo Finance"
                self.after(0, self.source_lbl.configure,
                           {"text": f"Data: {src} · Private"})

                df = fetch_candles(coin, tf, limit)
                if df.empty:
                    self.after(0, self.report_box.append,
                               f"No data for {coin} — check ticker", "ERROR")
                    return

                # ── Proprietary indicators — always calculated, always shown ──
                df = ma.hott_lott(df)       # adds: hott, lott, hott_lott_trend
                df = ma.xtreme_trend(df)    # adds: ema_fast, ema_slow, xt_signal

                from analysis.market_analyzer import rsi as calc_rsi, ema
                df["rsi"] = calc_rsi(df["close"])

                # ── Optional overlays ────────────────────────────────────────
                # xtreme_trend already sets ema_fast/slow (8/21); override with
                # display EMAs (9/21) only if user wants the EMA overlay.
                if not self._show_ema.get():
                    df = df.drop(columns=["ema_fast", "ema_slow"], errors="ignore")

                if self._show_macd.get():
                    exp1 = df["close"].ewm(span=12, adjust=False).mean()
                    exp2 = df["close"].ewm(span=26, adjust=False).mean()
                    df["macd"]        = exp1 - exp2
                    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
                    df["macd_hist"]   = df["macd"] - df["macd_signal"]

                if not self._show_rsi.get():
                    df = df.drop(columns=["rsi"], errors="ignore")

                # ── Chart ───────────────────────────────────────────────────
                self.after(0, self.chart.plot, df, coin, tf,
                           self._show_macd.get(), self._show_volume.get())
                self._last_df = df

                # ── Pattern engine verdict (works on ALL assets) ─────────────
                try:
                    # Fetch more history for backtest accuracy
                    from trading.pattern_engine import evaluate_current, backtest_signals
                    hist_limit = max(limit, 300)
                    from analysis.data_fetcher import fetch_candles as _fc
                    df_hist = _fc(coin, tf, hist_limit)
                    verdict = evaluate_current(df_hist)
                    all_stats = backtest_signals(df_hist)
                    self.after(0, self._render_verdict, verdict, all_stats, coin, tf)
                except Exception as pe:
                    self.after(0, self.report_box.append, f"Pattern engine: {pe}", "WARNING")

            except Exception as e:
                self.after(0, self.report_box.append, f"Failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    def _redraw_if_ready(self):
        if self._last_df is not None and not self._last_df.empty:
            self._run_analysis()

    def _render_verdict(self, verdict, all_stats, coin, tf):
        """Display pattern engine verdict and all historical stats."""
        action = verdict.action
        c = verdict.confidence

        action_level = (
            "SUCCESS" if action == "LONG" else
            "ERROR"   if action == "SHORT" else
            "WARNING"
        )
        bar = "█" * int(c / 10) + "░" * (10 - int(c / 10))

        lines = [
            ("═" * 38, "DEFAULT"),
            (f" {coin}  {tf}  —  ${verdict.entry_price:,.4f}", "DEFAULT"),
            ("═" * 38, "DEFAULT"),
            (f"▶ VERDICT:  {action}  [{bar}] {c:.0f}%", action_level),
            (f"  Setup:    {verdict.label}", action_level),
            ("─" * 38, "DEFAULT"),
        ]

        if action != "WAIT":
            lines += [
                (f"  Win rate:   {verdict.win_rate*100:.0f}%  ({verdict.sample_size} signals)", "DEFAULT"),
                (f"  Expectancy: {verdict.expectancy:+.2f}% per trade", "DEFAULT"),
                (f"  R:R ratio:  1:{verdict.rr:.1f}", "DEFAULT"),
                ("─" * 38, "DEFAULT"),
                (f"  Entry:  ${verdict.entry_price:,.4f}", "DEFAULT"),
                (f"  Stop:   ${verdict.stop_loss:,.4f}", "ERROR"),
                (f"  TP 1:   ${verdict.take_profit_1:,.4f}", "SUCCESS"),
                (f"  TP 2:   ${verdict.take_profit_2:,.4f}", "SUCCESS"),
                ("─" * 38, "DEFAULT"),
            ]

        lines.append((verdict.reasoning, "DEFAULT"))
        lines.append(("═" * 38, "DEFAULT"))

        # ── Historical pattern stats ──────────────────────────────────────────
        if all_stats:
            lines.append(("PATTERN HISTORY (last 300 bars)", "INFO"))
            lines.append(("─" * 38, "DEFAULT"))
            for lbl, s in sorted(all_stats.items(), key=lambda x: -x[1].expectancy):
                lvl = "SUCCESS" if s.expectancy > 0.1 else "ERROR" if s.expectancy < 0 else "DEFAULT"
                lines.append((s.summary(), lvl))

        self.report_box.clear()
        for text, level in lines:
            self.report_box.append(text, level)
