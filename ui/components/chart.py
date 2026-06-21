"""Embeddable candlestick + indicator chart using Matplotlib."""
from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from ui.theme import (
    CHART_BG, CHART_GRID, CHART_CANDLE_UP, CHART_CANDLE_DOWN,
    CHART_EMA_FAST, CHART_EMA_SLOW, CHART_ATR, ACCENT, RED, YELLOW,
)


class CandleChart(ctk.CTkFrame):
    """Renders OHLCV candles with EMA, HOTT/LOTT and RSI sub-panel."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", CHART_BG)
        super().__init__(master, **kwargs)

        self.fig, (self.ax_main, self.ax_rsi) = plt.subplots(
            2, 1, figsize=(10, 6),
            gridspec_kw={"height_ratios": [3, 1]},
            facecolor=CHART_BG,
        )
        self._style_axes()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _style_axes(self):
        for ax in (self.ax_main, self.ax_rsi):
            ax.set_facecolor(CHART_BG)
            ax.tick_params(colors="#8B949E", labelsize=8)
            ax.spines[:].set_color(CHART_GRID)
            ax.grid(color=CHART_GRID, linewidth=0.5, linestyle="--", alpha=0.6)
        self.fig.tight_layout(pad=1.5)

    def plot(self, df: pd.DataFrame, coin: str = "", interval: str = ""):
        """Draw candles + indicators from an analyzed DataFrame."""
        self.ax_main.clear()
        self.ax_rsi.clear()
        self._style_axes()

        if df.empty:
            self.canvas.draw()
            return

        idx = range(len(df))

        # ── Candlesticks ─────────────────────────────────────────────────────
        width = 0.6
        for i, row in enumerate(df.itertuples()):
            color = CHART_CANDLE_UP if row.close >= row.open else CHART_CANDLE_DOWN
            # Body
            self.ax_main.bar(i, abs(row.close - row.open), width, bottom=min(row.open, row.close), color=color, zorder=2)
            # Wick
            self.ax_main.plot([i, i], [row.low, row.high], color=color, linewidth=0.8, zorder=1)

        # ── EMAs ─────────────────────────────────────────────────────────────
        if "ema_fast" in df.columns:
            self.ax_main.plot(idx, df["ema_fast"], color=CHART_EMA_FAST, linewidth=1.2, label="EMA Fast", zorder=3)
        if "ema_slow" in df.columns:
            self.ax_main.plot(idx, df["ema_slow"], color=CHART_EMA_SLOW, linewidth=1.2, label="EMA Slow", zorder=3)

        # ── HOTT / LOTT ───────────────────────────────────────────────────────
        if "hott" in df.columns:
            self.ax_main.plot(idx, df["hott"], color=CHART_CANDLE_UP, linewidth=0.8, linestyle="--", alpha=0.7, label="HOTT")
        if "lott" in df.columns:
            self.ax_main.plot(idx, df["lott"], color=CHART_CANDLE_DOWN, linewidth=0.8, linestyle="--", alpha=0.7, label="LOTT")

        # ── X-axis labels ─────────────────────────────────────────────────────
        step = max(1, len(df) // 8)
        tick_idx = list(range(0, len(df), step))
        labels = [df["timestamp"].iloc[i].strftime("%m/%d %H:%M") for i in tick_idx]
        self.ax_main.set_xticks(tick_idx)
        self.ax_main.set_xticklabels(labels, rotation=20, ha="right", fontsize=7, color="#8B949E")
        self.ax_main.set_title(f"{coin} {interval}".strip(), color="#E6EDF3", fontsize=11, pad=6)
        self.ax_main.legend(fontsize=7, facecolor="#161B22", edgecolor="#30363D", labelcolor="#8B949E")

        # ── RSI sub-panel ─────────────────────────────────────────────────────
        if "rsi" in df.columns:
            self.ax_rsi.plot(idx, df["rsi"], color=ACCENT, linewidth=1.0)
            self.ax_rsi.axhline(70, color=RED, linewidth=0.6, linestyle="--", alpha=0.7)
            self.ax_rsi.axhline(30, color=CHART_CANDLE_UP, linewidth=0.6, linestyle="--", alpha=0.7)
            self.ax_rsi.fill_between(idx, df["rsi"], 70, where=df["rsi"] >= 70, alpha=0.15, color=RED)
            self.ax_rsi.fill_between(idx, df["rsi"], 30, where=df["rsi"] <= 30, alpha=0.15, color=CHART_CANDLE_UP)
            self.ax_rsi.set_ylim(0, 100)
            self.ax_rsi.set_ylabel("RSI", color="#8B949E", fontsize=8)
            self.ax_rsi.set_xticks([])

        self.fig.tight_layout(pad=1.5)
        self.canvas.draw()
