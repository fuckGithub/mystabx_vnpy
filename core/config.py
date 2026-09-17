"""Runtime settings. Secrets stay in env or .vntrader, never in the repo."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from mystabx.paths import PROJECT_ROOT, TRADER_FOLDER

KEYS_FILE = TRADER_FOLDER / "web_keys.json"


def _load_dotenv() -> None:
    """Load repo-root .env without overriding already-exported vars."""
    path = PROJECT_ROOT / ".env"
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


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
        self.jwt_secret = os.environ.get("STABX_JWT_SECRET", keys["jwt_secret"])
        self.jwt_algorithm = "HS256"
        self.access_expire_minutes = int(os.environ.get("STABX_ACCESS_MINUTES", "60"))
        self.refresh_expire_days = int(os.environ.get("STABX_REFRESH_DAYS", "7"))
        self.fernet_key = os.environ.get("STABX_FERNET_KEY", keys["fernet_key"])
        self.admin_username = os.environ.get("STABX_ADMIN_USERNAME", "admin")
        self.admin_password = os.environ.get("STABX_ADMIN_PASSWORD", "admin123")
        self.simnow_user = os.environ.get("STABX_SIMNOW_USER", "").strip()
        self.simnow_password = os.environ.get("STABX_SIMNOW_PASSWORD", "").strip()
        self.clickhouse_url = os.environ.get("STABX_CLICKHOUSE_URL", "http://127.0.0.1:8123")
        self.clickhouse_host = os.environ.get("STABX_CLICKHOUSE_HOST", "127.0.0.1")
        self.clickhouse_port = int(os.environ.get("STABX_CLICKHOUSE_PORT", "8123"))
        self.clickhouse_user = os.environ.get("STABX_CLICKHOUSE_USER", "default")
        self.clickhouse_password = os.environ.get("STABX_CLICKHOUSE_PASSWORD", "")
        self.clickhouse_database = os.environ.get("STABX_CLICKHOUSE_DATABASE", "mystabx_vnpy")
        self.clickhouse_tick_ttl_days = int(os.environ.get("STABX_CLICKHOUSE_TICK_TTL_DAYS", "10"))
        # MySQL（低频业务：订阅 / 通道日志 / 策略元数据与源码）。兼容 MYSQL_*（.env.ecs）。
        self.mysql_host = (
            os.environ.get("STABX_MYSQL_HOST") or os.environ.get("MYSQL_HOST") or ""
        ).strip()
        self.mysql_port = int(
            os.environ.get("STABX_MYSQL_PORT") or os.environ.get("MYSQL_PORT") or "3306"
        )
        self.mysql_user = (
            os.environ.get("STABX_MYSQL_USER") or os.environ.get("MYSQL_USER") or "root"
        ).strip()
        self.mysql_password = (
            os.environ.get("STABX_MYSQL_PASSWORD")
            or os.environ.get("MYSQL_PWD")
            or os.environ.get("MYSQL_PASSWORD")
            or ""
        )
        self.mysql_database = (
            os.environ.get("STABX_MYSQL_DATABASE")
            or os.environ.get("MYSQL_DB")
            or "mystabx_vnpy"
        ).strip() or "mystabx_vnpy"
        self.host = os.environ.get("STABX_HOST", "0.0.0.0")
        self.port = int(os.environ.get("STABX_PORT", "18080"))
        raw_origins = os.environ.get(
            "STABX_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
        self.cors_origins = [item.strip() for item in raw_origins.split(",") if item.strip()]
        # P8 metric alert thresholds (docs/09 §8.6)
        self.metric_t2t_p99_ms = float(os.environ.get("STABX_METRIC_T2T_P99_MS", "50"))
        self.metric_ch_queue_warn = int(os.environ.get("STABX_METRIC_CH_QUEUE_WARN", "40000"))
        self.metric_ws_pending_warn = int(os.environ.get("STABX_METRIC_WS_PENDING_WARN", "2000"))

    def metric_thresholds(self) -> dict[str, float]:
        return {
            "tick_to_trade_p99_ms": self.metric_t2t_p99_ms,
            "ch_queue_warn": float(self.metric_ch_queue_warn),
            "ws_pending_warn": float(self.metric_ws_pending_warn),
        }


settings = Settings()
