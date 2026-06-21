"""PnL Dashboard tab — equity curve, win/loss stats, trade history (#8)."""
from __future__ import annotations
import threading
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
from ui.theme import *
from ui.components.card import Card
from ui.components.stat_tile import StatTile
from ui.components.log_box import LogBox


class PnLDashboardTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._canvas = None
        self._fig    = None
        self._build()
        self.after(500, self._refresh)

    def _build(self):
        self.columnconfigure(0, weight=1)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        ctk.CTkLabel(top, text="PnL Dashboard", font=FONT_TITLE,
                     text_color=TEXT_PRIMARY).pack(side="left")
        ctk.CTkButton(top, text="🔄  Refresh", fg_color=BG_INPUT,
                      text_color=ACCENT, hover_color=BORDER,
                      command=self._refresh).pack(side="right")

        # ── Stat tiles ────────────────────────────────────────────────────────
        tiles = ctk.CTkFrame(self, fg_color="transparent")
        tiles.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(PAD, 0))
        for c in range(6):
            tiles.columnconfigure(c, weight=1, uniform="tile")

        self._t_total    = StatTile(tiles, "Total Trades",  "—")
        self._t_wins     = StatTile(tiles, "Wins",          "—")
        self._t_losses   = StatTile(tiles, "Losses",        "—")
        self._t_wr       = StatTile(tiles, "Win Rate",      "—")
        self._t_pnl      = StatTile(tiles, "Total PnL",     "—")
        self._t_avg      = StatTile(tiles, "Avg PnL/Trade", "—")
        for col, tile in enumerate([self._t_total, self._t_wins, self._t_losses,
                                     self._t_wr, self._t_pnl, self._t_avg]):
            tile.grid(row=0, column=col, padx=4, pady=4, sticky="ew")

        # ── Equity curve chart ────────────────────────────────────────────────
        chart_card = Card(self, title="Equity Curve")
        chart_card.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(PAD, 0))
        self.rowconfigure(2, weight=1)
        self._chart_frame = ctk.CTkFrame(chart_card, fg_color=BG_DARK)
        self._chart_frame.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # ── Recent trades ─────────────────────────────────────────────────────
        trades_card = Card(self, title="Recent Closed Trades")
        trades_card.grid(row=3, column=0, sticky="ew", padx=PAD, pady=(PAD, PAD))
        self.trade_log = LogBox(trades_card, height=130)
        self.trade_log.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _refresh(self):
        threading.Thread(target=self._load_data, daemon=True).start()

    def _load_data(self):
        try:
            from trading.trade_history import get_summary, get_equity_curve, get_closed_trades
            summary = get_summary()
            curve   = get_equity_curve()
            trades  = get_closed_trades(limit=50)
            self.after(0, self._update_ui, summary, curve, trades)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_ui(self, summary: dict, curve: list, trades: list):
        closed  = summary.get("closed") or 0
        wins    = summary.get("wins") or 0
        losses  = summary.get("losses") or 0
        pnl     = summary.get("total_pnl_usd") or 0.0
        avg_pnl = summary.get("avg_pnl_pct") or 0.0
        wr      = (wins / closed * 100) if closed else 0

        pnl_color = GREEN if pnl >= 0 else RED

        self._t_total.update_value(str(summary.get("total_trades", 0)))
        self._t_wins.update_value(str(wins), text_color=GREEN)
        self._t_losses.update_value(str(losses), text_color=RED)
        self._t_wr.update_value(f"{wr:.0f}%", text_color=GREEN if wr >= 52 else RED)
        self._t_pnl.update_value(f"${pnl:+,.2f}", text_color=pnl_color)
        self._t_avg.update_value(f"{avg_pnl:+.2f}%" if avg_pnl else "—")

        self._draw_curve(curve)

        self.trade_log.clear()
        if not trades:
            self.trade_log.append("No closed trades yet.", "INFO")
        for t in trades:
            outcome = t.get("outcome", "?")
            pct = t.get("pnl_pct") or 0.0
            color = "SUCCESS" if outcome == "win" else "ERROR" if outcome == "loss" else "INFO"
            ts = datetime.fromtimestamp(t["closed_at"]).strftime("%m/%d %H:%M") if t.get("closed_at") else "?"
            self.trade_log.append(
                f"{ts}  {t['action']:5s} {t['ticker']:6s}  "
                f"{t.get('signal_label',''):12s}  PnL: {pct:+.2f}%  [{outcome}]",
                color,
            )

    def _draw_curve(self, curve: list):
        if self._canvas:
            self._canvas.get_tk_widget().destroy()
            plt.close(self._fig)

        fig, ax = plt.subplots(figsize=(8, 3), facecolor=BG_DARK)
        ax.set_facecolor(BG_DARK)

        if curve:
            timestamps = [datetime.fromtimestamp(p["ts"]) for p in curve]
            cumulative = [p["cumulative"] for p in curve]

            color = GREEN if cumulative[-1] >= 0 else RED
            ax.plot(timestamps, cumulative, color=color, linewidth=2)
            ax.fill_between(timestamps, 0, cumulative,
                            alpha=0.15, color=color)
            ax.axhline(0, color=BORDER, linewidth=0.8, linestyle="--")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        else:
            ax.text(0.5, 0.5, "No closed trades yet", transform=ax.transAxes,
                    ha="center", va="center", color=TEXT_SECONDARY, fontsize=12)

        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        ax.yaxis.label.set_color(TEXT_SECONDARY)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.set_ylabel("Cumulative PnL ($)", color=TEXT_SECONDARY, fontsize=9)
        fig.tight_layout(pad=0.4)

        self._fig = fig
        self._canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def _show_error(self, msg: str):
        self.trade_log.clear()
        self.trade_log.append(f"Error loading data: {msg}", "ERROR")
