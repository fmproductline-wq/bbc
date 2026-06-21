"""Scrollable coloured log output box."""
import customtkinter as ctk
from ui.theme import BG_INPUT, TEXT_PRIMARY, GREEN, RED, YELLOW, ACCENT, FONT_MONO


class LogBox(ctk.CTkTextbox):
    """Read-only, auto-scrolling log widget with colour tagging."""

    TAG_COLOURS = {
        "INFO":     ACCENT,
        "SUCCESS":  GREEN,
        "ERROR":    RED,
        "WARNING":  YELLOW,
        "SIGNAL":   "#BC8CFF",
        "DEFAULT":  TEXT_PRIMARY,
    }

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", BG_INPUT)
        kwargs.setdefault("font", FONT_MONO)
        kwargs.setdefault("state", "disabled")
        kwargs.setdefault("wrap", "word")
        super().__init__(master, **kwargs)

        for tag, colour in self.TAG_COLOURS.items():
            self._textbox.tag_configure(tag, foreground=colour)

    def append(self, text: str, level: str = "DEFAULT"):
        self.configure(state="normal")
        import time
        ts = time.strftime("%H:%M:%S")
        line = f"[{ts}] {text}\n"
        self._textbox.insert("end", line, level)
        self.configure(state="disabled")
        self.see("end")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
