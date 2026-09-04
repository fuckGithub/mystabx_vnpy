"""Fernet helpers for account connect_settings (docs/02 §6)."""

from __future__ import annotations

import json

from cryptography.fernet import Fernet

from core.config import settings

_fernet: Fernet | None = None


def _client() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.fernet_key.encode())
    return _fernet


def encrypt(connect_settings: dict) -> str:
    return _client().encrypt(json.dumps(connect_settings, ensure_ascii=False).encode()).decode()


def decrypt(ciphertext: str) -> dict:
    return json.loads(_client().decrypt(ciphertext.encode()))
