"""
UHRP Document Uploader tab — offline desktop UI for publishing/fetching
files on UHRP storage, paired with the same uhrp/client.py + uhrp/ledger.py
backend the Telegram bot uses (uhrp_node/*.mjs → a local BRC-100 wallet
such as Metanet Client, and nanostore.babbage.systems for storage).
"""
from __future__ import annotations
import os
import sys
import subprocess
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from ui.theme import *
from ui.components.card import Card
from ui.components.log_box import LogBox

RETENTION_CHOICES = [
    ("1 Day", 1440),
    ("7 Days", 10080),
    ("30 Days", 43200),
    ("90 Days", 129600),
    ("1 Year", 525600),
    ("10 Years", 5256000),
    ("100 Years", 52560000),
]


def _format_size(n: int) -> str:
    size = float(n)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _open_path(path: str):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception:
        pass


class UHRPTab(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self._files: list[dict] = []  # {path, filename, size, status_lbl, link}
        self._build()
        self._refresh_wallet_status(silent=True)

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.columnconfigure(0, weight=1, minsize=280)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(PAD, 4), pady=PAD)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, PAD), pady=PAD)
        right.rowconfigure(1, weight=2)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        self._build_wallet_card(left)
        self._build_upload_card(left)
        self._build_download_card(left)
        self._build_ledger_card(left)
        self._build_manage_card(left)
        self._build_queue(right)
        self._build_activity(right)

    # ── Left: Wallet status ───────────────────────────────────────────────────

    def _build_wallet_card(self, parent):
        card = Card(parent, title="Wallet")
        card.pack(fill="x")
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.wallet_dot = ctk.CTkLabel(pad, text="● Not checked", font=FONT_SMALL, text_color=TEXT_MUTED)
        self.wallet_dot.pack(anchor="w")

        ctk.CTkButton(pad, text="🔌  Check Wallet", fg_color=BG_INPUT, text_color=ACCENT,
                      hover_color=BORDER, font=FONT_BODY,
                      command=self._refresh_wallet_status).pack(fill="x", pady=(8, 0))

    def _refresh_wallet_status(self, silent: bool = False):
        if not silent:
            self.wallet_dot.configure(text="● Checking…", text_color=YELLOW)

        def _do():
            from uhrp import client as uhrp_client
            try:
                result = uhrp_client.check_wallet()
                text = f"● Connected — v{result.get('version', '?')}"
                self.after(0, self.wallet_dot.configure, {"text": text, "text_color": GREEN})
            except uhrp_client.UHRPError as e:
                self.after(0, self.wallet_dot.configure, {"text": "● No wallet reachable", "text_color": RED})
                if not silent:
                    self.after(0, self._log, f"Wallet check failed: {e}", "ERROR")

        threading.Thread(target=_do, daemon=True).start()

    # ── Left: Upload controls ─────────────────────────────────────────────────

    def _build_upload_card(self, parent):
        card = Card(parent, title="Upload to UHRP")
        card.pack(fill="x", pady=(12, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        row1 = ctk.CTkFrame(pad, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(row1, text="📄+ Add Files", fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
                      hover_color=BORDER, font=FONT_SMALL, width=110,
                      command=self._add_files).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row1, text="📁+ Add Folder", fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
                      hover_color=BORDER, font=FONT_SMALL, width=110,
                      command=self._add_folder).pack(side="left")

        ctk.CTkLabel(pad, text="Retention", font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.retention_var = ctk.StringVar(value="30 Days")
        ctk.CTkOptionMenu(pad, variable=self.retention_var, values=[c[0] for c in RETENTION_CHOICES],
                          fg_color=BG_INPUT, button_color=BORDER, button_hover_color=ACCENT,
                          text_color=TEXT_PRIMARY, font=FONT_BODY).pack(fill="x", pady=(2, 8))

        ctk.CTkButton(pad, text="⬆  Upload All", fg_color=GREEN, text_color="black",
                      font=("Inter", 13, "bold"), command=self._upload_all).pack(fill="x", pady=(0, 4))
        ctk.CTkButton(pad, text="🗑  Clear List", fg_color=BG_INPUT, text_color=TEXT_SECONDARY,
                      hover_color=BORDER, font=FONT_SMALL, command=self._clear_queue).pack(fill="x")

        ctk.CTkLabel(
            pad, text="Uploads pay a real BSV storage fee via your wallet. "
                      "Every upload is logged to the Excel ledger automatically.",
            font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=240, justify="left", anchor="w",
        ).pack(fill="x", pady=(8, 0))

    def _retention_minutes(self) -> int:
        label = self.retention_var.get()
        for name, minutes in RETENTION_CHOICES:
            if name == label:
                return minutes
        return 43200

    # ── Left: Download ────────────────────────────────────────────────────────

    def _build_download_card(self, parent):
        card = Card(parent, title="Download from UHRP")
        card.pack(fill="x", pady=(12, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkLabel(pad, text="UHRP URL", font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.download_entry = ctk.CTkEntry(pad, fg_color=BG_INPUT, border_color=BORDER,
                                            text_color=TEXT_PRIMARY, font=FONT_BODY,
                                            placeholder_text="uhrp://…")
        self.download_entry.pack(fill="x", pady=(2, 8))

        ctk.CTkButton(pad, text="⬇  Download", fg_color=ACCENT, text_color="white",
                      font=("Inter", 13, "bold"), command=self._download).pack(fill="x")

    # ── Left: Ledger shortcuts ────────────────────────────────────────────────

    def _build_ledger_card(self, parent):
        card = Card(parent, title="Ledger")
        card.pack(fill="x", pady=(12, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkButton(pad, text="📒  Open Ledger (Excel)", fg_color=BG_INPUT, text_color=ACCENT,
                      hover_color=BORDER, font=FONT_BODY,
                      command=self._open_ledger).pack(fill="x", pady=(0, 6))
        ctk.CTkButton(pad, text="📁  Open Files Folder", fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
                      hover_color=BORDER, font=FONT_BODY,
                      command=self._open_files_folder).pack(fill="x")

    def _open_ledger(self):
        from uhrp import ledger as uhrp_ledger
        _open_path(str(uhrp_ledger.get_ledger_path()))

    def _open_files_folder(self):
        from uhrp import ledger as uhrp_ledger
        uhrp_ledger.ensure_dirs()
        _open_path(str(uhrp_ledger.FILES_DIR))

    # ── Left: Manage hosted files (sync + renew) ──────────────────────────────

    def _build_manage_card(self, parent):
        card = Card(parent, title="Manage Hosted Files")
        card.pack(fill="x", pady=(12, 0))
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=PAD, pady=(0, PAD))

        ctk.CTkLabel(
            pad, text="Pulls your actual file list from the storage host and "
                      "reconciles it into the ledger — catches anything not "
                      "already logged and refreshes expiry/status.",
            font=FONT_SMALL, text_color=TEXT_MUTED, wraplength=240, justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(pad, text="🔄  Sync from Host", fg_color=BG_INPUT, text_color=ACCENT,
                      hover_color=BORDER, font=FONT_BODY, command=self._sync_from_host).pack(fill="x")

        ctk.CTkFrame(pad, height=1, fg_color=BORDER).pack(fill="x", pady=10)

        ctk.CTkLabel(pad, text="Renew (extend hosting)", font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, anchor="w").pack(fill="x")
        self.renew_url_entry = ctk.CTkEntry(pad, fg_color=BG_INPUT, border_color=BORDER,
                                             text_color=TEXT_PRIMARY, font=FONT_SMALL,
                                             placeholder_text="uhrp://…")
        self.renew_url_entry.pack(fill="x", pady=(2, 4))
        self.renew_minutes_entry = ctk.CTkEntry(pad, fg_color=BG_INPUT, border_color=BORDER,
                                                 text_color=TEXT_PRIMARY, font=FONT_SMALL,
                                                 placeholder_text="Additional minutes (e.g. 43200)")
        self.renew_minutes_entry.pack(fill="x", pady=(0, 6))
        ctk.CTkButton(pad, text="⏳  Renew", fg_color=BG_INPUT, text_color=ACCENT,
                      hover_color=BORDER, font=FONT_BODY, command=self._renew).pack(fill="x")

    def _sync_from_host(self):
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _run_sync(self):
        from uhrp import client as uhrp_client, sync as uhrp_sync
        self.after(0, self._log, "Syncing ledger with UHRP host…", "INFO")
        try:
            result = uhrp_sync.sync_from_host(
                "desktop-ui", on_progress=lambda msg: self.after(0, self._log, msg, "DEFAULT")
            )
        except uhrp_client.UHRPError as e:
            self.after(0, self._log, f"❌ Sync failed: {e}", "ERROR")
            return
        self.after(0, self._log,
                    f"✅ Sync complete — {result['updated']} updated, {result['added']} added.", "SUCCESS")
        if result["errors"]:
            self.after(0, self._log, f"⚠️ {len(result['errors'])} file(s) had lookup errors.", "WARNING")

    def _renew(self):
        uhrp_url = self.renew_url_entry.get().strip()
        minutes_raw = self.renew_minutes_entry.get().strip()
        if not uhrp_url or not minutes_raw:
            self._log("Enter a UHRP URL and additional minutes to renew.", "WARNING")
            return
        try:
            minutes = int(minutes_raw)
        except ValueError:
            self._log("Additional minutes must be a whole number.", "WARNING")
            return
        threading.Thread(target=self._run_renew, args=(uhrp_url, minutes), daemon=True).start()

    def _run_renew(self, uhrp_url: str, minutes: int):
        from uhrp import client as uhrp_client, ledger as uhrp_ledger
        self.after(0, self._log, f"Renewing {uhrp_url}…", "INFO")
        try:
            result = uhrp_client.renew_file(uhrp_url, minutes)
        except uhrp_client.UHRPError as e:
            self.after(0, self._log, f"❌ Renew failed: {e}", "ERROR")
            return
        new_expiry = result.get("newExpiryTime")
        if new_expiry:
            uhrp_ledger.update_expiry(uhrp_url, new_expiry)
        self.after(0, self._log,
                    f"✅ Renewed — paid {result.get('amount', '?')} sats, new expiry {new_expiry or 'unknown'}",
                    "SUCCESS")

    # ── Right: File queue table ───────────────────────────────────────────────

    def _build_queue(self, parent):
        card = Card(parent, title="File Queue")
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=PAD)
        header.columnconfigure(0, weight=3)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=2)
        for i, text in enumerate(["File Name", "Size", "Status"]):
            ctk.CTkLabel(header, text=text, font=("Inter", 11, "bold"),
                         text_color=TEXT_SECONDARY, anchor="w").grid(row=0, column=i, sticky="w", pady=(0, 4))

        self.queue_frame = ctk.CTkScrollableFrame(card, fg_color=BG_INPUT, corner_radius=CORNER_RADIUS)
        self.queue_frame.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, 4))
        self.queue_frame.columnconfigure(0, weight=3)
        self.queue_frame.columnconfigure(1, weight=1)
        self.queue_frame.columnconfigure(2, weight=2)

        self.empty_label = ctk.CTkLabel(self.queue_frame, text="No files added yet.",
                                         font=FONT_SMALL, text_color=TEXT_MUTED)
        self.empty_label.grid(row=0, column=0, columnspan=3, pady=20)

        prog_wrap = ctk.CTkFrame(card, fg_color="transparent")
        prog_wrap.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(4, PAD))
        prog_wrap.columnconfigure(0, weight=1)

        self.progress_label = ctk.CTkLabel(prog_wrap, text="Upload Progress — 0%",
                                            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self.progress_label.grid(row=0, column=0, sticky="w")
        self.progress_bar = ctk.CTkProgressBar(prog_wrap, progress_color=ACCENT, fg_color=BORDER)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _build_activity(self, parent):
        card = Card(parent, title="Activity")
        card.grid(row=1, column=0, sticky="nsew")
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        inner.rowconfigure(0, weight=1)
        inner.columnconfigure(0, weight=1)
        self.log_box = LogBox(inner)
        self.log_box.grid(row=0, column=0, sticky="nsew")

    def _log(self, text: str, level: str = "DEFAULT"):
        self.log_box.append(text, level)

    # ── Queue management ──────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(title="Select files to publish to UHRP")
        for p in paths:
            self._queue_file(p)

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder to publish to UHRP")
        if not folder:
            return
        for root, dirs, files in os.walk(folder):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.startswith("."):
                    continue
                self._queue_file(os.path.join(root, name))

    def _queue_file(self, path: str):
        if not os.path.isfile(path):
            return
        self.empty_label.grid_forget()
        filename = os.path.basename(path)
        size = os.path.getsize(path)
        row = len(self._files)

        ctk.CTkLabel(self.queue_frame, text=filename, font=FONT_SMALL, text_color=TEXT_PRIMARY,
                     anchor="w").grid(row=row, column=0, sticky="w", padx=(6, 4), pady=3)
        ctk.CTkLabel(self.queue_frame, text=_format_size(size), font=FONT_SMALL, text_color=TEXT_SECONDARY,
                     anchor="w").grid(row=row, column=1, sticky="w", pady=3)
        status_lbl = ctk.CTkLabel(self.queue_frame, text="Queued", font=FONT_SMALL, text_color=YELLOW, anchor="w")
        status_lbl.grid(row=row, column=2, sticky="w", padx=(0, 6), pady=3)

        self._files.append({
            "path": path, "filename": filename, "size": size,
            "status_lbl": status_lbl, "status": "Queued",
        })

    def _clear_queue(self):
        for widget in self.queue_frame.winfo_children():
            widget.destroy()
        self._files.clear()
        self.empty_label = ctk.CTkLabel(self.queue_frame, text="No files added yet.",
                                         font=FONT_SMALL, text_color=TEXT_MUTED)
        self.empty_label.grid(row=0, column=0, columnspan=3, pady=20)
        self._set_progress(0, "Upload Progress — 0%")

    def _set_progress(self, frac: float, text: str):
        self.progress_bar.set(frac)
        self.progress_label.configure(text=text)

    # ── Upload flow ───────────────────────────────────────────────────────────

    def _upload_all(self):
        pending = [f for f in self._files if f["status"] == "Queued"]
        if not pending:
            self._log("No queued files to upload.", "WARNING")
            return
        threading.Thread(target=self._run_uploads, args=(pending,), daemon=True).start()

    def _run_uploads(self, files: list[dict]):
        from uhrp import client as uhrp_client, ledger as uhrp_ledger
        uhrp_ledger.ensure_dirs()
        total = len(files)
        retention = self._retention_minutes()

        for i, f in enumerate(files):
            pct = i / total
            self.after(0, self._set_progress, pct, f"Uploading {f['filename']} ({i + 1}/{total})")
            self.after(0, f["status_lbl"].configure, {"text": "Uploading…", "text_color": ACCENT})
            self.after(0, self._log, f"Uploading {f['filename']}…", "INFO")

            try:
                result = uhrp_client.upload_file(f["path"], retention)
                uhrp_url = result["uhrpURL"]

                direct_link = None
                try:
                    urls = uhrp_client.resolve_url(uhrp_url)
                    direct_link = urls[0] if urls else None
                except uhrp_client.UHRPError:
                    pass

                row = uhrp_ledger.add_entry(
                    direction="UPLOAD",
                    filename=f["filename"],
                    content_type=result.get("mimeType", ""),
                    size=result.get("size", f["size"]),
                    sha256=result.get("sha256", ""),
                    uhrp_url=uhrp_url,
                    direct_link=direct_link,
                    hosted_by=result.get("hostedBy", []),
                    local_path=f["path"],
                    requested_by="desktop-ui",
                )
                f["status"] = "Uploaded"
                self.after(0, f["status_lbl"].configure, {"text": "✅ Uploaded", "text_color": GREEN})
                self.after(0, self._log, f"✅ {f['filename']} → {uhrp_url}  (ledger row {row})", "SUCCESS")
                if direct_link:
                    self.after(0, self._log, f"   Direct link: {direct_link}", "SUCCESS")
                else:
                    self.after(0, self._log, "   Direct link pending — resolve later once it propagates.", "WARNING")

            except uhrp_client.UHRPError as e:
                f["status"] = "Failed"
                self.after(0, f["status_lbl"].configure, {"text": "❌ Failed", "text_color": RED})
                self.after(0, self._log, f"❌ {f['filename']} failed: {e}", "ERROR")

        self.after(0, self._set_progress, 1.0, "Upload Progress — 100%")

    # ── Download flow ─────────────────────────────────────────────────────────

    def _download(self):
        uhrp_url = self.download_entry.get().strip()
        if not uhrp_url:
            self._log("Enter a UHRP URL to download.", "WARNING")
            return
        threading.Thread(target=self._run_download, args=(uhrp_url,), daemon=True).start()

    def _run_download(self, uhrp_url: str):
        import mimetypes
        from uhrp import client as uhrp_client, ledger as uhrp_ledger
        uhrp_ledger.ensure_dirs()

        self.after(0, self._log, f"Downloading {uhrp_url}…", "INFO")
        short_hash = uhrp_url.replace("uhrp://", "").replace("uhrp:", "")[:16] or "uhrp_file"
        tmp_path = uhrp_ledger.FILES_DIR / short_hash

        try:
            result = uhrp_client.download_file(uhrp_url, str(tmp_path))
        except uhrp_client.UHRPError as e:
            self.after(0, self._log, f"❌ Download failed: {e}", "ERROR")
            return

        mime_type = result.get("mimeType") or "application/octet-stream"
        ext = mimetypes.guess_extension(mime_type) or ""
        final_path = uhrp_ledger.FILES_DIR / f"{short_hash}{ext}"
        tmp_path.rename(final_path)

        row = uhrp_ledger.add_entry(
            direction="DOWNLOAD",
            filename=final_path.name,
            content_type=mime_type,
            size=result.get("size", 0),
            sha256=uhrp_client.local_sha256(str(final_path)),
            uhrp_url=uhrp_url,
            direct_link=None,
            hosted_by=[],
            local_path=str(final_path),
            requested_by="desktop-ui",
        )
        try:
            urls = uhrp_client.resolve_url(uhrp_url)
            if urls:
                uhrp_ledger.update_direct_link(uhrp_url, urls[0])
        except uhrp_client.UHRPError:
            pass

        self.after(0, self._log, f"✅ Downloaded → {final_path}  (ledger row {row})", "SUCCESS")
