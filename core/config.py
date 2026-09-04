"""Runtime settings. Secrets stay in env or .vntrader, never in the repo."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from mystabx.paths import PROJECT_ROOT, TRADER_FOLDER

KEYS_FILE = TRADER_FOLDER / "web_keys.json"


def _load_or_create_keys() -> dict[str, str]:
    TRADER_FOLDER.mkdir(parents=True, exist_ok=True)
    if KEYS_FILE.exists():
        try:
            data = json.loads(KEYS_FILE.read_text(encoding="utf-8") or "{}")
            if data.get("jwt_secret") and data.get("fernet_key"):
                return data
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    from cryptography.fernet import Fernet

    data["jwt_secret"] = data.get("jwt_secret") or secrets.token_urlsafe(48)
    data["fernet_key"] = data.get("fernet_key") or Fernet.generate_key().decode()
    KEYS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(KEYS_FILE, 0o600)
    except OSError:
        pass
    return data


class Settings:
    def __init__(self) -> None:
        keys = _load_or_create_keys()
        self.project_root = PROJECT_ROOT
        self.sqlite_path = Path(
            os.environ.get("STABX_SQLITE_PATH", str(TRADER_FOLDER / "stabx_web.db"))
        )
        self.jwt_secret = os.environ.get("STABX_JWT_SECRET", keys["jwt_secret"])
        self.jwt_algorithm = "HS256"
        self.access_expire_minutes = int(os.environ.get("STABX_ACCESS_MINUTES", "60"))
        self.refresh_expire_days = int(os.environ.get("STABX_REFRESH_DAYS", "7"))
        self.fernet_key = os.environ.get("STABX_FERNET_KEY", keys["fernet_key"])
        self.admin_username = os.environ.get("STABX_ADMIN_USERNAME", "admin")
        self.admin_password = os.environ.get("STABX_ADMIN_PASSWORD", "admin123")
        self.clickhouse_url = os.environ.get("STABX_CLICKHOUSE_URL", "http://127.0.0.1:8123")
        self.host = os.environ.get("STABX_HOST", "0.0.0.0")
        self.port = int(os.environ.get("STABX_PORT", "8000"))
        raw_origins = os.environ.get(
            "STABX_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
        self.cors_origins = [item.strip() for item in raw_origins.split(",") if item.strip()]


settings = Settings()
