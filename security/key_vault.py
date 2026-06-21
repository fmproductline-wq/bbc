"""
Best Brand Co. — Encrypted Key Vault

The private key is NEVER stored in plain text after first setup.

How it works
────────────
1. First launch: user enters password + private key in the unlock screen
2. A random 128-bit salt is generated
3. PBKDF2-HMAC-SHA256 (480,000 iterations) derives a 256-bit AES key from password+salt
4. Fernet (AES-128-CBC + HMAC-SHA256) encrypts the private key
5. Encrypted blob + salt are saved to ~/.bestbrand/vault.enc
6. Plain-text key is NEVER written to disk

On every subsequent launch
──────────────────────────
1. User enters password
2. Same derivation recreates the AES key
3. Decrypts vault → private key available in memory only for the session
4. Wrong password → decryption fails → key never exposed

The .env WALLET_PRIVATE_KEY entry is OPTIONAL once the vault is set up.
If vault exists, it takes priority. .env key is ignored.
"""
from __future__ import annotations

import base64
import os
import struct
from pathlib import Path
from loguru import logger

_BBC_DIR   = Path.home() / ".bestbrand"
_VAULT_FILE = _BBC_DIR / "vault.enc"

# PBKDF2 parameters
_ITERATIONS = 480_000
_SALT_BYTES  = 16
_KEY_BYTES   = 32   # 256-bit AES key


# ── Key derivation ────────────────────────────────────────────────────────────

def _derive_key(password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 → 256-bit key."""
    import hashlib
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
        dklen=_KEY_BYTES,
    )
    return base64.urlsafe_b64encode(dk)


# ── Vault operations ──────────────────────────────────────────────────────────

def vault_exists() -> bool:
    return _VAULT_FILE.exists()


def save_key(private_key: str, password: str) -> None:
    """
    Encrypt and save the private key with the given password.
    Raises ValueError if the key doesn't look like a hex private key.
    """
    pk = private_key.strip()
    if pk.startswith("0x"):
        pk = pk[2:]
    if len(pk) != 64 or not all(c in "0123456789abcdefABCDEF" for c in pk):
        raise ValueError("Private key must be a 64-character hex string (with or without 0x prefix)")

    from cryptography.fernet import Fernet
    salt       = os.urandom(_SALT_BYTES)
    fernet_key = _derive_key(password, salt)
    f          = Fernet(fernet_key)
    encrypted  = f.encrypt(pk.encode("utf-8"))

    _BBC_DIR.mkdir(parents=True, exist_ok=True)
    # Format: [2-byte salt length][salt][encrypted payload]
    with open(_VAULT_FILE, "wb") as fp:
        fp.write(struct.pack(">H", _SALT_BYTES))
        fp.write(salt)
        fp.write(encrypted)

    # Set file permissions: owner read/write only (unix)
    try:
        _VAULT_FILE.chmod(0o600)
    except Exception:
        pass

    logger.info("Private key encrypted and saved to vault")


def load_key(password: str) -> str:
    """
    Decrypt and return the private key (with 0x prefix).
    Raises InvalidPassword if password is wrong.
    Raises FileNotFoundError if vault doesn't exist yet.
    """
    if not _VAULT_FILE.exists():
        raise FileNotFoundError("Vault not found — set up your key first")

    from cryptography.fernet import Fernet, InvalidToken

    with open(_VAULT_FILE, "rb") as fp:
        salt_len  = struct.unpack(">H", fp.read(2))[0]
        salt      = fp.read(salt_len)
        encrypted = fp.read()

    fernet_key = _derive_key(password, salt)
    f = Fernet(fernet_key)

    try:
        pk = f.decrypt(encrypted).decode("utf-8")
    except InvalidToken:
        raise InvalidPassword("Wrong password — could not decrypt key vault")

    return "0x" + pk


def delete_vault() -> None:
    """Wipe the vault file (use with caution)."""
    if _VAULT_FILE.exists():
        _VAULT_FILE.unlink()
        logger.warning("Key vault deleted")


def change_password(old_password: str, new_password: str) -> None:
    """Re-encrypt the vault with a new password."""
    pk = load_key(old_password)   # raises InvalidPassword if wrong
    save_key(pk, new_password)
    logger.info("Vault password changed")


class InvalidPassword(Exception):
    pass
