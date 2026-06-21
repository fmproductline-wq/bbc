"""
Main desktop application window.

Run with:  python desktop_app.py
"""
import sys
import threading
from pathlib import Path
import customtkinter as ctk
from ui.theme import (
    BG_DARK, BG_CARD, BORDER, ACCENT, PURPLE, GREEN, RED, WHITE,
    TEXT_PRIMARY, TEXT_SECONDARY, FONT_TITLE, FONT_BODY, FONT_SMALL,
)


# ── CustomTkinter global config ───────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SidebarButton(ctk.CTkButton):
    """Styled navigation button for the sidebar."""

    def __init__(self, master, text: str, icon: str = "", active: bool = False, **kwargs):
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("height", 40)
        kwargs.setdefault("anchor", "w")
        kwargs.setdefault("font", FONT_BODY)
        kwargs.setdefault("fg_color", ACCENT if active else "transparent")
        kwargs.setdefault("text_color", WHITE if active else TEXT_PRIMARY)
        kwargs.setdefault("hover_color", "#1A1A2E")
        super().__init__(master, text=f"  {icon}  {text}" if icon else f"  {text}", **kwargs)


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Best Brand Co.")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(fg_color=BG_DARK)

        self._active_tab: str = ""
        self._tab_frames: dict[str, ctk.CTkFrame] = {}
        self._sidebar_buttons: dict[str, SidebarButton] = {}

        self._build_layout()
        self._init_tabs()
        self._navigate("Dashboard")
        self._start_auto_refresh()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_layout(self):
        # Root grid: sidebar | content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=BG_CARD,
                                     corner_radius=0, border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo / title
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=12, pady=(20, 8))

        _logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if _logo_path.exists():
            try:
                from PIL import Image
                _img = ctk.CTkImage(
                    light_image=Image.open(_logo_path),
                    dark_image=Image.open(_logo_path),
                    size=(160, 52),
                )
                ctk.CTkLabel(logo_frame, image=_img, text="").pack(anchor="w")
            except Exception:
                _logo_path = None

        if not _logo_path or not _logo_path.exists():
            ctk.CTkLabel(
                logo_frame,
                text="Best Brand Co.",
                font=("Inter", 18, "bold"),
                text_color=ACCENT,
            ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=12, pady=(0, 8))

        # Nav buttons
        nav_items = [
            ("Dashboard",    "🏠"),
            ("Trading",      "📈"),
            ("Analysis",     "🔭"),
            ("Predictions",  "🎰"),
            ("Bug Checker",  "🔍"),
            ("Settings",     "⚙️"),
        ]
        for name, icon in nav_items:
            btn = SidebarButton(self.sidebar, text=name, icon=icon,
                                command=lambda n=name: self._navigate(n))
            btn.pack(fill="x", padx=8, pady=2)
            self._sidebar_buttons[name] = btn

        # Separator + status
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=12, pady=(12, 8))

        self.status_dot = ctk.CTkLabel(self.sidebar, text="● Server: OFF",
                                        font=FONT_SMALL, text_color=RED)
        self.status_dot.pack(anchor="w", padx=16)

        self.auto_trade_indicator = ctk.CTkLabel(self.sidebar, text="● Auto-Trade: OFF",
                                                  font=FONT_SMALL, text_color=RED)
        self.auto_trade_indicator.pack(anchor="w", padx=16, pady=2)

        self.signal_count = ctk.CTkLabel(self.sidebar, text="Signals: 0",
                                          font=FONT_SMALL, text_color=TEXT_SECONDARY)
        self.signal_count.pack(anchor="w", padx=16, pady=2)

        # Start/Stop webhook server
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=12, pady=(12, 8))

        self._server_running = False
        self.server_btn = ctk.CTkButton(
            self.sidebar, text="▶  Start Server",
            fg_color=GREEN, text_color="black", font=("Inter", 12, "bold"),
            command=self._toggle_server,
        )
        self.server_btn.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(self.sidebar, text="Webhook on :8000",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(anchor="w", padx=16, pady=(2, 0))

        # ── Watchlist ─────────────────────────────────────────────────────────
        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=12, pady=(12, 4))

        from ui.components.watchlist import WatchlistPanel
        self.watchlist = WatchlistPanel(self.sidebar, border_width=0)
        self.watchlist.pack(fill="x", padx=4, pady=(0, 4))
        self.watchlist.set_on_select(self._on_symbol_select)

        # Version footer
        ctk.CTkLabel(self.sidebar, text="v2.0 · Best Brand Co.",
                     font=FONT_SMALL, text_color=PURPLE).pack(
            side="bottom", pady=12)

        # ── Content area ──────────────────────────────────────────────────────
        self.content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew", padx=0)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        # Top bar
        self.topbar = ctk.CTkFrame(self.content, fg_color=BG_CARD, height=52,
                                    corner_radius=0, border_width=0)
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_propagate(False)

        self.page_title = ctk.CTkLabel(self.topbar, text="Dashboard",
                                        font=("Inter", 16, "bold"), text_color=TEXT_PRIMARY)
        self.page_title.pack(side="left", padx=20, pady=14)

        self.notif_label = ctk.CTkLabel(self.topbar, text="", font=FONT_SMALL,
                                         text_color=TEXT_SECONDARY)
        self.notif_label.pack(side="right", padx=20)

        # Tab container
        self.tab_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.tab_container.grid(row=1, column=0, sticky="nsew")
        self.tab_container.grid_columnconfigure(0, weight=1)
        self.tab_container.grid_rowconfigure(0, weight=1)

    # ── Tab init ──────────────────────────────────────────────────────────────

    def _init_tabs(self):
        from ui.tabs.dashboard        import DashboardTab
        from ui.tabs.trading          import TradingTab
        from ui.tabs.analysis         import AnalysisTab
        from ui.tabs.prediction_markets import PredictionMarketsTab
        from ui.tabs.bug_checker      import BugCheckerTab
        from ui.tabs.settings         import SettingsTab

        tab_classes = {
            "Dashboard":   DashboardTab,
            "Trading":     TradingTab,
            "Analysis":    AnalysisTab,
            "Predictions": PredictionMarketsTab,
            "Bug Checker": BugCheckerTab,
            "Settings":    SettingsTab,
        }
        for name, cls in tab_classes.items():
            frame = cls(self.tab_container, app=self)
            frame.grid(row=0, column=0, sticky="nsew")
            self._tab_frames[name] = frame

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _navigate(self, name: str):
        self._active_tab = name
        self.page_title.configure(text=name)

        for n, btn in self._sidebar_buttons.items():
            btn.configure(fg_color=ACCENT if n == name else "transparent")

        for n, frame in self._tab_frames.items():
            if n == name:
                frame.tkraise()

    # ── Server toggle ──────────────────────────────────────────────────────────

    def _toggle_server(self):
        if self._server_running:
            self.set_notification("Server stopping is not supported mid-session. Restart the app.")
            return
        self._server_running = True
        self.server_btn.configure(text="⏹  Server Running", fg_color=BORDER, text_color=TEXT_SECONDARY)
        self.status_dot.configure(text="● Server: ON", text_color=GREEN)
        threading.Thread(target=self._run_server, daemon=True).start()

    def _run_server(self):
        try:
            import uvicorn
            import main as bot_main
            uvicorn.run(bot_main.app, host="0.0.0.0", port=8000, log_level="warning")
        except Exception as e:
            self.after(0, self.set_notification, f"Server error: {e}")
            self.after(0, self.status_dot.configure, {"text": "● Server: ERR", "text_color": RED})

    # ── Auto-refresh sidebar indicators ───────────────────────────────────────

    def _start_auto_refresh(self):
        self._refresh_indicators()

    def _refresh_indicators(self):
        try:
            from trading.state import state
            count = len(state.signal_log)
            self.signal_count.configure(text=f"Signals: {count}")
            if state.auto_trade:
                self.auto_trade_indicator.configure(text="● Auto-Trade: ON", text_color=GREEN)
            else:
                self.auto_trade_indicator.configure(text="● Auto-Trade: OFF", text_color=RED)
        except Exception:
            pass
        self.after(5000, self._refresh_indicators)

    # ── Symbol sync (Watchlist → Analysis chart, private) ────────────────────

    def _on_symbol_select(self, ticker: str, display_name: str):
        """
        Called when user clicks a symbol in the watchlist.
        Navigates to Analysis tab and loads the private in-app chart.
        No data leaves the app — all indicators run locally.
        """
        # Also sync coin field in Trading tab
        trading = self._tab_frames.get("Trading")
        if trading:
            for entry in (getattr(trading, "price_coin", None),
                          getattr(trading, "coin_entry", None)):
                if entry:
                    entry.delete(0, "end")
                    entry.insert(0, ticker)

        # Navigate to Analysis and trigger chart load
        self._navigate("Analysis")
        analysis = self._tab_frames.get("Analysis")
        if analysis and hasattr(analysis, "load_symbol"):
            analysis.load_symbol(ticker)

        self.set_notification(f"📊 {display_name} — loading chart…", color=ACCENT)

    # ── Notifications ──────────────────────────────────────────────────────────

    def set_notification(self, text: str, color: str = TEXT_SECONDARY):
        self.notif_label.configure(text=text, text_color=color)
        self.after(6000, lambda: self.notif_label.configure(text=""))


def run_app():
    """Entry point: show age gate + T&C, then launch main window."""
    from ui.terms_dialog import run_onboarding
    root = ctk.CTk()
    root.withdraw()

    accepted = run_onboarding(root)
    root.destroy()

    if not accepted:
        sys.exit(0)

    app = MainApp()
    app.mainloop()
