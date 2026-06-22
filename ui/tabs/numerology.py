"""
Numerology & Astrology Tab
==========================
Provides:
  • Personal reading (numerology + natal chart + astrocartography)
  • Compatibility reading (two people or brands / companies)
  • Astrocartography world map with planetary lines
  • AI-powered interpretation via Claude
"""
from __future__ import annotations

import os
import math
import threading
from datetime import date, datetime
from typing import Optional

import customtkinter as ctk

from ui.theme import (
    BG_DARK, BG_CARD, BG_INPUT, BORDER, ACCENT, PURPLE, GREEN, RED,
    YELLOW, BLUE, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_TITLE, FONT_HEADER, FONT_BODY, FONT_SMALL, FONT_MONO, PAD,
)
from ui.components.card import Card
from ui.components.log_box import LogBox


# Planet colour palette for astrocartography lines
PLANET_COLORS = {
    "Sun":     "#FFD700",
    "Moon":    "#C0C0C0",
    "Mercury": "#B0C4DE",
    "Venus":   "#90EE90",
    "Mars":    "#FF6347",
    "Jupiter": "#6A5ACD",
    "Saturn":  "#D2B48C",
    "Uranus":  "#00CED1",
    "Neptune": "#1E90FF",
    "Pluto":   "#BC8F8F",
}

# Very simplified world outline (longitude, latitude pairs for major coastlines)
# Encoded as a list of polylines — rough continental shapes for the map background
_CONTINENTS = [
    # North America (west coast + east coast outline)
    [(-140,60),(-140,55),(-135,50),(-125,48),(-120,35),(-115,30),(-110,23),
     (-90,16),(-83,10),(-77,8),(-75,10),(-80,25),(-82,30),(-80,35),(-75,40),
     (-70,42),(-67,47),(-60,47),(-65,44),(-66,45),(-60,47)],
    # Europe
    [(-10,35),(-5,36),(5,43),(8,44),(14,44),(18,40),(24,38),(28,37),(36,37),
     (28,41),(27,43),(30,46),(26,48),(18,50),(14,52),(10,55),(5,57),(0,58),
     (-5,58),(-10,55),(-10,35)],
    # Africa
    [(-18,14),(-10,5),(-5,4),(5,4),(10,3),(15,4),(40,10),(42,12),(44,12),
     (50,12),(52,14),(44,15),(38,20),(38,25),(34,30),(32,32),(30,30),(28,20),
     (20,15),(15,10),(10,5),(5,4),(0,5),(-5,5),(-10,6),(-18,14)],
    # South America
    [(-80,10),(-76,9),(-75,6),(-75,0),(-80,-5),(-78,-10),(-75,-15),(-70,-20),
     (-70,-30),(-68,-35),(-72,-42),(-75,-50),(-72,-55),(-68,-54),(-65,-54),
     (-58,-52),(-52,-34),(-48,-28),(-44,-23),(-38,-12),(-36,-5),(-35,0),
     (-42,2),(-50,2),(-62,4),(-72,10),(-80,10)],
    # Asia (rough)
    [(36,37),(40,38),(48,38),(55,24),(60,22),(65,25),(70,23),(78,8),(80,10),
     (88,22),(95,22),(100,5),(104,1),(108,3),(115,5),(120,15),(125,25),(130,32),
     (135,35),(140,40),(145,42),(135,45),(130,48),(125,50),(120,52),(130,55),
     (140,60),(150,60),(150,50),(140,45),(135,42),(130,35),(125,30),(120,25),
     (115,20),(110,12),(105,5),(100,2),(95,5),(90,22),(80,25),(65,38),(55,38),
     (48,38),(40,38),(36,37)],
    # Australia
    [(114,-22),(115,-28),(118,-32),(122,-34),(130,-33),(136,-35),(140,-38),
     (148,-38),(152,-30),(152,-24),(148,-20),(142,-14),(136,-12),(132,-12),
     (128,-16),(122,-20),(118,-22),(114,-22)],
]


class NumerologyTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._reading_data: dict = {}
        self._compat_data:  dict = {}
        self._build()

    # ── Main layout ──────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Notebook-style sub-tabs
        self.notebook = ctk.CTkTabview(
            self,
            fg_color=BG_DARK,
            segmented_button_fg_color=BG_CARD,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=PURPLE,
            segmented_button_unselected_color=BG_CARD,
            segmented_button_unselected_hover_color=BG_INPUT,
            text_color=TEXT_PRIMARY,
            border_width=1,
            border_color=BORDER,
        )
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=PAD)

        self.notebook.add("Personal Reading")
        self.notebook.add("Compatibility")
        self.notebook.add("Astrocartography")

        self._build_personal_tab(self.notebook.tab("Personal Reading"))
        self._build_compat_tab(self.notebook.tab("Compatibility"))
        self._build_astro_tab(self.notebook.tab("Astrocartography"))

    # ════════════════════════════════════════════════════════════════════════
    # Personal Reading tab
    # ════════════════════════════════════════════════════════════════════════

    def _build_personal_tab(self, parent):
        parent.columnconfigure(0, weight=1, minsize=300)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        # ── Left: input form ─────────────────────────────────────────────────
        left = ctk.CTkScrollableFrame(parent, fg_color="transparent", scrollbar_button_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=0)
        left.columnconfigure(0, weight=1)

        input_card = Card(left, title="Your Information")
        input_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        form = ctk.CTkFrame(input_card, fg_color="transparent")
        form.pack(fill="x", padx=PAD, pady=(0, PAD))

        def lbl(parent, t):
            return ctk.CTkLabel(parent, text=t, font=FONT_SMALL,
                                text_color=TEXT_SECONDARY, anchor="w")

        def entry(parent, placeholder=""):
            e = ctk.CTkEntry(parent, fg_color=BG_INPUT, border_color=BORDER,
                             text_color=TEXT_PRIMARY, font=FONT_BODY,
                             placeholder_text=placeholder,
                             placeholder_text_color=TEXT_MUTED)
            return e

        lbl(form, "Full Birth Name").pack(fill="x", pady=(4, 2))
        self.name_entry = entry(form, "e.g. Jane Marie Smith")
        self.name_entry.pack(fill="x")

        lbl(form, "Birth Date  (YYYY-MM-DD)").pack(fill="x", pady=(8, 2))
        self.bdate_entry = entry(form, "e.g. 1990-06-15")
        self.bdate_entry.pack(fill="x")

        lbl(form, "Birth Time  (HH:MM, 24h UTC)").pack(fill="x", pady=(8, 2))
        self.btime_entry = entry(form, "e.g. 14:30  (leave blank = noon)")
        self.btime_entry.pack(fill="x")

        lbl(form, "Birth Latitude  (decimal °)").pack(fill="x", pady=(8, 2))
        self.blat_entry = entry(form, "e.g. 40.71  (N=+, S=−)")
        self.blat_entry.pack(fill="x")

        lbl(form, "Birth Longitude (decimal °)").pack(fill="x", pady=(8, 2))
        self.blon_entry = entry(form, "e.g. -74.01  (E=+, W=−)")
        self.blon_entry.pack(fill="x")

        lbl(form, "Anthropic API Key").pack(fill="x", pady=(8, 2))
        self.api_key_entry = entry(form, "sk-ant-...  (for AI reading)")
        self.api_key_entry.configure(show="*")
        self.api_key_entry.pack(fill="x")
        # Pre-fill from env
        env_key = os.getenv("ANTHROPIC_API_KEY", "")
        if env_key:
            self.api_key_entry.insert(0, env_key)

        self.run_btn = ctk.CTkButton(
            form, text="✦  Generate Full Reading",
            fg_color=ACCENT, text_color=BG_DARK,
            font=("Inter", 13, "bold"),
            command=self._run_personal_reading,
        )
        self.run_btn.pack(fill="x", pady=(14, 4))

        self.status_lbl = ctk.CTkLabel(form, text="", font=FONT_SMALL,
                                        text_color=TEXT_MUTED)
        self.status_lbl.pack(anchor="w")

        # ── Numbers summary card ──────────────────────────────────────────────
        nums_card = Card(left, title="Birthday Numbers")
        nums_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.nums_frame = ctk.CTkFrame(nums_card, fg_color="transparent")
        self.nums_frame.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._nums_labels: dict[str, ctk.CTkLabel] = {}

        fields = [
            ("julian_day_number", "Julian Day Number"),
            ("march21_day",       "March-21 Day #"),
            ("march21_reduced",   "↳ Reduced"),
            ("jan1_day",          "Jan-1 Day #"),
            ("jan1_reduced",      "↳ Reduced"),
            ("life_path",         "Life Path"),
            ("expression",        "Expression"),
            ("soul_urge",         "Soul Urge"),
            ("personality",       "Personality"),
            ("birthday_num",      "Birthday #"),
            ("personal_year",     "Personal Year"),
        ]
        for key, label_text in fields:
            row_f = ctk.CTkFrame(self.nums_frame, fg_color="transparent")
            row_f.pack(fill="x", pady=1)
            ctk.CTkLabel(row_f, text=label_text + ":", font=FONT_SMALL,
                         text_color=TEXT_SECONDARY, width=130, anchor="w").pack(side="left")
            val_lbl = ctk.CTkLabel(row_f, text="—", font=FONT_MONO,
                                   text_color=ACCENT, anchor="w")
            val_lbl.pack(side="left", padx=4)
            self._nums_labels[key] = val_lbl

        # ── Right: AI reading + chart ─────────────────────────────────────────
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=0)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=2)

        chart_card = Card(right, title="Natal Chart")
        chart_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.chart_box = LogBox(chart_card, height=220)
        self.chart_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        ai_card = Card(right, title="AI Reading")
        ai_card.grid(row=1, column=0, sticky="nsew")
        self.ai_box = LogBox(ai_card, height=400)
        self.ai_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    def _run_personal_reading(self):
        name       = self.name_entry.get().strip()
        bdate_str  = self.bdate_entry.get().strip()
        btime      = self.btime_entry.get().strip() or "12:00"
        blat_str   = self.blat_entry.get().strip() or "0"
        blon_str   = self.blon_entry.get().strip() or "0"
        api_key    = self.api_key_entry.get().strip() or None

        if not name or not bdate_str:
            self.status_lbl.configure(text="Name and birth date are required.", text_color=RED)
            return
        try:
            bdate = date.fromisoformat(bdate_str)
        except ValueError:
            self.status_lbl.configure(text="Invalid date — use YYYY-MM-DD", text_color=RED)
            return
        try:
            blat = float(blat_str)
            blon = float(blon_str)
        except ValueError:
            self.status_lbl.configure(text="Invalid lat/lon — enter decimal degrees", text_color=RED)
            return

        self.run_btn.configure(state="disabled")
        self.status_lbl.configure(text="Calculating…", text_color=TEXT_MUTED)
        self.ai_box.clear()
        self.chart_box.clear()
        self.ai_box.append("Computing natal chart & numerology…", "INFO")

        def _work():
            from agents.numerology_agent import full_reading
            data = full_reading(name, bdate, btime, blat, blon, api_key=api_key)
            self.after(0, self._display_personal_reading, data, name, bdate)

        threading.Thread(target=_work, daemon=True).start()

    def _display_personal_reading(self, data: dict, name: str, bdate: date):
        self._reading_data = data
        profile = data.get("profile", {})
        natal   = data.get("natal_chart", {})
        cities  = data.get("city_lines", {})
        ai_text = data.get("ai_reading", "")

        # Update numbers panel
        for key, lbl in self._nums_labels.items():
            val = profile.get(key, "—")
            lbl.configure(text=str(val))

        # Natal chart display
        self.chart_box.clear()
        if "error" in natal:
            self.chart_box.append(natal["error"], "ERROR")
        elif "planets" in natal:
            self.chart_box.append(
                f"  ASCENDANT  {natal['ascendant']['sign']:13} "
                f"{natal['ascendant']['degree']:.1f}°", "SUCCESS"
            )
            self.chart_box.append(
                f"  MIDHEAVEN  {natal['midheaven']['sign']:13} "
                f"{natal['midheaven']['degree']:.1f}°", "INFO"
            )
            self.chart_box.append("─" * 40, "DEFAULT")
            for pname, pdata in natal["planets"].items():
                if "sign" in pdata:
                    sym = pdata.get("symbol", " ")
                    self.chart_box.append(
                        f"  {sym} {pname:9} {pdata['sign']:13} {pdata['degree']:.1f}°",
                        "DEFAULT",
                    )
            if cities:
                self.chart_box.append("─" * 40, "DEFAULT")
                self.chart_box.append("ASTROCARTOGRAPHY CITY LINES:", "INFO")
                for planet, city_list in cities.items():
                    if city_list:
                        self.chart_box.append(
                            f"  {planet}: {', '.join(city_list[:4])}", "DEFAULT"
                        )

        # AI reading
        self.ai_box.clear()
        if ai_text:
            for line in ai_text.split("\n"):
                level = "SUCCESS" if line.startswith("#") else "DEFAULT"
                self.ai_box.append(line, level)

        self.run_btn.configure(state="normal")
        self.status_lbl.configure(text="Reading complete.", text_color=GREEN)

        # Also populate Astrocartography tab if it exists
        self._update_astro_tab(data, name, bdate)

    # ════════════════════════════════════════════════════════════════════════
    # Compatibility tab
    # ════════════════════════════════════════════════════════════════════════

    def _build_compat_tab(self, parent):
        parent.columnconfigure(0, weight=1, minsize=280)
        parent.columnconfigure(1, weight=2)
        parent.rowconfigure(0, weight=1)

        # ── Left: inputs ──────────────────────────────────────────────────────
        left = ctk.CTkScrollableFrame(parent, fg_color="transparent", scrollbar_button_color=BORDER)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.columnconfigure(0, weight=1)

        def lbl(parent, t):
            return ctk.CTkLabel(parent, text=t, font=FONT_SMALL,
                                text_color=TEXT_SECONDARY, anchor="w")

        def entry(parent, placeholder=""):
            e = ctk.CTkEntry(parent, fg_color=BG_INPUT, border_color=BORDER,
                             text_color=TEXT_PRIMARY, font=FONT_BODY,
                             placeholder_text=placeholder,
                             placeholder_text_color=TEXT_MUTED)
            return e

        # Person / Entity 1
        card1 = Card(left, title="Person / Brand 1")
        card1.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        f1 = ctk.CTkFrame(card1, fg_color="transparent")
        f1.pack(fill="x", padx=PAD, pady=(0, PAD))

        lbl(f1, "Full Name or Brand Name").pack(fill="x", pady=(4, 2))
        self.c_name1 = entry(f1, "e.g. Apple Inc."); self.c_name1.pack(fill="x")
        lbl(f1, "Birthdate / Founded  (YYYY-MM-DD)").pack(fill="x", pady=(8, 2))
        self.c_date1 = entry(f1, "e.g. 1976-04-01"); self.c_date1.pack(fill="x")

        # Person / Entity 2
        card2 = Card(left, title="Person / Brand 2")
        card2.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        f2 = ctk.CTkFrame(card2, fg_color="transparent")
        f2.pack(fill="x", padx=PAD, pady=(0, PAD))

        lbl(f2, "Full Name or Brand Name").pack(fill="x", pady=(4, 2))
        self.c_name2 = entry(f2, "e.g. Google LLC"); self.c_name2.pack(fill="x")
        lbl(f2, "Birthdate / Founded  (YYYY-MM-DD)").pack(fill="x", pady=(8, 2))
        self.c_date2 = entry(f2, "e.g. 1998-09-04"); self.c_date2.pack(fill="x")

        # Entity type selector
        type_card = Card(left, title="Comparison Type")
        type_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        type_frame = ctk.CTkFrame(type_card, fg_color="transparent")
        type_frame.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.entity_type = ctk.CTkSegmentedButton(
            type_frame,
            values=["people", "brands / companies", "person & brand"],
            fg_color=BG_INPUT,
            selected_color=ACCENT,
            selected_hover_color=PURPLE,
            unselected_color=BG_INPUT,
            unselected_hover_color=BG_CARD,
            text_color=TEXT_PRIMARY,
            font=FONT_SMALL,
        )
        self.entity_type.set("people")
        self.entity_type.pack(fill="x", pady=4)

        # API key (shared with personal tab — auto-synced)
        api_card = Card(left, title="API Key")
        api_card.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        apif = ctk.CTkFrame(api_card, fg_color="transparent")
        apif.pack(fill="x", padx=PAD, pady=(0, PAD))
        lbl(apif, "Anthropic API Key").pack(fill="x", pady=(4, 2))
        self.c_api_key = ctk.CTkEntry(apif, fg_color=BG_INPUT, border_color=BORDER,
                                       text_color=TEXT_PRIMARY, font=FONT_BODY, show="*",
                                       placeholder_text="sk-ant-...",
                                       placeholder_text_color=TEXT_MUTED)
        self.c_api_key.pack(fill="x")
        env_key = os.getenv("ANTHROPIC_API_KEY", "")
        if env_key:
            self.c_api_key.insert(0, env_key)

        self.compat_btn = ctk.CTkButton(
            left, text="⚡ Calculate Compatibility",
            fg_color=PURPLE, text_color=WHITE,
            font=("Inter", 13, "bold"),
            command=self._run_compat,
        )
        self.compat_btn.grid(row=4, column=0, sticky="ew", pady=(0, 4))

        self.compat_status = ctk.CTkLabel(left, text="", font=FONT_SMALL,
                                           text_color=TEXT_MUTED)
        self.compat_status.grid(row=5, column=0, sticky="w")

        # ── Right: results ────────────────────────────────────────────────────
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        # Score banner
        self.score_card = Card(right, title="Compatibility Score")
        self.score_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        score_inner = ctk.CTkFrame(self.score_card, fg_color="transparent")
        score_inner.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.score_lbl = ctk.CTkLabel(score_inner, text="—  /  100",
                                       font=("Inter", 32, "bold"), text_color=ACCENT)
        self.score_lbl.pack(side="left", padx=(0, 12))
        self.score_summary = ctk.CTkLabel(score_inner, text="Enter names and dates above",
                                           font=FONT_BODY, text_color=TEXT_SECONDARY,
                                           wraplength=400, justify="left")
        self.score_summary.pack(side="left", fill="x", expand=True)

        ai_card = Card(right, title="AI Compatibility Reading")
        ai_card.grid(row=1, column=0, sticky="nsew")
        self.compat_box = LogBox(ai_card, height=500)
        self.compat_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    def _run_compat(self):
        n1 = self.c_name1.get().strip()
        n2 = self.c_name2.get().strip()
        d1s = self.c_date1.get().strip()
        d2s = self.c_date2.get().strip()
        api_key = self.c_api_key.get().strip() or None
        etype = self.entity_type.get()

        if not all([n1, n2, d1s, d2s]):
            self.compat_status.configure(text="All four fields required.", text_color=RED)
            return
        try:
            d1 = date.fromisoformat(d1s)
            d2 = date.fromisoformat(d2s)
        except ValueError:
            self.compat_status.configure(text="Invalid date — use YYYY-MM-DD", text_color=RED)
            return

        self.compat_btn.configure(state="disabled")
        self.compat_status.configure(text="Calculating…", text_color=TEXT_MUTED)
        self.compat_box.clear()
        self.compat_box.append("Running compatibility analysis…", "INFO")

        def _work():
            from agents.numerology_agent import compatibility_reading
            data = compatibility_reading(n1, d1, n2, d2, entity_type=etype, api_key=api_key)
            self.after(0, self._display_compat, data, n1, n2)

        threading.Thread(target=_work, daemon=True).start()

    def _display_compat(self, data: dict, n1: str, n2: str):
        self._compat_data = data
        score = data.get("score", 0)
        summary = data.get("summary", "")
        ai_text = data.get("ai_reading", "")
        p1 = data.get("numerology_1", {})
        p2 = data.get("numerology_2", {})

        color = GREEN if score >= 75 else YELLOW if score >= 55 else RED
        self.score_lbl.configure(text=f"{score}  /  100", text_color=color)
        self.score_summary.configure(text=summary)

        self.compat_box.clear()
        # Numbers comparison header
        self.compat_box.append(f"{'':>20}{n1[:16]:>18}  {n2[:16]}", "INFO")
        self.compat_box.append("─" * 56, "DEFAULT")
        for key, label in [
            ("julian_day_number", "Julian Day #"),
            ("march21_day",       "March-21 Day #"),
            ("march21_reduced",   "  ↳ Reduced"),
            ("jan1_day",          "Jan-1 Day #"),
            ("jan1_reduced",      "  ↳ Reduced"),
            ("life_path",         "Life Path"),
            ("expression",        "Expression"),
            ("soul_urge",         "Soul Urge"),
            ("personality",       "Personality"),
        ]:
            v1 = str(p1.get(key, "—"))
            v2 = str(p2.get(key, "—"))
            match = "✓" if v1 == v2 else " "
            self.compat_box.append(
                f"  {label:20} {v1:>8}  {v2:>8}   {match}", "DEFAULT"
            )
        self.compat_box.append("─" * 56, "DEFAULT")
        self.compat_box.append(f"  Compatibility Score:           {score}/100", "SUCCESS")
        self.compat_box.append("═" * 56, "DEFAULT")

        if ai_text:
            self.compat_box.append("", "DEFAULT")
            self.compat_box.append("AI READING", "INFO")
            self.compat_box.append("─" * 56, "DEFAULT")
            for line in ai_text.split("\n"):
                self.compat_box.append(line, "DEFAULT")

        self.compat_btn.configure(state="normal")
        self.compat_status.configure(text="Complete.", text_color=GREEN)

    # ════════════════════════════════════════════════════════════════════════
    # Astrocartography tab
    # ════════════════════════════════════════════════════════════════════════

    def _build_astro_tab(self, parent):
        parent.columnconfigure(0, weight=3)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        # Map canvas area
        map_card = Card(parent, title="Astrocartography World Map")
        map_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        map_card.columnconfigure(0, weight=1)
        map_card.rowconfigure(1, weight=1)

        # Legend
        legend_frame = ctk.CTkFrame(map_card, fg_color="transparent")
        legend_frame.pack(fill="x", padx=PAD, pady=(0, 4))
        for planet, color in list(PLANET_COLORS.items())[:5]:
            dot = ctk.CTkLabel(legend_frame, text=f"● {planet}",
                               font=FONT_SMALL, text_color=color)
            dot.pack(side="left", padx=6)
        legend_frame2 = ctk.CTkFrame(map_card, fg_color="transparent")
        legend_frame2.pack(fill="x", padx=PAD, pady=(0, 4))
        for planet, color in list(PLANET_COLORS.items())[5:]:
            dot = ctk.CTkLabel(legend_frame2, text=f"● {planet}",
                               font=FONT_SMALL, text_color=color)
            dot.pack(side="left", padx=6)

        line_legend = ctk.CTkFrame(map_card, fg_color="transparent")
        line_legend.pack(fill="x", padx=PAD, pady=(0, 6))
        for style, label in [("─── ", "MC (Midheaven)"), ("- - ", "IC (Nadir)"),
                               ("···  ", "AC (Rising)"),  ("— — ", "DC (Setting)")]:
            ctk.CTkLabel(line_legend, text=style + label, font=FONT_SMALL,
                         text_color=TEXT_SECONDARY).pack(side="left", padx=8)

        # Embed matplotlib figure
        self._map_canvas_widget = None
        self._map_figure = None
        map_container = ctk.CTkFrame(map_card, fg_color=BG_DARK, corner_radius=6)
        map_container.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))
        self._astro_map_container = map_container
        self._init_map()

        # Right panel: city lines + planet selector
        right = ctk.CTkScrollableFrame(parent, fg_color="transparent", scrollbar_button_color=BORDER)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right.columnconfigure(0, weight=1)

        ctrl_card = Card(right, title="Generate Map")
        ctrl_card.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctrl_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkLabel(ctrl_frame, text="Fill in Personal Reading tab and\nclick 'Generate Full Reading'.\nOr enter a date below:",
                     font=FONT_SMALL, text_color=TEXT_MUTED, justify="left").pack(anchor="w", pady=(4, 8))

        ctk.CTkLabel(ctrl_frame, text="Quick Date (YYYY-MM-DD):", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.astro_date_entry = ctk.CTkEntry(ctrl_frame, fg_color=BG_INPUT, border_color=BORDER,
                                              text_color=TEXT_PRIMARY, font=FONT_BODY,
                                              placeholder_text="e.g. 1990-06-15",
                                              placeholder_text_color=TEXT_MUTED)
        self.astro_date_entry.pack(fill="x")

        self.gen_map_btn = ctk.CTkButton(
            ctrl_frame, text="Generate Map",
            fg_color=BLUE, text_color=WHITE, font=("Inter", 12, "bold"),
            command=self._generate_quick_map,
        )
        self.gen_map_btn.pack(fill="x", pady=(8, 0))

        # Planet checkboxes
        planet_card = Card(right, title="Show Planets")
        planet_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        planet_frame = ctk.CTkFrame(planet_card, fg_color="transparent")
        planet_frame.pack(fill="x", padx=PAD, pady=(0, PAD))

        self._planet_vars: dict[str, ctk.BooleanVar] = {}
        for planet in PLANET_COLORS:
            var = ctk.BooleanVar(value=planet in ("Sun","Moon","Venus","Mars","Jupiter"))
            self._planet_vars[planet] = var
            cb = ctk.CTkCheckBox(planet_frame, text=planet, variable=var,
                                 font=FONT_SMALL, text_color=PLANET_COLORS[planet],
                                 fg_color=PLANET_COLORS[planet], border_color=BORDER,
                                 checkmark_color=BG_DARK,
                                 command=self._redraw_map)
            cb.pack(anchor="w", pady=1)

        # City lines report
        cities_card = Card(right, title="Power Cities")
        cities_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.cities_box = LogBox(cities_card, height=300)
        self.cities_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        self._astro_data: dict = {}

    def _init_map(self):
        """Create the matplotlib world map canvas."""
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.patches as mpatches

            fig = Figure(figsize=(10, 5), dpi=90, facecolor="#0A0A0F")
            ax  = fig.add_subplot(111)
            ax.set_facecolor("#0E1628")
            ax.set_xlim(-180, 180)
            ax.set_ylim(-90,  90)
            ax.set_xticks(range(-180, 181, 30))
            ax.set_yticks(range(-90,   91, 30))
            ax.tick_params(colors="#5A5A80", labelsize=7)
            ax.grid(True, color="#1A2040", linewidth=0.4)
            ax.spines[:].set_color("#2D2D5E")
            ax.set_xlabel("Longitude", color="#5A5A80", fontsize=8)
            ax.set_ylabel("Latitude",  color="#5A5A80", fontsize=8)

            # Draw simplified continents
            for poly in _CONTINENTS:
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                ax.fill(xs, ys, color="#1A3040", alpha=0.7, linewidth=0)
                ax.plot(xs, ys, color="#2D4060", linewidth=0.6)

            self._map_figure = fig
            self._map_ax = ax

            canvas = FigureCanvasTkAgg(fig, master=self._astro_map_container)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self._map_canvas_widget = canvas
        except Exception as e:
            ctk.CTkLabel(self._astro_map_container, text=f"Map unavailable: {e}",
                         font=FONT_SMALL, text_color=TEXT_MUTED).pack(expand=True)

    def _update_astro_tab(self, data: dict, name: str, bdate: date):
        """Called after personal reading — populates the Astrocartography tab."""
        astro  = data.get("astrocartography", {})
        cities = data.get("city_lines", {})
        if astro:
            self._astro_data = astro
            self._redraw_map()
            self.cities_box.clear()
            for planet, city_list in cities.items():
                if city_list:
                    self.cities_box.append(f"{planet}:", "INFO")
                    for c in city_list:
                        self.cities_box.append(f"  {c}", "DEFAULT")

    def _generate_quick_map(self):
        d_str = self.astro_date_entry.get().strip()
        if not d_str:
            return
        try:
            bdate = date.fromisoformat(d_str)
        except ValueError:
            return

        self.gen_map_btn.configure(state="disabled")

        def _work():
            from agents.numerology_agent import calculate_astrocartography, find_cities_on_lines
            astro  = calculate_astrocartography(bdate)
            cities = find_cities_on_lines(astro)
            self.after(0, self._finish_quick_map, astro, cities)

        threading.Thread(target=_work, daemon=True).start()

    def _finish_quick_map(self, astro: dict, cities: dict):
        self._astro_data = astro
        self._redraw_map()
        self.cities_box.clear()
        for planet, city_list in cities.items():
            if city_list:
                self.cities_box.append(f"{planet}:", "INFO")
                for c in city_list:
                    self.cities_box.append(f"  {c}", "DEFAULT")
        self.gen_map_btn.configure(state="normal")

    def _redraw_map(self):
        if not self._map_figure or not self._astro_data:
            return
        try:
            ax = self._map_ax
            # Remove existing astrocarto lines (keep base map)
            while len(ax.lines) > len(_CONTINENTS):
                ax.lines[-1].remove()
            # Also remove text labels added previously
            for txt in list(ax.texts):
                txt.remove()

            for planet, data in self._astro_data.items():
                if not self._planet_vars.get(planet, ctk.BooleanVar(value=False)).get():
                    continue
                color = PLANET_COLORS.get(planet, "#FFFFFF")
                mc  = data.get("mc_lon")
                ic  = data.get("ic_lon")
                ac  = data.get("ac_pts", [])
                dc  = data.get("dc_pts", [])

                if mc is not None:
                    ax.axvline(mc, color=color, linewidth=1.0, linestyle="-", alpha=0.8)
                if ic is not None:
                    ax.axvline(ic, color=color, linewidth=0.8, linestyle="--", alpha=0.6)

                if ac:
                    lats = [p[0] for p in ac]
                    lons = [p[1] for p in ac]
                    ax.plot(lons, lats, color=color, linewidth=0.8, linestyle=":", alpha=0.7)
                if dc:
                    lats = [p[0] for p in dc]
                    lons = [p[1] for p in dc]
                    ax.plot(lons, lats, color=color, linewidth=0.8, linestyle="-.", alpha=0.7)

            self._map_canvas_widget.draw()
        except Exception:
            pass
