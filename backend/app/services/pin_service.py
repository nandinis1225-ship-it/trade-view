"""Local event PIN hashing and verification — no network required."""

from __future__ import annotations

import hashlib
import hmac
import secrets

from app.core.config import get_settings


def generate_pin_verifier(pin: str) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for storage in participant .env."""
    salt = secrets.token_hex(16)
    digest = _hash_pin(pin.strip(), salt)
    return salt, digest


def _hash_pin(pin: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 120_000).hex()


def verify_event_pin(pin: str) -> bool:
    settings = get_settings()
    candidate = pin.strip()
    if not candidate:
        return False

    hash_hex = (settings.event_pin_hash or "").strip()
    salt_hex = (settings.event_pin_salt or "").strip()
    if hash_hex and salt_hex:
        expected = _hash_pin(candidate, salt_hex)
        return hmac.compare_digest(expected, hash_hex)

    expected_plain = (settings.event_pin or "").strip()
    if expected_plain:
        return hmac.compare_digest(candidate, expected_plain)

    return False
