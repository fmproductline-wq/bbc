"""
Install ID & Age Verification Registry.

On first launch, generates a unique install ID (UUID4) and records it
alongside the user's age verification, T&C acceptance timestamp, and
platform info. All records are stored locally in ~/.bbc/registry.json
and appended to a per-install log file ~/.bbc/installs.log.

This gives the Creator a persistent, per-device compliance record.
"""
from __future__ import annotations
import json
import os
import platform
import sys
import time
import uuid
from pathlib import Path
from loguru import logger

# ── Storage paths ─────────────────────────────────────────────────────────────
_BBC_DIR  = Path.home() / ".bbc"
_REG_FILE = _BBC_DIR / "registry.json"
_LOG_FILE = _BBC_DIR / "installs.log"

APP_VERSION = "2.0.0"


def _ensure_dir():
    _BBC_DIR.mkdir(parents=True, exist_ok=True)


# ── Registry record ───────────────────────────────────────────────────────────

def _load_registry() -> dict:
    _ensure_dir()
    if _REG_FILE.exists():
        try:
            return json.loads(_REG_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_registry(data: dict):
    _ensure_dir()
    _REG_FILE.write_text(json.dumps(data, indent=2))


def get_or_create_install_id() -> str:
    """
    Return the persistent install ID for this device.
    Creates one on first call and stores it in ~/.bbc/registry.json.
    """
    reg = _load_registry()
    if "install_id" not in reg:
        reg["install_id"] = str(uuid.uuid4())
        reg["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        reg["platform"]   = platform.system()
        reg["python"]     = sys.version.split()[0]
        reg["app_version"] = APP_VERSION
        _save_registry(reg)
        logger.info(f"New install registered: {reg['install_id']}")
    return reg["install_id"]


# ── Age verification ──────────────────────────────────────────────────────────

def is_age_verified() -> bool:
    """True if the user has already confirmed they are 18+ on this device."""
    reg = _load_registry()
    return reg.get("age_verified", False)


def is_terms_accepted() -> bool:
    """True if T&C have been accepted on this device."""
    reg = _load_registry()
    return reg.get("terms_accepted", False)


def record_acceptance(age_verified: bool, birth_year: int | None = None):
    """
    Persist age verification + T&C acceptance to the registry and append
    a timestamped entry to the install log.

    Args:
        age_verified:  True if user confirmed they are 18+
        birth_year:    Optional birth year (not stored — only used to verify age ≥ 18)
    """
    reg = _load_registry()
    install_id = reg.get("install_id") or get_or_create_install_id()
    reg = _load_registry()   # reload after potential creation

    now_ts  = time.time()
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_ts))

    reg["age_verified"]       = age_verified
    reg["terms_accepted"]     = True
    reg["accepted_at"]        = now_str
    reg["accepted_ts"]        = now_ts
    reg["acceptance_version"] = "2026-06-21"  # T&C version date

    _save_registry(reg)

    # Append to flat log (one line per acceptance event)
    _ensure_dir()
    log_entry = (
        f"{now_str} | install_id={install_id} | age_verified={age_verified} "
        f"| platform={platform.system()} | version={APP_VERSION} "
        f"| terms_version=2026-06-21\n"
    )
    with open(_LOG_FILE, "a") as f:
        f.write(log_entry)

    logger.info(f"Acceptance recorded for install {install_id}")


def get_registry_summary() -> dict:
    """Return the full registry record for display in the Settings tab."""
    reg = _load_registry()
    return {
        "install_id":     reg.get("install_id", "—"),
        "created_at":     reg.get("created_at", "—"),
        "platform":       reg.get("platform", "—"),
        "app_version":    reg.get("app_version", "—"),
        "age_verified":   reg.get("age_verified", False),
        "terms_accepted": reg.get("terms_accepted", False),
        "accepted_at":    reg.get("accepted_at", "—"),
    }


def list_all_install_entries() -> list[str]:
    """Return all lines from the installs log (for admin review)."""
    if not _LOG_FILE.exists():
        return []
    return _LOG_FILE.read_text().strip().splitlines()
