"""Numeric stat tile — shows a label + big value + optional delta."""
import customtkinter as ctk
from ui.theme import BG_CARD, BORDER, CORNER_RADIUS, TEXT_PRIMARY, TEXT_SECONDARY, GREEN, RED


class StatTile(ctk.CTkFrame):
    def __init__(self, master, label: str, value: str = "—", delta: str = "", delta_positive: bool | None = None, **kwargs):
        kwargs.setdefault("fg_color", BG_CARD)
        kwargs.setdefault("corner_radius", CORNER_RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", BORDER)
        super().__init__(master, **kwargs)

        ctk.CTkLabel(self, text=label, font=("Inter", 11), text_color=TEXT_SECONDARY).pack(anchor="w", padx=14, pady=(12, 0))

        self._value_label = ctk.CTkLabel(self, text=value, font=("Inter", 22, "bold"), text_color=TEXT_PRIMARY)
        self._value_label.pack(anchor="w", padx=14)

        if delta:
            colour = GREEN if delta_positive else RED if delta_positive is False else TEXT_SECONDARY
            ctk.CTkLabel(self, text=delta, font=("Inter", 11), text_color=colour).pack(anchor="w", padx=14, pady=(0, 12))
        else:
            ctk.CTkFrame(self, height=12, fg_color="transparent").pack()

    def update_value(self, value: str, text_color: str = TEXT_PRIMARY):
        self._value_label.configure(text=value, text_color=text_color)
