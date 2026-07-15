"""
UHRP client — shells out to the Node.js helper in uhrp_node/.

Why Node: publishing a file to UHRP storage requires paying the host's
storage invoice, which means signing a BSV transaction through a BRC-100
wallet. That payment/signing flow is only implemented (and maintained) in
Babbage's @bsv/sdk (JS/TS) — there is no Python equivalent, so upload and
resolve/download both go through uhrp_node/*.mjs via subprocess.

Uploading requires a running, funded BRC-100 wallet (e.g. MetaNet Desktop)
reachable on the machine running this bot. Resolving/downloading does not —
those are free overlay-network reads.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from config import cfg

_NODE_DIR = Path(__file__).resolve().parent.parent / "uhrp_node"


class UHRPError(Exception):
    pass


def _run_node(script: str, args: list[str], timeout: int) -> dict:
    if shutil.which("node") is None:
        raise UHRPError(
            "Node.js is not installed. UHRP upload/download needs Node 18+ "
            "and `npm install` run once inside uhrp_node/."
        )

    cmd = ["node", str(_NODE_DIR / script), *args]
    try:
        proc = subprocess.run(
            cmd, cwd=_NODE_DIR, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise UHRPError(f"{script} timed out after {timeout}s")

    lines = [ln for ln in (proc.stdout or "").strip().splitlines() if ln.strip()]
    if not lines:
        stderr = (proc.stderr or "").strip()
        raise UHRPError(f"{script} produced no output. stderr: {stderr[:500] or '(empty)'}")

    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError:
        raise UHRPError(f"{script} produced invalid output: {lines[-1][:500]}")

    if not data.get("ok"):
        raise UHRPError(data.get("error") or f"{script} failed")
    return data


def upload_file(
    file_path: str,
    retention_minutes: Optional[int] = None,
    storage_url: Optional[str] = None,
) -> dict:
    """Publishes file_path to UHRP storage. Returns dict with uhrpURL, hostedBy, sha256, mimeType, size."""
    retention_minutes = retention_minutes or cfg.UHRP_RETENTION_MINUTES
    storage_url = storage_url or cfg.UHRP_STORAGE_URL
    args = [file_path, str(retention_minutes)]
    if storage_url:
        args.append(storage_url)
    return _run_node("upload.mjs", args, timeout=180)


def resolve_url(uhrp_url: str) -> list[str]:
    """Resolves a uhrp:// URL to the direct HTTPS URL(s) currently hosting it. No wallet needed."""
    data = _run_node("resolve.mjs", [uhrp_url, cfg.UHRP_NETWORK_PRESET], timeout=60)
    return data.get("urls", [])


def download_file(uhrp_url: str, out_path: str) -> dict:
    """Downloads + hash-verifies a UHRP file to out_path. No wallet needed."""
    return _run_node("download.mjs", [uhrp_url, out_path, cfg.UHRP_NETWORK_PRESET], timeout=180)


def local_sha256(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
