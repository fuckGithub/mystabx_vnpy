"""SimNow CTP address constants. Never put account or password here."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SHANGHAI = timezone(timedelta(hours=8))

# Session-hours environment (use during exchange hours)
SIMNOW_SESSION = {
    "td": "182.254.243.31:30001",
    "md": "182.254.243.31:30011",
}

# 7x24 test environment (new accounts may need several trading days)
SIMNOW_24H = {
    "td": "182.254.243.31:40001",
    "md": "182.254.243.31:40011",
}

# Keys match CtpGateway.default_setting (Chinese field names) plus 柜台环境.
# This Mac vnpy_ctp build only ships the production API; SimNow uses that front.
# connect() reads: 用户名/密码/经纪商代码/交易服务器/行情服务器/产品名称/授权编码.
SIMNOW_CONNECT_DEFAULTS: dict[str, str] = {
    "经纪商代码": "9999",
    "交易服务器": SIMNOW_SESSION["td"],
    "行情服务器": SIMNOW_SESSION["md"],
    "产品名称": "simnow_client_test",
    "授权编码": "0000000000000000",
    "柜台环境": "实盘",
}

CONNECT_FILENAME = "connect_ctp.json"
SECRET_FIELDS = ("用户名", "密码")
MANUAL_FRONT_KEY = "手动指定前置"
CTP_SETTING_KEYS = (
    "用户名",
    "密码",
    "经纪商代码",
    "交易服务器",
    "行情服务器",
    "产品名称",
    "授权编码",
    "产品信息",
)
PUBLIC_CONNECT_KEYS = (
    "用户名",
    "经纪商代码",
    "交易服务器",
    "行情服务器",
    "产品名称",
    "授权编码",
    "柜台环境",
)

SIMNOW_HOST = "182.254.243.31"
SIMNOW_SESSION_PORTS = {"30001", "30011"}
SIMNOW_24H_PORTS = {"40001", "40011"}
SIMNOW_TD_PORTS = {"30001", "40001"}
SIMNOW_MD_PORTS = {"30011", "40011"}

# Auto front windows (Asia/Shanghai):
#   交易时段 — weekday day session 08:45–15:30, plus night session 20:45–02:35
#   (Sun evening through Fri night / Sat 02:35).
#   7×24 — midday 15:30–20:45, overnight after night close until morning,
#   and the weekend day gap. Session vs 7×24 is only which front to dial;
#   it is never a second gateway / account row.
AUTO_FRONT_WINDOWS = (
    "交易时段 08:45–15:30（周一至周五）与夜盘 20:45–02:35"
    "（周日夜盘至周五夜盘）；其余时间走 7×24。"
)


def merge_connect_settings(provided: dict[str, Any] | None) -> dict[str, Any]:
    """Fill omitted keys from SimNow defaults. Never overwrite user-provided values."""
    merged: dict[str, Any] = dict(SIMNOW_CONNECT_DEFAULTS)
    if not provided:
        return merged
    for key, value in provided.items():
        if value is None:
            continue
        merged[str(key)] = value
    return merged


def public_connect_settings(setting: dict[str, Any] | None) -> dict[str, str]:
    """Safe subset for list APIs — never includes 密码."""
    if not setting:
        return {}
    out: dict[str, str] = {}
    for key in PUBLIC_CONNECT_KEYS:
        value = setting.get(key)
        if value is None or value == "":
            continue
        out[key] = str(value)
    return out


def _truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "是"}


def auto_front_enabled(setting: dict[str, Any] | None) -> bool:
    """Auto-switch fronts unless the user checked 手动指定前置 / auto_front=false."""
    if not setting:
        return True
    if _truthy_flag(setting.get(MANUAL_FRONT_KEY)):
        return False
    if "auto_front" not in setting:
        return True
    value = setting.get("auto_front")
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def ctp_connect_payload(setting: dict[str, Any] | None) -> dict[str, Any]:
    """Pass only CtpGateway keys — drop 柜台环境 / auto_front / 手动指定前置."""
    if not setting:
        return {}
    return {key: setting[key] for key in CTP_SETTING_KEYS if key in setting}


def _shanghai_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(tz=SHANGHAI)
    if now.tzinfo is None:
        return now.replace(tzinfo=SHANGHAI)
    return now.astimezone(SHANGHAI)


def _in_session_window(now: datetime) -> bool:
    weekday = now.weekday()  # Mon=0 … Sun=6
    minutes = now.hour * 60 + now.minute
    day_open, day_close = 8 * 60 + 45, 15 * 60 + 30
    night_open, night_close = 20 * 60 + 45, 2 * 60 + 35
    if weekday < 5 and day_open <= minutes <= day_close:
        return True
    # Sun–Fri evening night session
    if minutes >= night_open and weekday in (6, 0, 1, 2, 3, 4):
        return True
    # Mon–Sat morning continuation of night session
    if minutes <= night_close and weekday in (0, 1, 2, 3, 4, 5):
        return True
    return False


def simnow_fronts_for_now(now: datetime | None = None) -> dict[str, str]:
    """Pick SimNow td/md fronts from Asia/Shanghai wall clock. See AUTO_FRONT_WINDOWS."""
    current = _shanghai_now(now)
    if _in_session_window(current):
        return {
            "交易服务器": SIMNOW_SESSION["td"],
            "行情服务器": SIMNOW_SESSION["md"],
            "env": "session",
            "label": "交易时段",
        }
    return {
        "交易服务器": SIMNOW_24H["td"],
        "行情服务器": SIMNOW_24H["md"],
        "env": "24x7",
        "label": "7×24",
    }


def normalize_front(value: Any) -> str:
    text = str(value or "").strip()
    for prefix in ("tcp://", "ssl://", "socks://", "socks5://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    return text


def _host_port(value: Any) -> tuple[str, str]:
    text = normalize_front(value)
    if ":" not in text:
        return text, ""
    host, port = text.rsplit(":", 1)
    return host.strip(), port.strip()


def is_known_simnow_front(value: Any, *, role: str | None = None) -> bool:
    host, port = _host_port(value)
    if host != SIMNOW_HOST or not port:
        return False
    if role == "td":
        return port in SIMNOW_TD_PORTS
    if role == "md":
        return port in SIMNOW_MD_PORTS
    return port in SIMNOW_SESSION_PORTS | SIMNOW_24H_PORTS


def classify_fronts(td: Any, md: Any) -> tuple[str, str]:
    td_n, md_n = normalize_front(td), normalize_front(md)
    if td_n == SIMNOW_SESSION["td"] and md_n == SIMNOW_SESSION["md"]:
        return "session", "交易时段"
    if td_n == SIMNOW_24H["td"] and md_n == SIMNOW_24H["md"]:
        return "24x7", "7×24"
    return "custom", "自定义"


def apply_simnow_auto_fronts(
    setting: dict[str, Any] | None,
    now: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve fronts for connect. Does not create another gateway.

    auto_front=false keeps saved addresses.
    Otherwise empty or well-known SimNow ports (30001/30011 vs 40001/40011)
    follow simnow_fronts_for_now(); truly custom IPs stay as saved.
    """
    out = dict(setting or {})
    chosen = simnow_fronts_for_now(now)
    auto = auto_front_enabled(out)
    td, md = out.get("交易服务器"), out.get("行情服务器")
    if auto:
        if not normalize_front(td) or is_known_simnow_front(td, role="td"):
            out["交易服务器"] = chosen["交易服务器"]
        if not normalize_front(md) or is_known_simnow_front(md, role="md"):
            out["行情服务器"] = chosen["行情服务器"]
    env, label = classify_fronts(out.get("交易服务器"), out.get("行情服务器"))
    if auto and env != "custom":
        env, label = chosen["env"], chosen["label"]
    meta = {
        "front_env": env,
        "front_label": label,
        "交易服务器": out.get("交易服务器"),
        "行情服务器": out.get("行情服务器"),
        "auto_front": auto,
    }
    return out, meta
