"""Build-time only: decrypt legacy Fernet tradeverse_timeline.enc.

Not used at participant runtime. Participant builds embed tradeverse_timeline.pkg
in the PyInstaller backend binary instead.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
TIMELINE_ENC = SEED_DIR / "tradeverse_timeline.enc"


def decrypt_timeline_bytes(key: str, blob: bytes) -> dict[str, Any]:
    """Decrypt Fernet-encrypted timeline bytes to a JSON object."""
    if not key.strip():
        raise ValueError("TIMELINE_DECRYPT_KEY is empty")
    fernet = Fernet(key.strip().encode("utf-8"))
    try:
        decrypted = fernet.decrypt(blob)
    except InvalidToken as exc:
        raise ValueError("invalid TIMELINE_DECRYPT_KEY — cannot decrypt timeline") from exc
    data = json.loads(decrypted.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("decrypted timeline is not a JSON object")
    return data


def decrypt_timeline_file(key: str, path: Path | None = None) -> dict[str, Any]:
    enc_path = path or TIMELINE_ENC
    if not enc_path.is_file():
        raise FileNotFoundError(f"encrypted timeline not found: {enc_path}")
    return decrypt_timeline_bytes(key, enc_path.read_bytes())
