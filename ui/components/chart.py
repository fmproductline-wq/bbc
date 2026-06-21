"""
Best Brand Co. — Private In-App Chart

Proprietary indicators always-on (non-removable):
  • HOTT — High Optimised Trend Tracker  (upper band, teal fill)
  • LOTT — Low  Optimised Trend Tracker  (lower band, red fill)
  • Xtreme Trend — buy ▲ / sell ▼ signal arrows on the candles

Optional sub-panels (user toggles):
  • RSI  •  MACD  •  Volume
"""
from __future__ import annotations
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.lines import Line2D
import pandas as pd
from ui.theme import (
    CHART_BG, CHART_GRID, CHART_CANDLE_UP, CHART_CANDLE_DOWN,
    CHART_EMA_FAST, CHART_EMA_SLOW, ACCENT, RED, YELLOW, PURPLE,
)

_TICK      = "#8B949E"
_TITLE_FG  = "#E6EDF3"

# ── Brand colours for proprietary indicators ──────────────────────────────────
_HOTT_COLOR  = "#00D4AA"   # teal  — upper tracker
_LOTT_COLOR  = "#FF4D6D"   # rose  — lower tracker
_XT_BUY      = "#00FF88"   # bright green arrow  ▲
_XT_SELL     = "#FF3366"   # bright red arrow    ▼
_XT_NEUTRAL  = "#888888"


class CandleChart(ctk.CTkFrame):
    """Best Brand Co. private chart with always-on HOTT/LOTT + Xtreme Trend."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", CHART_BG)
        super().__init__(master, **kwargs)
        self._built_with = (False, False)   # (show_macd, show_volume)
        self._build_figure(False, False)

    # ── Figure construction ───────────────────────────────────────────────────

    def _build_figure(self, show_macd: bool, show_volume: bool):
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().destroy()
            plt.close(self.fig)

        ratios = [5, 1]                       # main + RSI always present
        if show_macd:   ratios.append(1)
        if show_volume: ratios.append(0.8)

        self.fig = plt.figure(figsize=(11, 7), facecolor=CHART_BG)
        gs = gridspec.GridSpec(len(ratios), 1, figure=self.fig,
                               height_ratios=ratios, hspace=0.06)

        panel = iter(range(len(ratios)))
        self.ax_main = self.fig.add_subplot(gs[next(panel)])
        self.ax_rsi  = self.fig.add_subplot(gs[next(panel)], sharex=self.ax_main)
        self.ax_macd = self.fig.add_subplot(gs[next(panel)], sharex=self.ax_main) if show_macd  else None
        self.ax_vol  = self.fig.add_subplot(gs[next(panel)], sharex=self.ax_main) if show_volume else None

        for ax in self.fig.get_axes():
            ax.set_facecolor(CHART_BG)
            ax.tick_params(colors=_TICK, labelsize=7)
            ax.spines[:].set_color(CHART_GRID)
            ax.grid(color=CHART_GRID, linewidth=0.35, linestyle="--", alpha=0.45)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._built_with = (show_macd, show_volume)

    # ── Main draw ─────────────────────────────────────────────────────────────

    def plot(self, df: pd.DataFrame, coin: str = "", interval: str = "",
             show_macd: bool = False, show_volume: bool = False):
        """Render all panels. HOTT/LOTT and Xtreme Trend are always drawn."""
        if self._built_with != (show_macd, show_volume):
            self._build_figure(show_macd, show_volume)

        for ax in self.fig.get_axes():
            ax.cla()
            ax.set_facecolor(CHART_BG)
            ax.tick_params(colors=_TICK, labelsize=7)
            ax.grid(color=CHART_GRID, linewidth=0.35, linestyle="--", alpha=0.45)

        if df.empty:
            self.canvas.draw()
            return

        idx = list(range(len(df)))

        # ── 1. Candlesticks ───────────────────────────────────────────────────
        for i, row in enumerate(df.itertuples()):
            up    = row.close >= row.open
            color = CHART_CANDLE_UP if up else CHART_CANDLE_DOWN
            self.ax_main.bar(i, abs(row.close - row.open), 0.6,
                             bottom=min(row.open, row.close),
                             color=color, zorder=2)
            self.ax_main.plot([i, i], [row.low, row.high],
                              color=color, linewidth=0.8, zorder=1)

        # ── 2. ★ HOTT / LOTT — always on ★ ──────────────────────────────────
        if "hott" in df.columns and "lott" in df.columns:
            self.ax_main.plot(idx, df["hott"], color=_HOTT_COLOR,
                              linewidth=2.0, zorder=4, label="HOTT")
            self.ax_main.plot(idx, df["lott"], color=_LOTT_COLOR,
                              linewidth=2.0, zorder=4, label="LOTT")
            # Shaded channel between HOTT and LOTT
            self.ax_main.fill_between(idx, df["hott"], df["lott"],
                                      alpha=0.07, color=ACCENT, zorder=0)

        # ── 3. ★ Xtreme Trend arrows — always on ★ ───────────────────────────
        if "xt_signal" in df.columns:
            buy_idx  = [i for i, v in enumerate(df["xt_signal"]) if v ==  1]
            sell_idx = [i for i, v in enumerate(df["xt_signal"]) if v == -1]

            if buy_idx:
                buy_prices  = [df["low"].iloc[i]  * 0.997 for i in buy_idx]
                self.ax_main.scatter(buy_idx, buy_prices,
                                     marker="^", color=_XT_BUY,
                                     s=55, zorder=6, label="XT Buy")

            if sell_idx:
                sell_prices = [df["high"].iloc[i] * 1.003 for i in sell_idx]
                self.ax_main.scatter(sell_idx, sell_prices,
                                     marker="v", color=_XT_SELL,
                                     s=55, zorder=6, label="XT Sell")

        # ── 4. EMA overlay (optional — only drawn if columns present) ─────────
        if "ema_fast" in df.columns:
            self.ax_main.plot(idx, df["ema_fast"], color=CHART_EMA_FAST,
                              linewidth=1.1, alpha=0.85, label="EMA 9")
        if "ema_slow" in df.columns:
            self.ax_main.plot(idx, df["ema_slow"], color=CHART_EMA_SLOW,
                              linewidth=1.1, alpha=0.85, label="EMA 21")

        # ── 5. Title + x-axis labels ──────────────────────────────────────────
        step     = max(1, len(df) // 8)
        tick_idx = list(range(0, len(df), step))
        labels   = [df["timestamp"].iloc[i].strftime("%m/%d %H:%M")
                    for i in tick_idx]
        self.ax_main.set_xticks(tick_idx)
        self.ax_main.set_xticklabels(labels, rotation=20, ha="right",
                                     fontsize=7, color=_TICK)
        self.ax_main.set_title(
            f"  {coin}   {interval}",
            color=_TITLE_FG, fontsize=11, pad=5, loc="left", fontweight="bold",
        )

        # Custom legend showing proprietary indicators first
        legend_els = [
            Line2D([0], [0], color=_HOTT_COLOR, linewidth=2,    label="HOTT"),
            Line2D([0], [0], color=_LOTT_COLOR, linewidth=2,    label="LOTT"),
            Line2D([0], [0], marker="^", color=_XT_BUY,  linestyle="none",
                   markersize=7, label="Xtreme ▲ BUY"),
            Line2D([0], [0], marker="v", color=_XT_SELL, linestyle="none",
                   markersize=7, label="Xtreme ▼ SELL"),
        ]
        if "ema_fast" in df.columns:
            legend_els.append(Line2D([0], [0], color=CHART_EMA_FAST,
                                     linewidth=1.2, label="EMA 9"))
        if "ema_slow" in df.columns:
            legend_els.append(Line2D([0], [0], color=CHART_EMA_SLOW,
                                     linewidth=1.2, label="EMA 21"))

        self.ax_main.legend(handles=legend_els, fontsize=7,
                            facecolor="#161B22", edgecolor="#30363D",
                            labelcolor=_TICK, loc="upper left")
        plt.setp(self.ax_main.get_xticklabels(), visible=False)

        # ── 6. RSI sub-panel ──────────────────────────────────────────────────
        if "rsi" in df.columns:
            self.ax_rsi.plot(idx, df["rsi"], color=ACCENT, linewidth=1.0)
            self.ax_rsi.axhline(70, color=RED,             linewidth=0.6, linestyle="--")
            self.ax_rsi.axhline(30, color=CHART_CANDLE_UP, linewidth=0.6, linestyle="--")
            self.ax_rsi.fill_between(idx, df["rsi"], 70,
                                     where=df["rsi"] >= 70, alpha=0.12, color=RED)
            self.ax_rsi.fill_between(idx, df["rsi"], 30,
                                     where=df["rsi"] <= 30, alpha=0.12, color=CHART_CANDLE_UP)
            self.ax_rsi.set_ylim(0, 100)
            self.ax_rsi.set_ylabel("RSI", color=_TICK, fontsize=7)
        plt.setp(self.ax_rsi.get_xticklabels(), visible=False)

        # ── 7. MACD sub-panel ─────────────────────────────────────────────────
        if self.ax_macd is not None and "macd" in df.columns:
            self.ax_macd.plot(idx, df["macd"],        color=ACCENT,  linewidth=0.9, label="MACD")
            self.ax_macd.plot(idx, df["macd_signal"], color=YELLOW,  linewidth=0.9, label="Signal")
            if "macd_hist" in df.columns:
                bar_colors = [CHART_CANDLE_UP if v >= 0 else CHART_CANDLE_DOWN
                              for v in df["macd_hist"]]
                self.ax_macd.bar(idx, df["macd_hist"], color=bar_colors, alpha=0.5, width=0.6)
            self.ax_macd.axhline(0, color=CHART_GRID, linewidth=0.5)
            self.ax_macd.set_ylabel("MACD", color=_TICK, fontsize=7)
            self.ax_macd.legend(fontsize=6, facecolor="#161B22",
                                edgecolor="#30363D", labelcolor=_TICK)
            plt.setp(self.ax_macd.get_xticklabels(), visible=False)

        # ── 8. Volume sub-panel ───────────────────────────────────────────────
        if self.ax_vol is not None and "volume" in df.columns:
            vcols = [CHART_CANDLE_UP if df["close"].iloc[i] >= df["open"].iloc[i]
                     else CHART_CANDLE_DOWN for i in range(len(df))]
            self.ax_vol.bar(idx, df["volume"], color=vcols, alpha=0.6, width=0.6)
            self.ax_vol.set_ylabel("Vol", color=_TICK, fontsize=7)

        self.fig.tight_layout(pad=1.0)
        self.canvas.draw()
