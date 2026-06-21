"""Private in-app candlestick chart with full indicator suite."""
from __future__ import annotations
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
from ui.theme import (
    CHART_BG, CHART_GRID, CHART_CANDLE_UP, CHART_CANDLE_DOWN,
    CHART_EMA_FAST, CHART_EMA_SLOW, CHART_ATR, ACCENT, RED, YELLOW,
    PURPLE,
)

_TICK_COLOR = "#8B949E"
_LABEL_COLOR = "#E6EDF3"


class CandleChart(ctk.CTkFrame):
    """Full private chart — candles, EMA, HOTT/LOTT, RSI, MACD, Volume."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", CHART_BG)
        super().__init__(master, **kwargs)
        self._build_figure(show_macd=False, show_volume=False)

    def _build_figure(self, show_macd=False, show_volume=False):
        """(Re)build the matplotlib figure with the right subplot layout."""
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().destroy()
            plt.close(self.fig)

        # Decide sub-panels
        ratios = [4]        # main candle panel always present
        n_sub = 1           # RSI always
        ratios.append(1)
        if show_macd:
            ratios.append(1); n_sub += 1
        if show_volume:
            ratios.append(0.7); n_sub += 1

        n_rows = 1 + n_sub
        self.fig = plt.figure(figsize=(11, 7), facecolor=CHART_BG)
        gs = gridspec.GridSpec(n_rows, 1, figure=self.fig,
                               height_ratios=ratios, hspace=0.08)

        self.ax_main = self.fig.add_subplot(gs[0])
        self.ax_rsi  = self.fig.add_subplot(gs[1], sharex=self.ax_main)

        idx = 2
        self.ax_macd = self.fig.add_subplot(gs[idx], sharex=self.ax_main) if show_macd else None
        if show_macd: idx += 1
        self.ax_vol  = self.fig.add_subplot(gs[idx], sharex=self.ax_main) if show_volume else None

        for ax in self.fig.get_axes():
            ax.set_facecolor(CHART_BG)
            ax.tick_params(colors=_TICK_COLOR, labelsize=7)
            ax.spines[:].set_color(CHART_GRID)
            ax.grid(color=CHART_GRID, linewidth=0.4, linestyle="--", alpha=0.5)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def plot(self, df: pd.DataFrame, coin: str = "", interval: str = "",
             show_macd: bool = False, show_volume: bool = False):
        """Draw the complete private chart from a DataFrame with indicator columns."""
        self._build_figure(show_macd=show_macd, show_volume=show_volume)

        if df.empty:
            self.canvas.draw()
            return

        idx = range(len(df))

        # ── Candlesticks ──────────────────────────────────────────────────────
        width = 0.6
        for i, row in enumerate(df.itertuples()):
            color = CHART_CANDLE_UP if row.close >= row.open else CHART_CANDLE_DOWN
            self.ax_main.bar(i, abs(row.close - row.open), width,
                             bottom=min(row.open, row.close), color=color, zorder=2)
            self.ax_main.plot([i, i], [row.low, row.high],
                              color=color, linewidth=0.8, zorder=1)

        # ── EMA lines ─────────────────────────────────────────────────────────
        if "ema_fast" in df.columns:
            self.ax_main.plot(idx, df["ema_fast"], color=CHART_EMA_FAST,
                              linewidth=1.3, label="EMA 9", zorder=3)
        if "ema_slow" in df.columns:
            self.ax_main.plot(idx, df["ema_slow"], color=CHART_EMA_SLOW,
                              linewidth=1.3, label="EMA 21", zorder=3)

        # ── HOTT / LOTT ───────────────────────────────────────────────────────
        if "hott" in df.columns:
            self.ax_main.plot(idx, df["hott"], color=CHART_CANDLE_UP,
                              linewidth=0.9, linestyle="--", alpha=0.8, label="HOTT")
        if "lott" in df.columns:
            self.ax_main.plot(idx, df["lott"], color=CHART_CANDLE_DOWN,
                              linewidth=0.9, linestyle="--", alpha=0.8, label="LOTT")

        # ── X-axis labels ─────────────────────────────────────────────────────
        step = max(1, len(df) // 8)
        tick_idx = list(range(0, len(df), step))
        labels = [df["timestamp"].iloc[i].strftime("%m/%d %H:%M") for i in tick_idx]
        self.ax_main.set_xticks(tick_idx)
        self.ax_main.set_xticklabels(labels, rotation=20, ha="right",
                                     fontsize=7, color=_TICK_COLOR)
        self.ax_main.set_title(
            f"  {coin}  {interval}   [Private — indicators run locally]",
            color=_LABEL_COLOR, fontsize=10, pad=6, loc="left",
        )
        self.ax_main.legend(fontsize=7, facecolor="#161B22",
                            edgecolor="#30363D", labelcolor=_TICK_COLOR)
        plt.setp(self.ax_main.get_xticklabels(), visible=False)

        # ── RSI ───────────────────────────────────────────────────────────────
        if "rsi" in df.columns:
            self.ax_rsi.plot(idx, df["rsi"], color=ACCENT, linewidth=1.0)
            self.ax_rsi.axhline(70, color=RED, linewidth=0.6, linestyle="--", alpha=0.7)
            self.ax_rsi.axhline(30, color=CHART_CANDLE_UP, linewidth=0.6, linestyle="--", alpha=0.7)
            self.ax_rsi.fill_between(idx, df["rsi"], 70, where=df["rsi"] >= 70,
                                     alpha=0.12, color=RED)
            self.ax_rsi.fill_between(idx, df["rsi"], 30, where=df["rsi"] <= 30,
                                     alpha=0.12, color=CHART_CANDLE_UP)
            self.ax_rsi.set_ylim(0, 100)
            self.ax_rsi.set_ylabel("RSI", color=_TICK_COLOR, fontsize=7)
        plt.setp(self.ax_rsi.get_xticklabels(), visible=False)

        # ── MACD ──────────────────────────────────────────────────────────────
        if self.ax_macd is not None and "macd" in df.columns:
            self.ax_macd.plot(idx, df["macd"], color=ACCENT, linewidth=0.9, label="MACD")
            self.ax_macd.plot(idx, df["macd_signal"], color=YELLOW,
                              linewidth=0.9, label="Signal")
            if "macd_hist" in df.columns:
                colors = [CHART_CANDLE_UP if v >= 0 else CHART_CANDLE_DOWN
                          for v in df["macd_hist"]]
                self.ax_macd.bar(idx, df["macd_hist"], color=colors, alpha=0.5, width=0.6)
            self.ax_macd.axhline(0, color=CHART_GRID, linewidth=0.5)
            self.ax_macd.set_ylabel("MACD", color=_TICK_COLOR, fontsize=7)
            self.ax_macd.legend(fontsize=6, facecolor="#161B22",
                                edgecolor="#30363D", labelcolor=_TICK_COLOR)
            plt.setp(self.ax_macd.get_xticklabels(), visible=False)

        # ── Volume ────────────────────────────────────────────────────────────
        if self.ax_vol is not None and "volume" in df.columns:
            vol_colors = [CHART_CANDLE_UP if df["close"].iloc[i] >= df["open"].iloc[i]
                          else CHART_CANDLE_DOWN for i in range(len(df))]
            self.ax_vol.bar(idx, df["volume"], color=vol_colors, alpha=0.6, width=0.6)
            self.ax_vol.set_ylabel("Vol", color=_TICK_COLOR, fontsize=7)

        self.fig.tight_layout(pad=1.2)
        self.canvas.draw()
