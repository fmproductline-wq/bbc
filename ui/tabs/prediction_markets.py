"""Prediction Markets tab — Polymarket, Kalshi, Metaculus."""
from __future__ import annotations
import threading
import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox


class PredictionMarketsTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Platform tabs ─────────────────────────────────────────────────────
        self.platform_seg = ctk.CTkSegmentedButton(
            self,
            values=["Polymarket", "Kalshi", "Metaculus"],
            fg_color=BG_CARD,
            selected_color=PURPLE,
            text_color=TEXT_PRIMARY,
            font=FONT_BODY,
            command=self._switch_platform,
        )
        self.platform_seg.set("Polymarket")
        self.platform_seg.grid(row=0, column=0, columnspan=3, sticky="ew",
                               padx=PAD, pady=(PAD, 8))

        # ── Search ────────────────────────────────────────────────────────────
        search_card = Card(self, title="Search Markets")
        search_card.grid(row=1, column=0, sticky="nsew", padx=(PAD, 4), pady=(0, PAD))

        sf = ctk.CTkFrame(search_card, fg_color="transparent")
        sf.pack(fill="x", padx=PAD, pady=(0, 8))

        self.search_entry = ctk.CTkEntry(sf, placeholder_text="Search…",
                                          fg_color=BG_INPUT, border_color=BORDER,
                                          text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(sf, text="Search", width=80, fg_color=PURPLE, text_color="white",
                      command=self._search).pack(side="left", padx=(8, 0))

        self.results_box = LogBox(search_card, height=450)
        self.results_box.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

        # ── Order form ─────────────────────────────────────────────────────────
        order_card = Card(self, title="Place Bet")
        order_card.grid(row=1, column=1, sticky="nsew", padx=4, pady=(0, PAD))

        of = ctk.CTkFrame(order_card, fg_color="transparent")
        of.pack(fill="x", padx=PAD, pady=(0, PAD))

        def lbl(t): return ctk.CTkLabel(of, text=t, font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        def ent(placeholder=""):
            e = ctk.CTkEntry(of, placeholder_text=placeholder,
                             fg_color=BG_INPUT, border_color=BORDER,
                             text_color=TEXT_PRIMARY, font=FONT_BODY)
            return e

        lbl("Market ID / Ticker").pack(fill="x", pady=(4, 2))
        self.market_id_e = ent("token_id or ticker"); self.market_id_e.pack(fill="x")

        lbl("Side").pack(fill="x", pady=(8, 2))
        self.side_seg = ctk.CTkSegmentedButton(of, values=["YES", "NO"],
                                                fg_color=BG_INPUT,
                                                selected_color=GREEN,
                                                text_color=TEXT_PRIMARY)
        self.side_seg.set("YES")
        self.side_seg.pack(fill="x")

        lbl("Price / Probability (0–1 or cents)").pack(fill="x", pady=(8, 2))
        self.price_e = ent("0.55"); self.price_e.pack(fill="x")

        lbl("Size / Contracts").pack(fill="x", pady=(8, 2))
        self.size_e = ent("10"); self.size_e.pack(fill="x")

        # Kalshi-only fields
        self._kalshi_frame = ctk.CTkFrame(of, fg_color="transparent")
        lbl2 = ctk.CTkLabel(self._kalshi_frame, text="Action (buy/sell)",
                             font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        lbl2.pack(fill="x", pady=(8, 2))
        self.action_seg = ctk.CTkSegmentedButton(self._kalshi_frame, values=["buy", "sell"],
                                                  fg_color=BG_INPUT, selected_color=ACCENT,
                                                  text_color=TEXT_PRIMARY)
        self.action_seg.set("buy")
        self.action_seg.pack(fill="x")

        ctk.CTkButton(of, text="Place Bet →", fg_color=PURPLE, text_color="white",
                      font=("Inter", 13, "bold"),
                      command=self._place_bet).pack(fill="x", pady=16)

        # Probability helper
        prob_card = Card(of, title="Quick Prob Check")
        prob_card.pack(fill="x", pady=(0, 0))

        pf = ctk.CTkFrame(prob_card, fg_color="transparent")
        pf.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(pf, text="Our estimate (0–1)", font=FONT_SMALL, text_color=TEXT_SECONDARY).pack(fill="x")
        self.our_est_e = ctk.CTkEntry(pf, placeholder_text="0.65",
                                       fg_color=BG_INPUT, border_color=BORDER,
                                       text_color=TEXT_PRIMARY, font=FONT_BODY)
        self.our_est_e.pack(fill="x", pady=(2, 8))
        ctk.CTkButton(pf, text="Analyze Edge", fg_color=BG_INPUT,
                      text_color=PURPLE, hover_color=BORDER,
                      command=self._analyze_edge).pack(fill="x")

        # ── Bet log ────────────────────────────────────────────────────────────
        log_card = Card(self, title="Bet Log")
        log_card.grid(row=1, column=2, sticky="nsew", padx=(4, PAD), pady=(0, PAD))
        self.bet_log = LogBox(log_card, height=480)
        self.bet_log.pack(fill="both", expand=True, padx=PAD, pady=(0, PAD))

    def _switch_platform(self, platform: str):
        if platform == "Kalshi":
            self._kalshi_frame.pack(fill="x", after=self.size_e)
        else:
            self._kalshi_frame.pack_forget()

    def _search(self):
        query = self.search_entry.get().strip()
        platform = self.platform_seg.get()
        self.results_box.clear()
        self.results_box.append(f"Searching {platform}: '{query}'…", "INFO")

        def _do():
            try:
                if platform == "Polymarket":
                    from predictions import polymarket
                    markets = polymarket.search_markets(query, limit=8)
                    for m in markets:
                        self.after(0, self.results_box.append,
                                   f"{'─'*36}", "DEFAULT")
                        self.after(0, self.results_box.append,
                                   m.get("question", "?"), "SIGNAL")
                        self.after(0, self.results_box.append,
                                   f"  YES: {m.get('yes_price')}  NO: {m.get('no_price')}", "DEFAULT")
                        self.after(0, self.results_box.append,
                                   f"  ID:  {m.get('id')}", "DEFAULT")

                elif platform == "Kalshi":
                    from predictions import kalshi
                    markets = kalshi.search_markets(query, limit=8)
                    for m in markets:
                        self.after(0, self.results_box.append, f"{'─'*36}", "DEFAULT")
                        self.after(0, self.results_box.append, m.get("title", "?"), "SIGNAL")
                        self.after(0, self.results_box.append,
                                   f"  YES ask: {m.get('yes_ask')}¢  NO ask: {m.get('no_ask')}¢", "DEFAULT")
                        self.after(0, self.results_box.append,
                                   f"  Ticker: {m.get('ticker')}", "DEFAULT")

                elif platform == "Metaculus":
                    from predictions import metaculus
                    questions = metaculus.search_questions(query, limit=8)
                    for q in questions:
                        prob = q.get("community_prediction")
                        prob_str = f"{prob*100:.1f}%" if prob else "N/A"
                        self.after(0, self.results_box.append, f"{'─'*36}", "DEFAULT")
                        self.after(0, self.results_box.append, q.get("title", "?"), "SIGNAL")
                        self.after(0, self.results_box.append,
                                   f"  Community: {prob_str}  ID: {q.get('id')}", "DEFAULT")

                if not query:
                    self.after(0, self.results_box.append, "Enter a search term above", "WARNING")

            except Exception as e:
                self.after(0, self.results_box.append, f"Search failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    def _place_bet(self):
        platform = self.platform_seg.get()
        market_id = self.market_id_e.get().strip()
        side = self.side_seg.get()
        try:
            price = float(self.price_e.get())
            size  = float(self.size_e.get())
        except ValueError:
            self.bet_log.append("Invalid price or size", "ERROR"); return

        self.bet_log.append(f"Placing {platform} {side} bet…", "INFO")

        def _do():
            try:
                from trading.state import state
                if platform == "Polymarket":
                    from predictions import polymarket
                    result = polymarket.place_order(market_id, side, price, size)
                    oid = result.get("orderID") or result.get("order_id") or "?"
                    self.after(0, self.bet_log.append, f"Order placed — ID: {oid}", "SUCCESS")

                elif platform == "Kalshi":
                    from predictions import kalshi
                    action = self.action_seg.get()
                    result = kalshi.place_order(market_id, side.lower(), action, int(size), int(price))
                    oid = result.get("order", {}).get("id", "?")
                    self.after(0, self.bet_log.append, f"Order placed — ID: {oid}", "SUCCESS")

                elif platform == "Metaculus":
                    from predictions import metaculus
                    result = metaculus.submit_prediction(int(market_id), price)
                    self.after(0, self.bet_log.append, f"Forecast submitted: {result}", "SUCCESS")

                state.log_bet({"platform": platform, "market_id": market_id, "side": side, "price": price, "size": size})

            except Exception as e:
                self.after(0, self.bet_log.append, f"Bet failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    def _analyze_edge(self):
        try:
            mkt_price = float(self.price_e.get())
            our_est   = float(self.our_est_e.get())
        except ValueError:
            self.bet_log.append("Fill in Price and Our Estimate first", "WARNING"); return

        platform = self.platform_seg.get().lower()
        side = self.side_seg.get()
        market_id = self.market_id_e.get().strip() or "—"

        from analysis.probability import score_opportunity
        opp = score_opportunity(
            platform=platform,
            market_id=market_id,
            question="Quick check",
            market_price_raw=mkt_price,
            our_estimate=our_est,
            side=side,
        )

        level = {"STRONG BET": "SUCCESS", "BET": "SUCCESS", "MARGINAL": "WARNING", "SKIP": "ERROR"}.get(opp.verdict, "DEFAULT")
        lines = [
            "─" * 36,
            f"Verdict:  {opp.verdict}",
            f"Edge:     {opp.edge_pct:+.1f}pp",
            f"EV:       {opp.ev*100:.2f}¢ per $1 risked",
            f"Kelly:    {opp.kelly_pct*100:.1f}% of bankroll",
            opp.rationale,
        ]
        for line in lines:
            self.bet_log.append(line, level)
