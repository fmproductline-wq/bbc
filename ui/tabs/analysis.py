"""Analysis tab — market analysis + live candlestick chart."""
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

        ctrl_card = Card(left, title="Market Analysis")
        ctrl_card.pack(fill="x")

        form = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        form.pack(fill="x", padx=PAD, pady=(0, PAD))

        def lbl(t): return ctk.CTkLabel(form, text=t, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        lbl("Coin").pack(fill="x", pady=(4, 2))
        self.coin_e = ctk.CTkEntry(form, fg_color=BG_INPUT, border_color=BORDER,
                                    text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.coin_e.insert(0, "BTC")
        self.coin_e.pack(fill="x")

        lbl("Timeframe").pack(fill="x", pady=(8, 2))
        self.tf_box = ctk.CTkComboBox(form, values=["1m", "5m", "15m", "1h", "4h", "1d"],
                                       fg_color=BG_INPUT, border_color=BORDER,
                                       text_color=TEXT_PRIMARY, button_color=ACCENT,
                                       dropdown_fg_color=BG_CARD, font=FONT_BODY)
        self.tf_box.set("1h")
        self.tf_box.pack(fill="x")

        lbl("Candles").pack(fill="x", pady=(8, 2))
        self.limit_e = ctk.CTkEntry(form, fg_color=BG_INPUT, border_color=BORDER,
                                     text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.limit_e.insert(0, "120")
        self.limit_e.pack(fill="x")

        ctk.CTkButton(form, text="▶  Analyze", fg_color=ACCENT, text_color=BG_DARK,
                      font=("Inter", 13, "bold"),
                      command=self._run_analysis).pack(fill="x", pady=14)

        # Report card
        report_card = Card(left, title="Analysis Report")
        report_card.pack(fill="both", expand=True, pady=(8, 0))

        self.report_box = LogBox(report_card, height=400)
        self.report_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # ── Right panel: chart ────────────────────────────────────────────────
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

    def _run_analysis(self):
        coin = self.coin_e.get().strip().upper()
        tf   = self.tf_box.get()
        try:
            limit = int(self.limit_e.get())
        except ValueError:
            limit = 120

        self.report_box.clear()
        self.report_box.append(f"Analyzing {coin} {tf}…", "INFO")

        def _do():
            try:
                from analysis import market_analyzer as ma
                report = ma.analyze(coin, tf, limit)

                # Render to log box
                lines = [
                    ("─" * 38, "DEFAULT"),
                    (f" {coin} / {tf}  —  ${report.price:,.4f}", "DEFAULT"),
                    ("─" * 38, "DEFAULT"),
                    (f"Trend:      {report.trend} ({report.strength})",
                     "SUCCESS" if report.trend == "BULLISH" else "ERROR" if report.trend == "BEARISH" else "DEFAULT"),
                    (f"RSI:        {report.rsi_val:.1f}", "DEFAULT"),
                    (f"MACD:       {report.macd_cross}", "SUCCESS" if report.macd_cross == "BULLISH" else "ERROR" if report.macd_cross == "BEARISH" else "DEFAULT"),
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
                ]
                self.after(0, self.report_box.clear)
                for text, level in lines:
                    self.after(0, self.report_box.append, text, level)

                # Chart: re-fetch df with indicators
                df = ma.fetch_candles(coin, tf, limit)
                df = ma.hott_lott(df)
                df = ma.xtreme_trend(df)
                from analysis.market_analyzer import rsi as calc_rsi
                df["rsi"] = calc_rsi(df["close"])
                self.after(0, self.chart.plot, df, coin, tf)

            except Exception as e:
                self.after(0, self.report_box.append, f"Analysis failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()
