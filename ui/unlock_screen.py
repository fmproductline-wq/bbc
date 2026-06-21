"""
Best Brand Co. — Password Unlock / First-Time Setup Screen

Shown before the main app window.
  • First launch  → Setup mode: enter private key + choose password
  • Return launch → Unlock mode: enter password to decrypt vault
  • Change password available in Settings tab
"""
from __future__ import annotations
import threading
import customtkinter as ctk
from pathlib import Path
from ui.theme import (
    BG_DARK, BG_CARD, BG_INPUT, BORDER, ACCENT, PURPLE,
    RED, GREEN, WHITE, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    FONT_BODY, FONT_SMALL, CORNER_RADIUS,
)

# Result container filled by the screen
_unlocked_key: str = ""


def get_unlocked_key() -> str:
    return _unlocked_key


class UnlockScreen(ctk.CTkToplevel):
    """
    Modal that must be completed before the main window opens.
    Calls on_success(private_key) when unlocked, on_cancel() if closed.
    """

    def __init__(self, master, on_success, on_cancel):
        super().__init__(master)
        self._on_success = on_success
        self._on_cancel  = on_cancel

        from security.key_vault import vault_exists
        self._setup_mode = not vault_exists()

        self.title("Best Brand Co. — Secure Unlock")
        self.geometry("480x620" if self._setup_mode else "480x400")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build()
        self.after(100, self._focus_password)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        # Top accent bar
        ctk.CTkFrame(self, height=3, fg_color=ACCENT, corner_radius=0).pack(fill="x")

        # Logo / title area
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(28, 0))

        _logo_path = Path(__file__).parent.parent / "assets" / "logo.png"
        if _logo_path.exists():
            try:
                from PIL import Image
                img = ctk.CTkImage(
                    light_image=Image.open(_logo_path),
                    dark_image=Image.open(_logo_path),
                    size=(140, 46),
                )
                ctk.CTkLabel(header, image=img, text="").pack(anchor="center")
            except Exception:
                self._text_logo(header)
        else:
            self._text_logo(header)

        mode_text = "First-Time Setup" if self._setup_mode else "Unlock Vault"
        ctk.CTkLabel(
            self, text=mode_text,
            font=("Inter", 15, "bold"), text_color=TEXT_PRIMARY,
        ).pack(pady=(12, 0))

        ctk.CTkLabel(
            self,
            text="Your private key is encrypted — it never leaves this device in plain text.",
            font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=380,
        ).pack(pady=(4, 16))

        # Card
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=0)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=24, pady=20)

        def lbl(text):
            ctk.CTkLabel(inner, text=text, font=FONT_SMALL,
                         text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(8, 2))

        # ── Setup mode: also collect private key ──────────────────────────────
        if self._setup_mode:
            lbl("Wallet Private Key  (stored encrypted — never shared)")
            self._key_entry = ctk.CTkEntry(
                inner, show="•", fg_color=BG_INPUT, border_color=BORDER,
                text_color=TEXT_PRIMARY, font=FONT_BODY,
            )
            self._key_entry.pack(fill="x")
            ctk.CTkLabel(
                inner,
                text="Paste your full private key (0x… or hex). It will be encrypted immediately.",
                font=("Inter", 10), text_color=TEXT_MUTED, wraplength=360, justify="left",
            ).pack(anchor="w", pady=(2, 0))

        # ── Password ──────────────────────────────────────────────────────────
        lbl("Password" if not self._setup_mode else "Choose a Password")
        self._pw_entry = ctk.CTkEntry(
            inner, show="•", fg_color=BG_INPUT, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            placeholder_text="Enter password…",
        )
        self._pw_entry.pack(fill="x")
        self._pw_entry.bind("<Return>",
                            lambda e: self._confirm_entry.focus() if self._setup_mode else self._submit())

        if self._setup_mode:
            lbl("Confirm Password")
            self._confirm_entry = ctk.CTkEntry(
                inner, show="•", fg_color=BG_INPUT, border_color=BORDER,
                text_color=TEXT_PRIMARY, font=FONT_BODY,
                placeholder_text="Re-enter password…",
            )
            self._confirm_entry.pack(fill="x")
            self._confirm_entry.bind("<Return>", lambda e: self._submit())

        # Status label
        self._status = ctk.CTkLabel(
            inner, text="", font=FONT_SMALL, text_color=RED, wraplength=360,
        )
        self._status.pack(pady=(10, 0))

        # Buttons
        btn_row = ctk.CTkFrame(inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(12, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        btn_label = "Encrypt & Unlock" if self._setup_mode else "Unlock"
        ctk.CTkButton(
            btn_row, text=f"🔓  {btn_label}",
            fg_color=ACCENT, text_color=BG_DARK, font=("Inter", 13, "bold"),
            command=self._submit,
        ).grid(row=0, column=0, padx=(0, 6), sticky="ew")

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color="transparent", text_color=TEXT_MUTED,
            hover_color=BG_INPUT, border_width=1, border_color=BORDER,
            command=self._cancel,
        ).grid(row=0, column=1, padx=(6, 0), sticky="ew")

        # Security note at bottom
        note = ctk.CTkFrame(self, fg_color="transparent")
        note.pack(fill="x", padx=32, pady=(16, 0))
        ctk.CTkLabel(
            note,
            text="🔒  AES-256 encryption · PBKDF2-SHA256 · 480,000 iterations\n"
                 "Key lives in memory only — wiped when app closes.",
            font=("Inter", 10), text_color=TEXT_MUTED,
            justify="center",
        ).pack(anchor="center")

    def _text_logo(self, parent):
        ctk.CTkLabel(
            parent, text="Best Brand Co.",
            font=("Inter", 22, "bold"), text_color=ACCENT,
        ).pack(anchor="center")

    def _focus_password(self):
        if self._setup_mode and hasattr(self, "_key_entry"):
            self._key_entry.focus()
        elif hasattr(self, "_pw_entry"):
            self._pw_entry.focus()

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _set_status(self, text: str, color: str = RED):
        self._status.configure(text=text, text_color=color)

    def _submit(self):
        from security.key_vault import (
            save_key, load_key, InvalidPassword, vault_exists,
        )

        password = self._pw_entry.get()
        if not password:
            self._set_status("Password is required.")
            return

        if self._setup_mode:
            # ── First-time setup ──────────────────────────────────────────────
            private_key = self._key_entry.get().strip()
            if not private_key:
                self._set_status("Private key is required.")
                return

            confirm = self._confirm_entry.get()
            if password != confirm:
                self._set_status("Passwords do not match.")
                return
            if len(password) < 8:
                self._set_status("Password must be at least 8 characters.")
                return

            self._set_status("Encrypting…", color=TEXT_MUTED)
            self.update()

            def _do():
                try:
                    save_key(private_key, password)
                    pk = load_key(password)
                    self.after(0, self._success, pk)
                except ValueError as e:
                    self.after(0, self._set_status, f"Invalid key: {e}")
                except Exception as e:
                    self.after(0, self._set_status, f"Error: {e}")

            threading.Thread(target=_do, daemon=True).start()

        else:
            # ── Unlock existing vault ─────────────────────────────────────────
            self._set_status("Decrypting…", color=TEXT_MUTED)
            self.update()

            def _do():
                try:
                    pk = load_key(password)
                    self.after(0, self._success, pk)
                except InvalidPassword:
                    self.after(0, self._set_status, "Wrong password. Try again.")
                except FileNotFoundError:
                    self.after(0, self._set_status, "Vault not found. Restart app.")
                except Exception as e:
                    self.after(0, self._set_status, f"Error: {e}")

            threading.Thread(target=_do, daemon=True).start()

    def _success(self, private_key: str):
        self._set_status("✓ Unlocked", color=GREEN)
        self.after(300, lambda: (self.destroy(), self._on_success(private_key)))

    def _cancel(self):
        self.destroy()
        self._on_cancel()


# ── Change-password dialog (used from Settings tab) ───────────────────────────

class ChangePasswordDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Change Vault Password")
        self.geometry("400x360")
        self.resizable(False, False)
        self.configure(fg_color=BG_DARK)
        self.grab_set()
        self._build()

    def _build(self):
        ctk.CTkFrame(self, height=3, fg_color=ACCENT, corner_radius=0).pack(fill="x")
        ctk.CTkLabel(self, text="Change Vault Password",
                     font=("Inter", 15, "bold"), text_color=TEXT_PRIMARY).pack(pady=(20, 4))

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=28, pady=8)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)

        def lbl(t):
            ctk.CTkLabel(inner, text=t, font=FONT_SMALL,
                         text_color=TEXT_SECONDARY, anchor="w").pack(fill="x", pady=(6, 2))

        lbl("Current Password")
        self._old = ctk.CTkEntry(inner, show="•", fg_color=BG_INPUT,
                                  border_color=BORDER, text_color=TEXT_PRIMARY, font=FONT_BODY)
        self._old.pack(fill="x")

        lbl("New Password  (min 8 characters)")
        self._new = ctk.CTkEntry(inner, show="•", fg_color=BG_INPUT,
                                  border_color=BORDER, text_color=TEXT_PRIMARY, font=FONT_BODY)
        self._new.pack(fill="x")

        lbl("Confirm New Password")
        self._conf = ctk.CTkEntry(inner, show="•", fg_color=BG_INPUT,
                                   border_color=BORDER, text_color=TEXT_PRIMARY, font=FONT_BODY)
        self._conf.pack(fill="x")
        self._conf.bind("<Return>", lambda e: self._submit())

        self._status = ctk.CTkLabel(inner, text="", font=FONT_SMALL,
                                     text_color=RED, wraplength=320)
        self._status.pack(pady=(8, 0))

        ctk.CTkButton(inner, text="🔑  Update Password",
                      fg_color=ACCENT, text_color=BG_DARK,
                      font=("Inter", 12, "bold"),
                      command=self._submit).pack(fill="x", pady=(10, 0))

    def _submit(self):
        from security.key_vault import change_password, InvalidPassword
        old = self._old.get()
        new = self._new.get()
        conf = self._conf.get()

        if not all([old, new, conf]):
            self._status.configure(text="All fields required.", text_color=RED)
            return
        if new != conf:
            self._status.configure(text="New passwords do not match.", text_color=RED)
            return
        if len(new) < 8:
            self._status.configure(text="Password must be at least 8 characters.", text_color=RED)
            return

        self._status.configure(text="Updating…", text_color=TEXT_MUTED)
        self.update()

        def _do():
            try:
                change_password(old, new)
                self.after(0, self._status.configure,
                           {"text": "✓ Password updated successfully", "text_color": GREEN})
                self.after(1500, self.destroy)
            except InvalidPassword:
                self.after(0, self._status.configure,
                           {"text": "Current password is wrong.", "text_color": RED})
            except Exception as e:
                self.after(0, self._status.configure,
                           {"text": f"Error: {e}", "text_color": RED})

        threading.Thread(target=_do, daemon=True).start()
