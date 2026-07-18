"""
Reconciles the local Excel ledger against what's actually on the storage
host — the same data behind a UHRP storage UI's "Files" / "Manage Your
Files" view (listUploads + findFile). Lets the ledger catch up on files
uploaded from elsewhere and refreshes expiry/status for everything it
already knows about, without needing to revisit the storage host's website.
"""
from __future__ import annotations
from typing import Callable, Optional

from uhrp import client as uhrp_client, ledger as uhrp_ledger

ProgressFn = Optional[Callable[[str], None]]


def sync_from_host(requested_by: str, on_progress: ProgressFn = None) -> dict:
    """
    Pulls the wallet's hosted file list, updates Expiry Time/Status for rows
    already in the ledger, and adds a new row (direction SYNCED) for any
    hosted file the ledger doesn't know about yet.

    Returns {"updated": int, "added": int, "errors": list[str]}.
    """
    def emit(msg: str):
        if on_progress:
            on_progress(msg)

    emit("Fetching hosted file list…")
    uploads = uhrp_client.list_uploads()
    known = uhrp_ledger.known_uhrp_urls()

    updated = 0
    added = 0
    errors: list[str] = []

    for entry in uploads:
        uhrp_url = entry.get("uhrpUrl")
        expiry_time = entry.get("expiryTime")
        if not uhrp_url:
            continue

        # Ledger writes (openpyxl) can fail independently of the network calls above
        # (e.g. the .xlsx is open in Excel) — a bad row must not abort the rest of
        # the loop, or files the host already reported get silently dropped from sync.
        try:
            if uhrp_url in known:
                if expiry_time:
                    uhrp_ledger.update_expiry(uhrp_url, expiry_time)
                    updated += 1
                continue

            emit(f"New file on host: {uhrp_url[:24]}… — fetching details")
            try:
                details = uhrp_client.find_file(uhrp_url)
            except uhrp_client.UHRPError as e:
                errors.append(f"{uhrp_url}: {e}")
                details = {}

            try:
                size = int(details.get("size") or 0)
            except (TypeError, ValueError):
                size = 0

            direct_link = None
            try:
                urls = uhrp_client.resolve_url(uhrp_url)
                direct_link = urls[0] if urls else None
            except uhrp_client.UHRPError:
                pass  # not fatal — direct link stays "pending", resolvable later

            uhrp_ledger.add_entry(
                direction="SYNCED",
                filename=details.get("name") or uhrp_url,
                content_type=details.get("mimeType") or "",
                size=size,
                sha256="",
                uhrp_url=uhrp_url,
                direct_link=direct_link,
                hosted_by=[],
                local_path=None,
                requested_by=requested_by,
                expiry_time=details.get("expiryTime") or expiry_time,
            )
            added += 1
        except Exception as e:
            errors.append(f"{uhrp_url}: ledger write failed — {e}")

    emit(f"Sync complete — {updated} updated, {added} added.")
    return {"updated": updated, "added": added, "errors": errors}
