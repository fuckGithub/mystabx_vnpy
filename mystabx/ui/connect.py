"""Prefill SimNow addresses into connect_ctp.json without writing secrets."""

from __future__ import annotations

import json
from pathlib import Path

from mystabx.config.simnow import (
    CONNECT_FILENAME,
    SECRET_FIELDS,
    SIMNOW_CONNECT_DEFAULTS,
)


def ensure_simnow_connect_template() -> Path:
    """Write or merge non-secret SimNow fields into the local connect file.

    Password and username are never taken from the repo. Existing secrets
    in the local file are left untouched.
    """
    from vnpy.trader.utility import get_file_path

    path = get_file_path(CONNECT_FILENAME)
    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            existing = {}

    merged = dict(existing)
    changed = False
    for key, value in SIMNOW_CONNECT_DEFAULTS.items():
        if key in SECRET_FIELDS:
            continue
        current = merged.get(key, "")
        if current in ("", None):
            merged[key] = value
            changed = True

    for secret in SECRET_FIELDS:
        merged.setdefault(secret, "")

    if changed or not path.exists():
        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
    return path
