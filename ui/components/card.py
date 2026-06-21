"""Reusable card frame component."""
import customtkinter as ctk
from ui.theme import BG_CARD, BORDER, CORNER_RADIUS, PAD


class Card(ctk.CTkFrame):
    """A rounded card with optional title label."""

    def __init__(self, master, title: str = "", **kwargs):
        kwargs.setdefault("fg_color", BG_CARD)
        kwargs.setdefault("corner_radius", CORNER_RADIUS)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", BORDER)
        super().__init__(master, **kwargs)

        if title:
            ctk.CTkLabel(
                self,
                text=title,
                font=("Inter", 13, "bold"),
                text_color="#8B949E",
                anchor="w",
            ).pack(anchor="w", padx=PAD, pady=(PAD, 4))
