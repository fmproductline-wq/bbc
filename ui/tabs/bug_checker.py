"""Bug Checker Agent tab — run checks, view results, configure auto-scan."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox


class BugCheckerTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1, minsize=260)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ── Left: controls ─────────────────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(PAD, 4), pady=PAD)

        ctrl = Card(left, title="Bug Checker Agent")
        ctrl.pack(fill="x")

        pad = ctk.CTkFrame(ctrl, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkLabel(pad, text="Runs automated health checks on:", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, anchor="w", wraplength=220, justify="left").pack(fill="x", pady=(0, 8))

        checks = [
            "Config & API keys",
            "Hyperliquid connectivity",
            "Orphaned positions",
            "Stop-loss breaches",
            "Runaway loss detection",
            "Stale signals",
            "Duplicate positions",
            "Prediction market APIs",
        ]
        for c in checks:
            row = ctk.CTkFrame(pad, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text="•", font=FONT_SMALL, text_color=ACCENT, width=12).pack(side="left")
            ctk.CTkLabel(row, text=c, font=FONT_SMALL, text_color=TEXT_PRIMARY, anchor="w").pack(side="left")

        ctk.CTkButton(pad, text="🔍  Run Check (report only)", fg_color=BG_INPUT,
                      text_color=ACCENT, hover_color=BORDER, font=FONT_BODY,
                      command=lambda: self._run(remediate=False)).pack(fill="x", pady=(16, 4))

        ctk.CTkButton(pad, text="🔧  Run Check + Auto-Fix", fg_color=RED,
                      text_color="white", font=("Inter", 13, "bold"),
                      command=lambda: self._run(remediate=True)).pack(fill="x", pady=4)

        # Auto-scan interval
        auto_card = Card(left, title="Auto-Scan Schedule")
        auto_card.pack(fill="x", pady=(12, 0))

        apad = ctk.CTkFrame(auto_card, fg_color="transparent")
        apad.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkLabel(apad, text="Interval (minutes)", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.interval_e = ctk.CTkEntry(apad, fg_color=BG_INPUT, border_color=BORDER,
                                        text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.interval_e.insert(0, "30")
        self.interval_e.pack(fill="x", pady=(2, 8))

        self.auto_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(apad, text="Enable auto-scan", variable=self.auto_var,
                      progress_color=GREEN, button_color=ACCENT,
                      text_color=TEXT_PRIMARY, font=FONT_SMALL,
                      command=self._toggle_auto).pack(anchor="w")

        self._auto_after_id = None

        # Summary stats
        stats_card = Card(left, title="Last Check Summary")
        stats_card.pack(fill="x", pady=(12, 0))

        sp = ctk.CTkFrame(stats_card, fg_color="transparent")
        sp.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.stat_critical = ctk.CTkLabel(sp, text="Critical:  —", font=FONT_BODY,
                                           text_color=RED, anchor="w")
        self.stat_critical.pack(fill="x")
        self.stat_warning  = ctk.CTkLabel(sp, text="Warnings: —", font=FONT_BODY,
                                           text_color=YELLOW, anchor="w")
        self.stat_warning.pack(fill="x")
        self.stat_info     = ctk.CTkLabel(sp, text="Info:     —", font=FONT_BODY,
                                           text_color=ACCENT, anchor="w")
        self.stat_info.pack(fill="x")

        # ── Right: results log ─────────────────────────────────────────────────
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, PAD), pady=PAD)
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        log_card = Card(right, title="Check Results")
        log_card.grid(row=0, column=0, sticky="nsew")
        log_card.rowconfigure(0, weight=1)
        log_card.columnconfigure(0, weight=1)

        self.result_box = LogBox(log_card)
        self.result_box.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))

        btn_row = ctk.CTkFrame(log_card, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, PAD))
        ctk.CTkButton(btn_row, text="Clear", width=80, fg_color=BG_INPUT,
                      text_color=TEXT_SECONDARY, hover_color=BORDER,
                      command=self.result_box.clear).pack(side="right")

    def _run(self, remediate: bool):
        self.result_box.clear()
        self.result_box.append("Starting bug check…", "INFO")

        def _do():
            try:
                from agents.bug_checker import run_bug_check
                result = run_bug_check(auto_remediate=remediate)

                crit = sum(1 for r in result.reports if r.severity == "CRITICAL")
                warn = sum(1 for r in result.reports if r.severity == "WARNING")
                info = sum(1 for r in result.reports if r.severity == "INFO")

                self.after(0, self.stat_critical.configure, {"text": f"Critical:  {crit}"})
                self.after(0, self.stat_warning.configure,  {"text": f"Warnings: {warn}"})
                self.after(0, self.stat_info.configure,     {"text": f"Info:     {info}"})

                for r in result.reports:
                    level = {"CRITICAL": "ERROR", "WARNING": "WARNING", "INFO": "INFO"}.get(r.severity, "DEFAULT")
                    self.after(0, self.result_box.append,
                               f"[{r.severity}] {r.category}: {r.message}", level)
                    if r.action_taken:
                        self.after(0, self.result_box.append,
                                   f"  → {r.action_taken}", "SIGNAL")

                if not result.reports:
                    self.after(0, self.result_box.append, "✓ All checks passed — no issues found.", "SUCCESS")
                else:
                    status = "CRITICAL issues found!" if crit else f"{warn} warning(s)"
                    lvl = "ERROR" if crit else "WARNING" if warn else "SUCCESS"
                    self.after(0, self.result_box.append, f"\nSummary: {status}", lvl)

            except Exception as e:
                self.after(0, self.result_box.append, f"Bug check error: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    def _toggle_auto(self):
        if self.auto_var.get():
            self._schedule_auto()
        elif self._auto_after_id:
            self.after_cancel(self._auto_after_id)
            self._auto_after_id = None

    def _schedule_auto(self):
        try:
            mins = max(1, int(self.interval_e.get()))
        except ValueError:
            mins = 30
        self._run(remediate=False)
        self._auto_after_id = self.after(mins * 60 * 1000, self._schedule_auto)
