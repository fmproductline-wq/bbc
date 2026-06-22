"""
Marketing Manager tab — control the ebook sales bot from the desktop.

Sub-tabs:
  Dashboard   — bot status, last post times, quick-run buttons
  Campaigns   — platform toggles, style hints, run + schedule controls
  Content Lab — generate & preview posts per platform, edit before posting
  Sales       — aggregate sales data from Gumroad / Stripe / SendOwl
  Email       — AI email sequence generator
  Settings    — ebook metadata + API key configuration
"""
import threading
import os
import json
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from ui.theme import (
    BG_DARK, BG_CARD, BG_INPUT, BORDER, ACCENT, GREEN, RED, YELLOW,
    PURPLE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL, FONT_MONO,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _card(parent, **kw):
    kw.setdefault("fg_color", BG_CARD)
    kw.setdefault("corner_radius", 10)
    kw.setdefault("border_width", 1)
    kw.setdefault("border_color", BORDER)
    return ctk.CTkFrame(parent, **kw)


def _label(parent, text, font=FONT_BODY, color=TEXT_PRIMARY, **kw):
    return ctk.CTkLabel(parent, text=text, font=font, text_color=color, **kw)


def _section_header(parent, title):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(fill="x", padx=16, pady=(14, 2))
    _label(f, title, font=FONT_HEADER).pack(side="left")
    ctk.CTkFrame(f, height=1, fg_color=BORDER).pack(side="left", fill="x", expand=True, padx=(10, 0))
    return f


def _entry_row(parent, label, var, show=""):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=3)
    _label(row, label, color=TEXT_SECONDARY, width=220, anchor="w").pack(side="left")
    e = ctk.CTkEntry(row, textvariable=var, fg_color=BG_INPUT, border_color=BORDER,
                     text_color=TEXT_PRIMARY, show=show)
    e.pack(side="left", fill="x", expand=True)
    return e


def _dot(parent, color=GREEN):
    return ctk.CTkLabel(parent, text="●", font=FONT_SMALL, text_color=color)


# ── Platform list ─────────────────────────────────────────────────────────────

PLATFORMS = ["twitter", "linkedin", "facebook", "instagram", "reddit", "pinterest", "telegram"]

PLATFORM_ICONS = {
    "twitter":   "𝕏",
    "linkedin":  "in",
    "facebook":  "f",
    "instagram": "📷",
    "reddit":    "👾",
    "pinterest": "📌",
    "telegram":  "✈️",
}

PLATFORM_NAMES = {
    "twitter":   "Twitter / X",
    "linkedin":  "LinkedIn",
    "facebook":  "Facebook",
    "instagram": "Instagram",
    "reddit":    "Reddit",
    "pinterest": "Pinterest",
    "telegram":  "Telegram",
}


# ─────────────────────────────────────────────────────────────────────────────
#  Main Tab
# ─────────────────────────────────────────────────────────────────────────────

class MarketingTab(ctk.CTkFrame):

    def __init__(self, master, app=None, **kw):
        super().__init__(master, fg_color=BG_DARK, **kw)
        self.app = app

        # Shared state
        self._platform_vars: dict[str, ctk.BooleanVar] = {p: ctk.BooleanVar(value=True) for p in PLATFORMS}
        self._use_ai_var = ctk.BooleanVar(value=True)
        self._style_var  = ctk.StringVar(value="")
        self._interval_var = ctk.IntVar(value=6)
        self._scheduler_thread: threading.Thread | None = None
        self._scheduler_running = False
        self._post_log: list[dict] = []

        # Ebook settings vars
        self._ebook_vars = {
            "EBOOK_TITLE":         ctk.StringVar(value=os.getenv("EBOOK_TITLE", "")),
            "EBOOK_TAGLINE":       ctk.StringVar(value=os.getenv("EBOOK_TAGLINE", "")),
            "EBOOK_PRICE":         ctk.StringVar(value=os.getenv("EBOOK_PRICE", "")),
            "EBOOK_AUTHOR":        ctk.StringVar(value=os.getenv("EBOOK_AUTHOR", "")),
            "EBOOK_DESCRIPTION":   ctk.StringVar(value=os.getenv("EBOOK_DESCRIPTION", "")),
            "EBOOK_TOPICS":        ctk.StringVar(value=os.getenv("EBOOK_TOPICS", "")),
            "EBOOK_COVER_IMAGE_URL": ctk.StringVar(value=os.getenv("EBOOK_COVER_IMAGE_URL", "")),
        }
        self._api_vars = {
            "ANTHROPIC_API_KEY":         ctk.StringVar(value=os.getenv("ANTHROPIC_API_KEY", "")),
            "GUMROAD_ACCESS_TOKEN":      ctk.StringVar(value=os.getenv("GUMROAD_ACCESS_TOKEN", "")),
            "GUMROAD_PRODUCT_ID":        ctk.StringVar(value=os.getenv("GUMROAD_PRODUCT_ID", "")),
            "PAYHIP_PRODUCT_LINK":       ctk.StringVar(value=os.getenv("PAYHIP_PRODUCT_LINK", "")),
            "STRIPE_SECRET_KEY":         ctk.StringVar(value=os.getenv("STRIPE_SECRET_KEY", "")),
            "STRIPE_PRICE_ID":           ctk.StringVar(value=os.getenv("STRIPE_PRICE_ID", "")),
            "TWITTER_API_KEY":           ctk.StringVar(value=os.getenv("TWITTER_API_KEY", "")),
            "TWITTER_API_SECRET":        ctk.StringVar(value=os.getenv("TWITTER_API_SECRET", "")),
            "TWITTER_ACCESS_TOKEN":      ctk.StringVar(value=os.getenv("TWITTER_ACCESS_TOKEN", "")),
            "TWITTER_ACCESS_TOKEN_SECRET": ctk.StringVar(value=os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")),
            "LINKEDIN_ACCESS_TOKEN":     ctk.StringVar(value=os.getenv("LINKEDIN_ACCESS_TOKEN", "")),
            "LINKEDIN_PERSON_URN":       ctk.StringVar(value=os.getenv("LINKEDIN_PERSON_URN", "")),
            "META_ACCESS_TOKEN":         ctk.StringVar(value=os.getenv("META_ACCESS_TOKEN", "")),
            "FACEBOOK_PAGE_ID":          ctk.StringVar(value=os.getenv("FACEBOOK_PAGE_ID", "")),
            "INSTAGRAM_ACCOUNT_ID":      ctk.StringVar(value=os.getenv("INSTAGRAM_ACCOUNT_ID", "")),
            "REDDIT_CLIENT_ID":          ctk.StringVar(value=os.getenv("REDDIT_CLIENT_ID", "")),
            "REDDIT_CLIENT_SECRET":      ctk.StringVar(value=os.getenv("REDDIT_CLIENT_SECRET", "")),
            "REDDIT_USERNAME":           ctk.StringVar(value=os.getenv("REDDIT_USERNAME", "")),
            "REDDIT_PASSWORD":           ctk.StringVar(value=os.getenv("REDDIT_PASSWORD", "")),
            "REDDIT_SUBREDDITS":         ctk.StringVar(value=os.getenv("REDDIT_SUBREDDITS", "ebooks,selfpublishing")),
            "PINTEREST_ACCESS_TOKEN":    ctk.StringVar(value=os.getenv("PINTEREST_ACCESS_TOKEN", "")),
            "PINTEREST_BOARD_ID":        ctk.StringVar(value=os.getenv("PINTEREST_BOARD_ID", "")),
            "TELEGRAM_BOT_TOKEN":        ctk.StringVar(value=os.getenv("TELEGRAM_BOT_TOKEN", "")),
            "TELEGRAM_CHANNEL_ID":       ctk.StringVar(value=os.getenv("TELEGRAM_CHANNEL_ID", "")),
        }

        # Generated content cache {platform: text}
        self._generated: dict[str, str] = {}
        self._content_textboxes: dict[str, ctk.CTkTextbox] = {}

        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self, fg_color=BG_DARK, segmented_button_fg_color=BG_CARD,
                               segmented_button_selected_color=ACCENT,
                               segmented_button_selected_hover_color="#5A52E0",
                               segmented_button_unselected_color=BG_CARD,
                               segmented_button_unselected_hover_color=BG_INPUT,
                               text_color=TEXT_PRIMARY)
        tabs.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        for name in ("Dashboard", "Campaigns", "Content Lab", "Sales", "Email", "Settings"):
            tabs.add(name)

        self._build_dashboard(tabs.tab("Dashboard"))
        self._build_campaigns(tabs.tab("Campaigns"))
        self._build_content_lab(tabs.tab("Content Lab"))
        self._build_sales(tabs.tab("Sales"))
        self._build_email(tabs.tab("Email"))
        self._build_settings(tabs.tab("Settings"))

    # ── Dashboard tab ─────────────────────────────────────────────────────────

    def _build_dashboard(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure((0, 1), weight=1)
        parent.grid_rowconfigure(2, weight=1)

        # ── Stat row ──────────────────────────────────────────────────────────
        stat_row = ctk.CTkFrame(parent, fg_color="transparent")
        stat_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=(16, 8))
        stat_row.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._stat_tiles = {}
        stats = [
            ("total_posts", "Total Posts", "0", ACCENT),
            ("success_rate", "Success Rate", "—", GREEN),
            ("scheduler",   "Scheduler",   "OFF", RED),
            ("last_run",    "Last Run",    "Never", TEXT_SECONDARY),
        ]
        for col, (key, label, val, color) in enumerate(stats):
            tile = _card(stat_row)
            tile.grid(row=0, column=col, padx=6, pady=0, sticky="ew")
            _label(tile, label, font=FONT_SMALL, color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
            v_lbl = _label(tile, val, font=("Inter", 20, "bold"), color=color)
            v_lbl.pack(anchor="w", padx=14, pady=(0, 10))
            self._stat_tiles[key] = v_lbl

        # ── Platform status grid ──────────────────────────────────────────────
        plat_card = _card(parent)
        plat_card.grid(row=1, column=0, padx=(16, 8), pady=8, sticky="nsew")
        _label(plat_card, "Platform Status", font=FONT_HEADER).pack(anchor="w", padx=14, pady=(12, 8))

        self._platform_status_labels: dict[str, ctk.CTkLabel] = {}
        self._platform_last_labels:   dict[str, ctk.CTkLabel] = {}

        for p in PLATFORMS:
            row = ctk.CTkFrame(plat_card, fg_color=BG_INPUT, corner_radius=6)
            row.pack(fill="x", padx=10, pady=3)
            row.grid_columnconfigure(1, weight=1)

            _label(row, PLATFORM_ICONS.get(p, "•"), font=("Inter", 12, "bold")).grid(row=0, column=0, padx=(10, 6), pady=8)
            _label(row, PLATFORM_NAMES[p]).grid(row=0, column=1, sticky="w", pady=8)

            dot = _dot(row, RED)
            dot.grid(row=0, column=2, padx=4)
            self._platform_status_labels[p] = dot

            last = _label(row, "Never", font=FONT_SMALL, color=TEXT_MUTED)
            last.grid(row=0, column=3, padx=(0, 10))
            self._platform_last_labels[p] = last

        # ── Quick actions ─────────────────────────────────────────────────────
        act_card = _card(parent)
        act_card.grid(row=1, column=1, padx=(8, 16), pady=8, sticky="nsew")
        _label(act_card, "Quick Actions", font=FONT_HEADER).pack(anchor="w", padx=14, pady=(12, 8))

        ctk.CTkButton(
            act_card, text="▶  Run Campaign Now", font=("Inter", 13, "bold"),
            fg_color=ACCENT, hover_color="#5A52E0", height=44,
            command=self._run_campaign_now,
        ).pack(fill="x", padx=12, pady=4)

        self._sched_btn = ctk.CTkButton(
            act_card, text="⏰  Start Scheduler", font=FONT_BODY,
            fg_color=GREEN, text_color="black", height=38,
            command=self._toggle_scheduler,
        )
        self._sched_btn.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            act_card, text="🔄  Refresh Sales Data", font=FONT_BODY,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            text_color=TEXT_PRIMARY, height=38,
            command=self._refresh_sales,
        ).pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            act_card, text="📋  Generate All Content", font=FONT_BODY,
            fg_color=BG_INPUT, border_color=BORDER, border_width=1,
            text_color=TEXT_PRIMARY, height=38,
            command=self._generate_all_content,
        ).pack(fill="x", padx=12, pady=4)

        # Interval display
        _label(act_card, "Post interval (hours):", color=TEXT_SECONDARY).pack(anchor="w", padx=14, pady=(14, 2))
        interval_row = ctk.CTkFrame(act_card, fg_color="transparent")
        interval_row.pack(fill="x", padx=12, pady=(0, 4))
        ctk.CTkSlider(
            interval_row, from_=1, to=24, variable=self._interval_var,
            fg_color=BG_INPUT, progress_color=ACCENT, button_color=ACCENT,
        ).pack(side="left", fill="x", expand=True)
        _label(interval_row, "", color=TEXT_PRIMARY, width=32).pack(side="left", padx=6)
        self._interval_display = ctk.CTkLabel(interval_row, text="6h", font=FONT_BODY, text_color=ACCENT)
        self._interval_display.pack(side="left")
        self._interval_var.trace_add("write", lambda *_: self._interval_display.configure(
            text=f"{self._interval_var.get()}h"))

        # ── Activity log ──────────────────────────────────────────────────────
        log_card = _card(parent)
        log_card.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="nsew")
        _label(log_card, "Activity Log", font=FONT_HEADER).pack(anchor="w", padx=14, pady=(12, 4))

        self._log_box = ctk.CTkTextbox(
            log_card, fg_color=BG_INPUT, text_color=TEXT_SECONDARY,
            font=FONT_MONO, border_width=0, state="disabled",
        )
        self._log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ── Campaigns tab ─────────────────────────────────────────────────────────

    def _build_campaigns(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        # ── Platform toggles ──────────────────────────────────────────────────
        _section_header(scroll, "Active Platforms")
        plat_grid = ctk.CTkFrame(scroll, fg_color="transparent")
        plat_grid.pack(fill="x", padx=16, pady=(6, 0))
        plat_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        for i, p in enumerate(PLATFORMS):
            tile = _card(plat_grid)
            tile.grid(row=i // 4, column=i % 4, padx=6, pady=6, sticky="ew")
            icon_row = ctk.CTkFrame(tile, fg_color="transparent")
            icon_row.pack(fill="x", padx=10, pady=(10, 4))
            _label(icon_row, PLATFORM_ICONS.get(p, "•"), font=("Inter", 18)).pack(side="left")
            ctk.CTkSwitch(
                icon_row, text="", variable=self._platform_vars[p],
                onvalue=True, offvalue=False,
                progress_color=ACCENT, button_color=TEXT_PRIMARY,
            ).pack(side="right")
            _label(tile, PLATFORM_NAMES[p], font=FONT_SMALL, color=TEXT_SECONDARY).pack(anchor="w", padx=10, pady=(0, 10))

        # ── Content settings ──────────────────────────────────────────────────
        _section_header(scroll, "Content Settings")
        content_card = _card(scroll)
        content_card.pack(fill="x", padx=16, pady=8)

        ai_row = ctk.CTkFrame(content_card, fg_color="transparent")
        ai_row.pack(fill="x", padx=14, pady=(12, 6))
        _label(ai_row, "Use Claude AI to generate posts").pack(side="left")
        ctk.CTkSwitch(
            ai_row, text="", variable=self._use_ai_var,
            progress_color=PURPLE, button_color=TEXT_PRIMARY,
        ).pack(side="right")

        _label(content_card, "Style hint (optional):", color=TEXT_SECONDARY).pack(anchor="w", padx=14, pady=(6, 2))
        ctk.CTkEntry(
            content_card, textvariable=self._style_var, placeholder_text='e.g. "make it funny" or "ask a question"',
            fg_color=BG_INPUT, border_color=BORDER, text_color=TEXT_PRIMARY,
        ).pack(fill="x", padx=14, pady=(0, 12))

        # ── Run controls ──────────────────────────────────────────────────────
        _section_header(scroll, "Run Campaign")
        run_card = _card(scroll)
        run_card.pack(fill="x", padx=16, pady=8)

        btn_row = ctk.CTkFrame(run_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=12)
        btn_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_row, text="▶  Run Now (All Selected Platforms)",
            fg_color=ACCENT, hover_color="#5A52E0",
            font=("Inter", 13, "bold"), height=44,
            command=self._run_campaign_now,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self._sched_btn2 = ctk.CTkButton(
            btn_row, text="⏰  Start Scheduler",
            fg_color=GREEN, text_color="black",
            font=("Inter", 13, "bold"), height=44,
            command=self._toggle_scheduler,
        )
        self._sched_btn2.grid(row=0, column=1, padx=(6, 0), sticky="ew")

        self._progress_label = _label(run_card, "Idle", color=TEXT_MUTED)
        self._progress_label.pack(anchor="w", padx=14, pady=(0, 12))

    # ── Content Lab tab ───────────────────────────────────────────────────────

    def _build_content_lab(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Top controls
        ctrl = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, border_width=0)
        ctrl.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 1))

        _label(ctrl, "Generate platform content using AI or templates",
               color=TEXT_SECONDARY).pack(side="left", padx=16, pady=12)

        ctk.CTkButton(
            ctrl, text="✨ Generate All", fg_color=PURPLE,
            font=("Inter", 12, "bold"), width=140,
            command=self._generate_all_content,
        ).pack(side="right", padx=8, pady=10)

        ctk.CTkButton(
            ctrl, text="🚀 Post All", fg_color=ACCENT,
            font=("Inter", 12, "bold"), width=120,
            command=self._post_all_generated,
        ).pack(side="right", padx=(0, 4), pady=10)

        # Scrollable platform content editors
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1), weight=1)

        for i, p in enumerate(PLATFORMS):
            card = _card(scroll)
            card.grid(row=i // 2, column=i % 2, padx=8, pady=8, sticky="nsew")
            scroll.grid_rowconfigure(i // 2, weight=1)

            # Header
            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=10, pady=(10, 4))
            _label(hdr, f"{PLATFORM_ICONS[p]}  {PLATFORM_NAMES[p]}", font=FONT_HEADER).pack(side="left")

            btn_frame = ctk.CTkFrame(hdr, fg_color="transparent")
            btn_frame.pack(side="right")
            ctk.CTkButton(
                btn_frame, text="✨ Gen", width=60, height=26,
                fg_color=PURPLE, font=FONT_SMALL,
                command=lambda _p=p: self._generate_one(platform=_p),
            ).pack(side="left", padx=2)
            ctk.CTkButton(
                btn_frame, text="Post", width=52, height=26,
                fg_color=ACCENT, font=FONT_SMALL,
                command=lambda _p=p: self._post_one(platform=_p),
            ).pack(side="left", padx=2)

            # Char count
            char_lbl = _label(card, "0 chars", font=FONT_SMALL, color=TEXT_MUTED)
            char_lbl.pack(anchor="e", padx=12)

            # Textbox
            tb = ctk.CTkTextbox(
                card, fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
                font=FONT_BODY, border_width=0, height=140,
                wrap="word",
            )
            tb.pack(fill="both", expand=True, padx=10, pady=(2, 10))
            self._content_textboxes[p] = tb

            # Update char count on key
            def _update_count(event, _lbl=char_lbl, _tb=tb):
                n = len(_tb.get("1.0", "end").strip())
                color = RED if n > 280 and _tb is self._content_textboxes.get("twitter") else TEXT_MUTED
                _lbl.configure(text=f"{n} chars", text_color=color)
            tb.bind("<KeyRelease>", _update_count)

    # ── Sales tab ─────────────────────────────────────────────────────────────

    def _build_sales(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, border_width=0)
        ctrl.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 1))
        _label(ctrl, "Sales data from all connected platforms", color=TEXT_SECONDARY).pack(side="left", padx=16, pady=12)
        ctk.CTkButton(ctrl, text="🔄 Refresh", fg_color=ACCENT, width=100,
                      command=self._refresh_sales).pack(side="right", padx=12, pady=10)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure((0, 1, 2), weight=1)

        # Summary tiles
        self._sales_tiles: dict[str, ctk.CTkLabel] = {}
        for col, (key, label) in enumerate([
            ("total_revenue", "Total Revenue"),
            ("total_sales",   "Total Sales"),
            ("platforms",     "Active Platforms"),
        ]):
            tile = _card(scroll)
            tile.grid(row=0, column=col, padx=8, pady=(8, 4), sticky="ew")
            _label(tile, label, font=FONT_SMALL, color=TEXT_MUTED).pack(anchor="w", padx=14, pady=(10, 2))
            lbl = _label(tile, "—", font=("Inter", 22, "bold"), color=ACCENT)
            lbl.pack(anchor="w", padx=14, pady=(0, 10))
            self._sales_tiles[key] = lbl

        # Per-platform sales tables
        self._sales_boxes: dict[str, ctk.CTkTextbox] = {}
        for row, (name, color) in enumerate([
            ("Gumroad", GREEN), ("Stripe", PURPLE), ("SendOwl", YELLOW)
        ], start=1):
            card = _card(scroll)
            card.grid(row=row, column=0, columnspan=3, padx=8, pady=4, sticky="nsew")
            scroll.grid_rowconfigure(row, weight=1)

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=14, pady=(10, 4))
            _dot(hdr, color).pack(side="left", padx=(0, 6))
            _label(hdr, name, font=FONT_HEADER).pack(side="left")

            tb = ctk.CTkTextbox(card, fg_color=BG_INPUT, text_color=TEXT_SECONDARY,
                                 font=FONT_MONO, border_width=0, height=110, state="disabled")
            tb.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self._sales_boxes[name.lower()] = tb

    # ── Email tab ─────────────────────────────────────────────────────────────

    def _build_email(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        ctrl = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=0, border_width=0)
        ctrl.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 1))
        _label(ctrl, "AI-generated email marketing sequence for your ebook",
               color=TEXT_SECONDARY).pack(side="left", padx=16, pady=12)

        num_var = ctk.IntVar(value=3)
        _label(ctrl, "Emails:", color=TEXT_SECONDARY).pack(side="right", padx=(0, 6), pady=12)
        ctk.CTkOptionMenu(ctrl, values=["1", "2", "3", "5"],
                           variable=num_var,
                           fg_color=BG_INPUT, button_color=ACCENT,
                           text_color=TEXT_PRIMARY, width=60,
                           ).pack(side="right", pady=10)

        ctk.CTkButton(ctrl, text="✨ Generate Sequence", fg_color=PURPLE,
                      font=("Inter", 12, "bold"), width=180,
                      command=lambda: self._generate_emails(num_var.get()),
                      ).pack(side="right", padx=8, pady=10)

        # Output area
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        self._email_frames: list[tuple] = []
        for i in range(5):
            card = _card(scroll)
            card.grid(row=i, column=0, padx=16, pady=6, sticky="ew")
            scroll.grid_rowconfigure(i, weight=0)

            subj_row = ctk.CTkFrame(card, fg_color="transparent")
            subj_row.pack(fill="x", padx=14, pady=(10, 4))
            _label(subj_row, f"Email {i + 1} — Subject:", font=FONT_HEADER).pack(side="left")
            copy_btn = ctk.CTkButton(subj_row, text="Copy", width=60, height=26,
                                      fg_color=BG_INPUT, border_color=BORDER, border_width=1,
                                      text_color=TEXT_PRIMARY, font=FONT_SMALL)
            copy_btn.pack(side="right")

            subj_lbl = _label(card, "", color=ACCENT, font=("Inter", 12, "bold"))
            subj_lbl.pack(anchor="w", padx=14, pady=(0, 6))

            tb = ctk.CTkTextbox(card, fg_color=BG_INPUT, text_color=TEXT_SECONDARY,
                                  font=FONT_BODY, border_width=0, height=130, wrap="word")
            tb.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            # Wire copy button
            def _make_copy(btn, _subj=subj_lbl, _tb=tb):
                def _copy():
                    text = f"Subject: {_subj.cget('text')}\n\n{_tb.get('1.0', 'end').strip()}"
                    btn.master.clipboard_clear()
                    btn.master.clipboard_append(text)
                    btn.configure(text="Copied!")
                    btn.after(1500, lambda: btn.configure(text="Copy"))
                return _copy
            copy_btn.configure(command=_make_copy(copy_btn))

            card.grid_remove()
            self._email_frames.append((card, subj_lbl, tb))

    # ── Settings tab ─────────────────────────────────────────────────────────

    def _build_settings(self, parent):
        parent.configure(fg_color=BG_DARK)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Ebook metadata ─────────────────────────────────────────────────
        _section_header(scroll, "Ebook Information")
        meta_card = _card(scroll)
        meta_card.pack(fill="x", padx=16, pady=8)

        labels = {
            "EBOOK_TITLE":           "Title",
            "EBOOK_TAGLINE":         "Tagline",
            "EBOOK_PRICE":           "Price (e.g. $9.99)",
            "EBOOK_AUTHOR":          "Author name",
            "EBOOK_DESCRIPTION":     "Description",
            "EBOOK_TOPICS":          "Topics (comma-separated)",
            "EBOOK_COVER_IMAGE_URL": "Cover image URL",
        }
        for key, lbl in labels.items():
            _entry_row(meta_card, lbl, self._ebook_vars[key])

        # ── AI ─────────────────────────────────────────────────────────────
        _section_header(scroll, "AI & Claude")
        ai_card = _card(scroll)
        ai_card.pack(fill="x", padx=16, pady=8)
        _entry_row(ai_card, "Anthropic API Key", self._api_vars["ANTHROPIC_API_KEY"], show="*")

        # ── Sales platforms ────────────────────────────────────────────────
        _section_header(scroll, "Sales Platforms")
        sales_card = _card(scroll)
        sales_card.pack(fill="x", padx=16, pady=8)
        for key, lbl in [
            ("GUMROAD_ACCESS_TOKEN", "Gumroad Access Token"),
            ("GUMROAD_PRODUCT_ID",   "Gumroad Product ID"),
            ("PAYHIP_PRODUCT_LINK",  "Payhip Product Link"),
            ("STRIPE_SECRET_KEY",    "Stripe Secret Key"),
            ("STRIPE_PRICE_ID",      "Stripe Price ID"),
        ]:
            _entry_row(sales_card, lbl, self._api_vars[key],
                       show="*" if "KEY" in key or "TOKEN" in key else "")

        # ── Social platforms ───────────────────────────────────────────────
        social_groups = [
            ("Twitter / X", [
                ("TWITTER_API_KEY",             "API Key"),
                ("TWITTER_API_SECRET",          "API Secret"),
                ("TWITTER_ACCESS_TOKEN",        "Access Token"),
                ("TWITTER_ACCESS_TOKEN_SECRET", "Access Token Secret"),
            ]),
            ("LinkedIn", [
                ("LINKEDIN_ACCESS_TOKEN", "Access Token"),
                ("LINKEDIN_PERSON_URN",   "Person URN"),
            ]),
            ("Meta (Facebook + Instagram)", [
                ("META_ACCESS_TOKEN",    "Page Access Token"),
                ("FACEBOOK_PAGE_ID",     "Facebook Page ID"),
                ("INSTAGRAM_ACCOUNT_ID", "Instagram Account ID"),
            ]),
            ("Reddit", [
                ("REDDIT_CLIENT_ID",     "Client ID"),
                ("REDDIT_CLIENT_SECRET", "Client Secret"),
                ("REDDIT_USERNAME",      "Username"),
                ("REDDIT_PASSWORD",      "Password"),
                ("REDDIT_SUBREDDITS",    "Subreddits (comma-separated)"),
            ]),
            ("Pinterest", [
                ("PINTEREST_ACCESS_TOKEN", "Access Token"),
                ("PINTEREST_BOARD_ID",     "Board ID"),
            ]),
            ("Telegram", [
                ("TELEGRAM_BOT_TOKEN",  "Bot Token"),
                ("TELEGRAM_CHANNEL_ID", "Channel ID (@name or -100...)"),
            ]),
        ]
        for group_name, fields in social_groups:
            _section_header(scroll, group_name)
            grp_card = _card(scroll)
            grp_card.pack(fill="x", padx=16, pady=8)
            for key, lbl in fields:
                _entry_row(grp_card, lbl, self._api_vars[key],
                           show="*" if any(s in key for s in ("SECRET", "TOKEN", "PASSWORD")) else "")

        # Save button
        save_row = ctk.CTkFrame(scroll, fg_color="transparent")
        save_row.pack(fill="x", padx=16, pady=(8, 20))
        self._save_status = _label(save_row, "", color=GREEN)
        self._save_status.pack(side="right", padx=12)
        ctk.CTkButton(
            save_row, text="💾  Save to .env", fg_color=GREEN, text_color="black",
            font=("Inter", 13, "bold"), height=40, width=160,
            command=self._save_settings,
        ).pack(side="right")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _log(self, msg: str, color: str = TEXT_SECONDARY):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self._log_box.configure(state="normal")
        self._log_box.insert("end", line)
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_progress(self, msg: str, color: str = TEXT_SECONDARY):
        self._progress_label.configure(text=msg, text_color=color)

    def _run_campaign_now(self):
        active = [p for p, v in self._platform_vars.items() if v.get()]
        if not active:
            self._log("No platforms selected.", RED)
            return
        self._log(f"Starting campaign on: {', '.join(active)}")
        self._set_progress("Running campaign...", YELLOW)
        threading.Thread(target=self._do_campaign, daemon=True).start()

    def _do_campaign(self):
        try:
            # Apply env vars from UI settings in memory
            self._apply_settings_to_env()
            active = [p for p, v in self._platform_vars.items() if v.get()]
            import importlib
            # Patch ACTIVE_PLATFORMS env var
            os.environ["ACTIVE_PLATFORMS"] = ",".join(active)

            # Lazy import so settings are applied first
            try:
                import ebook_bot.orchestrator as orch
                importlib.reload(orch)
                results = orch.run_campaign(
                    use_ai=self._use_ai_var.get(),
                    style_hint=self._style_var.get(),
                )
            except ImportError as ie:
                results = {"_summary": {"success": [], "failed": [], "link": ""}, "_error": str(ie)}

            summary = results.get("_summary", {})
            ok = summary.get("success", [])
            fail = summary.get("failed", [])

            now = datetime.now().strftime("%H:%M")
            for p in ok:
                self.after(0, lambda _p=p: self._platform_last_labels[_p].configure(text=now) if _p in self._platform_last_labels else None)
                self.after(0, lambda _p=p: self._platform_status_labels[_p].configure(text_color=GREEN) if _p in self._platform_status_labels else None)
            for p in fail:
                if p in self._platform_status_labels:
                    self.after(0, lambda _p=p: self._platform_status_labels[_p].configure(text_color=RED))

            self._post_log.append({"time": now, "success": ok, "failed": fail})
            total = len(self._post_log)
            rate = f"{round(len([r for r in self._post_log if r['success']]) / total * 100)}%" if total else "—"

            self.after(0, self._stat_tiles["total_posts"].configure, {"text": str(sum(len(r["success"]) for r in self._post_log))})
            self.after(0, self._stat_tiles["success_rate"].configure, {"text": rate})
            self.after(0, self._stat_tiles["last_run"].configure, {"text": now})

            msg = f"Done — posted to {ok}" if ok else "Campaign finished with no successful posts."
            self.after(0, self._log, msg, GREEN if ok else RED)
            self.after(0, self._set_progress, "Idle" if ok else "Errors — check log", GREEN if ok else RED)

        except Exception as e:
            self.after(0, self._log, f"Campaign error: {e}", RED)
            self.after(0, self._set_progress, f"Error: {e}", RED)

    def _toggle_scheduler(self):
        if self._scheduler_running:
            self._scheduler_running = False
            self._sched_btn.configure(text="⏰  Start Scheduler", fg_color=GREEN, text_color="black")
            self._sched_btn2.configure(text="⏰  Start Scheduler", fg_color=GREEN, text_color="black")
            self._stat_tiles["scheduler"].configure(text="OFF", text_color=RED)
            self._log("Scheduler stopped.")
        else:
            self._scheduler_running = True
            self._sched_btn.configure(text="⏹  Stop Scheduler", fg_color=RED, text_color=TEXT_PRIMARY)
            self._sched_btn2.configure(text="⏹  Stop Scheduler", fg_color=RED, text_color=TEXT_PRIMARY)
            self._stat_tiles["scheduler"].configure(text="ON", text_color=GREEN)
            self._log(f"Scheduler started — interval: {self._interval_var.get()}h")
            threading.Thread(target=self._scheduler_loop, daemon=True).start()

    def _scheduler_loop(self):
        import time
        interval_s = self._interval_var.get() * 3600
        next_run = time.time()
        while self._scheduler_running:
            if time.time() >= next_run:
                self.after(0, self._log, "Scheduled campaign firing...")
                self._do_campaign()
                next_run = time.time() + interval_s
                self.after(0, self._log, f"Next run in {self._interval_var.get()}h")
            time.sleep(30)

    def _generate_all_content(self):
        active = [p for p, v in self._platform_vars.items() if v.get()]
        self._log(f"Generating content for: {', '.join(active)}")
        threading.Thread(target=self._do_generate_all, args=(active,), daemon=True).start()

    def _do_generate_all(self, platforms: list[str]):
        self._apply_settings_to_env()
        for p in platforms:
            self.after(0, self._log, f"Generating {p}...")
            try:
                from ebook_bot.content import ai_writer, templates
                from ebook_bot import config as ecfg
                import importlib; importlib.reload(ecfg)
                if self._use_ai_var.get() and os.getenv("ANTHROPIC_API_KEY"):
                    text = ai_writer.generate_post(p, "(link)", style_hint=self._style_var.get())
                else:
                    style = "short" if p in ("twitter", "instagram", "telegram") else "medium"
                    text = templates.render_template(templates.pick_template(style), ecfg.EBOOK, "(link)")
                self._generated[p] = text
                tb = self._content_textboxes.get(p)
                if tb:
                    self.after(0, lambda _tb=tb, _t=text: (
                        _tb.delete("1.0", "end"),
                        _tb.insert("1.0", _t),
                    ))
            except Exception as e:
                self.after(0, self._log, f"{p} content error: {e}", RED)
        self.after(0, self._log, "Content generation complete.", GREEN)

    def _generate_one(self, platform: str):
        self._log(f"Generating {platform} content...")
        threading.Thread(target=self._do_generate_all, args=([platform],), daemon=True).start()

    def _post_one(self, platform: str):
        tb = self._content_textboxes.get(platform)
        if not tb:
            return
        text = tb.get("1.0", "end").strip()
        if not text:
            self._log(f"No content for {platform}", RED)
            return
        self._log(f"Posting to {platform}...")
        threading.Thread(target=self._do_post_one, args=(platform, text), daemon=True).start()

    def _do_post_one(self, platform: str, text: str):
        self._apply_settings_to_env()
        try:
            from ebook_bot.orchestrator import _get_best_link
            link = _get_best_link()
            text = text.replace("(link)", link)

            from ebook_bot.platforms import (twitter, linkedin, facebook,
                                              instagram, reddit, pinterest,
                                              telegram_channel)
            handlers = {
                "twitter":   lambda t: twitter.post(t),
                "linkedin":  lambda t: linkedin.post(t),
                "facebook":  lambda t: facebook.post(t),
                "instagram": lambda t: instagram.post(t, image_url=os.getenv("EBOOK_COVER_IMAGE_URL", "")),
                "reddit":    lambda t: reddit.post(t, link=link),
                "pinterest": lambda t: pinterest.post(t, link=link),
                "telegram":  lambda t: telegram_channel.post(t),
            }
            result = handlers[platform](text)
            if result:
                self.after(0, self._log, f"Posted to {platform}!", GREEN)
                if platform in self._platform_status_labels:
                    self.after(0, self._platform_status_labels[platform].configure, {"text_color": GREEN})
            else:
                self.after(0, self._log, f"{platform} post failed — check credentials", RED)
        except Exception as e:
            self.after(0, self._log, f"{platform} post error: {e}", RED)

    def _post_all_generated(self):
        for p, text in list(self._generated.items()):
            if text and self._platform_vars.get(p, ctk.BooleanVar()).get():
                threading.Thread(target=self._do_post_one, args=(p, text), daemon=True).start()

    def _generate_emails(self, count: int):
        self._log(f"Generating {count}-email sequence...")
        threading.Thread(target=self._do_generate_emails, args=(count,), daemon=True).start()

    def _do_generate_emails(self, count: int):
        self._apply_settings_to_env()
        try:
            from ebook_bot.content.ai_writer import generate_email_sequence
            from ebook_bot.orchestrator import _get_best_link
            link = _get_best_link() or "(your link)"
            emails = generate_email_sequence(link, num_emails=count)

            for i, (card, subj_lbl, tb) in enumerate(self._email_frames):
                if i < len(emails):
                    email = emails[i]
                    self.after(0, card.grid)
                    self.after(0, subj_lbl.configure, {"text": email.get("subject", "")})
                    body = email.get("body", "")
                    self.after(0, lambda _tb=tb, _b=body: (_tb.delete("1.0", "end"), _tb.insert("1.0", _b)))
                else:
                    self.after(0, card.grid_remove)

            self.after(0, self._log, f"Generated {len(emails)} emails.", GREEN)
        except Exception as e:
            self.after(0, self._log, f"Email generation error: {e}", RED)

    def _refresh_sales(self):
        self._log("Fetching sales data...")
        threading.Thread(target=self._do_refresh_sales, daemon=True).start()

    def _do_refresh_sales(self):
        self._apply_settings_to_env()
        try:
            from ebook_bot.orchestrator import get_sales_report
            report = get_sales_report()

            total_rev = 0.0
            total_count = 0
            active_platforms = 0

            for platform, data in report.items():
                tb = self._sales_boxes.get(platform)
                if not tb:
                    continue
                if isinstance(data, dict) and "error" in data:
                    lines = f"Error: {data['error']}"
                elif isinstance(data, list) and data:
                    active_platforms += 1
                    lines_parts = []
                    for item in data[:20]:
                        if isinstance(item, dict):
                            amt = item.get("amount", item.get("price", 0))
                            try:
                                total_rev += float(str(amt).replace("$", ""))
                                total_count += 1
                            except Exception:
                                pass
                            lines_parts.append(json.dumps(item, default=str))
                    lines = "\n".join(lines_parts) or "(no data)"
                else:
                    lines = "(no data or not configured)"

                self.after(0, lambda _tb=tb, _l=lines: (
                    _tb.configure(state="normal"),
                    _tb.delete("1.0", "end"),
                    _tb.insert("1.0", _l),
                    _tb.configure(state="disabled"),
                ))

            self.after(0, self._sales_tiles["total_revenue"].configure, {"text": f"${total_rev:,.2f}"})
            self.after(0, self._sales_tiles["total_sales"].configure,   {"text": str(total_count)})
            self.after(0, self._sales_tiles["platforms"].configure,     {"text": str(active_platforms)})
            self.after(0, self._log, "Sales data refreshed.", GREEN)
        except Exception as e:
            self.after(0, self._log, f"Sales refresh error: {e}", RED)

    def _apply_settings_to_env(self):
        """Push current UI values into os.environ so the bot modules pick them up."""
        for key, var in {**self._ebook_vars, **self._api_vars}.items():
            val = var.get()
            if val:
                os.environ[key] = val

    def _save_settings(self):
        """Write all settings to ebook_bot/.env file."""
        env_path = Path(__file__).parent.parent.parent / "ebook_bot" / ".env"
        lines = []
        self._apply_settings_to_env()

        all_vars = {
            **{k: v.get() for k, v in self._ebook_vars.items()},
            **{k: v.get() for k, v in self._api_vars.items()},
            "POST_INTERVAL_HOURS": str(self._interval_var.get()),
            "ACTIVE_PLATFORMS": ",".join(p for p, v in self._platform_vars.items() if v.get()) or "all",
        }
        for k, v in all_vars.items():
            lines.append(f'{k}="{v}"' if " " in v else f"{k}={v}")

        try:
            env_path.write_text("\n".join(lines) + "\n")
            self._save_status.configure(text="Saved!", text_color=GREEN)
            self.after(3000, lambda: self._save_status.configure(text=""))
            self._log(f"Settings saved to {env_path}", GREEN)
        except Exception as e:
            self._save_status.configure(text=f"Error: {e}", text_color=RED)
            self._log(f"Save error: {e}", RED)
