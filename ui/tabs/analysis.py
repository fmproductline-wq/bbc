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
        report_card = Card(left, title="Signal Report")
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

                # ── Signal report (crypto only via market_analyzer) ──────────
                if is_crypto(coin):
                    try:
                        report = ma.analyze(coin, tf, limit)
                        lines = self._format_report(report, coin, tf)
                        self.after(0, self.report_box.clear)
                        for text, level in lines:
                            self.after(0, self.report_box.append, text, level)
                    except Exception as re:
                        self.after(0, self.report_box.append,
                                   f"Signal analysis: {re}", "WARNING")
                else:
                    self._after_basic_report(df, coin, tf)

            except Exception as e:
                self.after(0, self.report_box.append, f"Failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    def _redraw_if_ready(self):
        if self._last_df is not None and not self._last_df.empty:
            self._run_analysis()

    def _after_basic_report(self, df, coin, tf):
        """Price/momentum report for non-crypto assets (futures, FX, indices)."""
        import numpy as np
        close   = df["close"]
        rsi_val = df["rsi"].iloc[-1] if "rsi" in df.columns else float("nan")
        change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100 if len(close) > 1 else 0.0
        ma20  = close.rolling(20).mean().iloc[-1]
        trend = "BULLISH" if close.iloc[-1] > ma20 else "BEARISH"

        hl_signal = int(df["hott_lott_trend"].iloc[-1]) if "hott_lott_trend" in df.columns else 0
        xt_signal = int(df["xt_signal"].iloc[-1])       if "xt_signal"       in df.columns else 0

        lines = [
            ("─" * 38, "DEFAULT"),
            (f" {coin} / {tf}  —  ${close.iloc[-1]:,.4f}", "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            (f"Change:       {change_pct:+.2f}%",
             "SUCCESS" if change_pct >= 0 else "ERROR"),
            (f"Trend (MA20): {trend}",
             "SUCCESS" if trend == "BULLISH" else "ERROR"),
            (f"RSI:          {rsi_val:.1f}" if not np.isnan(rsi_val) else "RSI: —", "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            (f"HOTT/LOTT:    {'▲ UP' if hl_signal==1 else '▼ DOWN' if hl_signal==-1 else '— FLAT'}",
             "SUCCESS" if hl_signal == 1 else "ERROR" if hl_signal == -1 else "DEFAULT"),
            (f"Xtreme Trend: {'▲ BUY' if xt_signal==1 else '▼ SELL' if xt_signal==-1 else '— FLAT'}",
             "SUCCESS" if xt_signal == 1 else "ERROR" if xt_signal == -1 else "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            ("Indicators calculated locally — data is private.", "DEFAULT"),
        ]
        self.after(0, self.report_box.clear)
        for text, level in lines:
            self.after(0, self.report_box.append, text, level)

    def _format_report(self, report, coin, tf) -> list[tuple[str, str]]:
        return [
            ("─" * 38, "DEFAULT"),
            (f" {coin} / {tf}  —  ${report.price:,.4f}", "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            (f"Trend:      {report.trend} ({report.strength})",
             "SUCCESS" if report.trend == "BULLISH" else "ERROR" if report.trend == "BEARISH" else "DEFAULT"),
            (f"RSI:        {report.rsi_val:.1f}", "DEFAULT"),
            (f"MACD:       {report.macd_cross}",
             "SUCCESS" if report.macd_cross == "BULLISH" else "ERROR" if report.macd_cross == "BEARISH" else "DEFAULT"),
            (f"ATR:        {report.atr_val:.4f}", "DEFAULT"),
            (f"Volatility: {report.volatility_pct:.2f}%", "DEFAULT"),
            (f"Xtreme Trend: {'▲ BUY' if report.xt_signal==1 else '▼ SELL' if report.xt_signal==-1 else '— FLAT'}",
             "SUCCESS" if report.xt_signal == 1 else "ERROR" if report.xt_signal == -1 else "DEFAULT"),
            (f"HOTT/LOTT:  {'▲ UP' if report.hott_lott_signal==1 else '▼ DOWN' if report.hott_lott_signal==-1 else '— FLAT'}",
             "SUCCESS" if report.hott_lott_signal == 1 else "ERROR" if report.hott_lott_signal == -1 else "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            (f"Action:     {report.suggested_action}",
             "SUCCESS" if "LONG" in report.suggested_action else "ERROR" if "SHORT" in report.suggested_action else "WARNING"),
            (f"Stop Loss:  ${report.stop_loss:,.4f}", "ERROR"),
            (f"TP1:        ${report.take_profit_1:,.4f}", "SUCCESS"),
            (f"TP2:        ${report.take_profit_2:,.4f}", "SUCCESS"),
            ("─" * 38, "DEFAULT"),
            (report.summary, "DEFAULT"),
            ("─" * 38, "DEFAULT"),
            ("All indicators calculated locally — data is private.", "DEFAULT"),
        ]
