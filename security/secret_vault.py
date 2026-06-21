"""
Best Brand Co. — Extended Secret Vault  (#1)

Extends key_vault to store ALL sensitive config values encrypted:
  Telegram token, Stripe keys, Polymarket/Kalshi credentials, API keys.

Format: vault stores a JSON dict encrypted with the same PBKDF2+Fernet
approach as key_vault.py.  Separate file: ~/.bestbrand/secrets.enc
"""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path
from loguru import logger

_BBC_DIR      = Path.home() / ".bestbrand"
_SECRETS_FILE = _BBC_DIR / "secrets.enc"

_ITERATIONS = 480_000
_SALT_BYTES  = 16
_KEY_BYTES   = 32

# Which .env keys to migrate into the vault
VAULT_KEYS: list[str] = [
    "TELEGRAM_BOT_TOKEN",
    "TRADINGVIEW_WEBHOOK_SECRET",
    "ONEINCH_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_PRICE_ID",
    "POLYMARKET_API_KEY",
    "POLYMARKET_API_SECRET",
    "POLYMARKET_API_PASSPHRASE",
    "KALSHI_PASSWORD",
    "METACULUS_TOKEN",
]


def _derive_key(password: str, salt: bytes) -> bytes:
    import hashlib, base64
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS, dklen=_KEY_BYTES)
    return base64.urlsafe_b64encode(dk)


def secrets_vault_exists() -> bool:
    return _SECRETS_FILE.exists()


def save_secrets(secrets: dict[str, str], password: str) -> None:
    """Encrypt and persist the secrets dict."""
    from cryptography.fernet import Fernet
    salt       = os.urandom(_SALT_BYTES)
    fernet_key = _derive_key(password, salt)
    f          = Fernet(fernet_key)
    payload    = json.dumps(secrets).encode("utf-8")
    encrypted  = f.encrypt(payload)

    _BBC_DIR.mkdir(parents=True, exist_ok=True)
    with open(_SECRETS_FILE, "wb") as fp:
        fp.write(struct.pack(">H", _SALT_BYTES))
        fp.write(salt)
        fp.write(encrypted)
    try:
        _SECRETS_FILE.chmod(0o600)
    except Exception:
        pass
    logger.info(f"Saved {len(secrets)} secrets to vault")


def load_secrets(password: str) -> dict[str, str]:
    """Decrypt and return the secrets dict. Raises InvalidSecretPassword on wrong password."""
    if not _SECRETS_FILE.exists():
        return {}

    from cryptography.fernet import Fernet, InvalidToken
    with open(_SECRETS_FILE, "rb") as fp:
        salt_len  = struct.unpack(">H", fp.read(2))[0]
        salt      = fp.read(salt_len)
        encrypted = fp.read()

    fernet_key = _derive_key(password, salt)
    f = Fernet(fernet_key)
    try:
        payload = f.decrypt(encrypted)
    except InvalidToken:
        raise InvalidSecretPassword("Wrong password — cannot decrypt secrets vault")

    return json.loads(payload.decode("utf-8"))


def inject_secrets_to_env(password: str) -> int:
    """Load secrets from vault and inject into os.environ. Returns count injected."""
    try:
        secrets = load_secrets(password)
        for k, v in secrets.items():
            if v:
                os.environ[k] = v
        logger.info(f"Injected {len(secrets)} secrets from vault into environment")
        return len(secrets)
    except Exception as e:
        logger.warning(f"Could not load secrets vault: {e}")
        return 0


def update_secret(key: str, value: str, password: str) -> None:
    """Update a single secret in the vault."""
    secrets = load_secrets(password) if secrets_vault_exists() else {}
    secrets[key] = value
    save_secrets(secrets, password)


def migrate_env_to_vault(env_path: str, password: str) -> dict[str, str]:
    """
    Read VAULT_KEYS from .env file, store them in the secrets vault,
    and return the migrated key→value dict.
    """
    env_vals: dict[str, str] = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env_vals[k.strip()] = v.strip()

    to_migrate = {k: env_vals[k] for k in VAULT_KEYS if k in env_vals and env_vals[k]}
    if to_migrate:
        # Merge with existing vault
        existing = load_secrets(password) if secrets_vault_exists() else {}
        existing.update(to_migrate)
        save_secrets(existing, password)

    return to_migrate


class InvalidSecretPassword(Exception):
    pass
