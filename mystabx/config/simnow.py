"""SimNow CTP address constants. Never put account or password here.

Backend single source of truth for fronts / connect defaults.
Frontend offline mirrors live in ``ui/config/simnow.ts`` (FALLBACK_*);
prefer ``GET /api/admin/connect-defaults`` at runtime so UI matches this module.
"""
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
# Never put InvestorID or password here — those come from STABX_SIMNOW_* env.
SIMNOW_ACCOUNT_NAME = "SimNow"
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


def _front_pair(env: str) -> dict[str, str]:
    if env == "session":
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


def simnow_fronts_for_now(now: datetime | None = None) -> dict[str, str]:
    """Pick SimNow td/md fronts from Asia/Shanghai wall clock. See AUTO_FRONT_WINDOWS."""
    current = _shanghai_now(now)
    if _in_session_window(current):
        return _front_pair("session")
    return _front_pair("24x7")


def simnow_front_candidates(now: datetime | None = None) -> list[dict[str, str]]:
    """Preferred (by Shanghai session) first, then the other known SimNow pair."""
    preferred = simnow_fronts_for_now(now)
    alternate = _front_pair("24x7" if preferred["env"] == "session" else "session")
    return [preferred, alternate]


def probe_simnow_pair(
    td: Any,
    md: Any,
    *,
    timeout: float = 3.0,
) -> dict[str, Any]:
    """TCP-probe a trade+md pair; ok only when both fronts accept connections."""
    trade = probe_tcp_front(str(td or ""), timeout=timeout)
    market = probe_tcp_front(str(md or ""), timeout=timeout)
    return {
        "ok": bool(trade.get("ok") and market.get("ok")),
        "trade": trade,
        "market": market,
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


def probe_tcp_front(address: str, timeout: float = 3.0) -> dict[str, Any]:
    """TCP reachability of a CTP front `host:port`. Does not log in."""
    import socket
    import time

    host, port = _host_port(address)
    display = normalize_front(address) or str(address or "").strip()
    if not host or not port:
        return {"ok": False, "address": display, "error": "地址格式无效，需 host:port"}
    try:
        port_n = int(port)
    except ValueError:
        return {"ok": False, "address": display, "error": "端口无效"}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    started = time.perf_counter()
    try:
        sock.connect((host, port_n))
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {"ok": True, "address": f"{host}:{port_n}", "latency_ms": latency_ms}
    except OSError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": False,
            "address": f"{host}:{port_n}",
            "latency_ms": latency_ms,
            "error": str(exc) or "连接失败",
        }
    finally:
        sock.close()


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
    *,
    probe: bool = False,
    probe_timeout: float = 3.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve fronts for connect. Does not create another gateway.

    auto_front=false / 手动指定前置 keeps saved addresses (never auto-fallback).
    Otherwise empty or well-known SimNow ports (30001/30011 vs 40001/40011)
    follow simnow_fronts_for_now(); truly custom IPs stay as saved.

    When probe=True and auto is on for known SimNow fronts: TCP-probe the
    time-preferred pair first, then the alternate pair; use the first fully
    reachable (trade+md) pair. meta.reachable is False only when every
    candidate fails (preferred addresses are still written for diagnostics).
    """
    out = dict(setting or {})
    preferred = simnow_fronts_for_now(now)
    auto = auto_front_enabled(out)
    td, md = out.get("交易服务器"), out.get("行情服务器")
    can_auto_pair = auto and (
        (not normalize_front(td) or is_known_simnow_front(td, role="td"))
        and (not normalize_front(md) or is_known_simnow_front(md, role="md"))
    )
    fallback_used = False
    preferred_label = preferred["label"]
    probe_trade: dict[str, Any] | None = None
    probe_market: dict[str, Any] | None = None
    reachable: bool | None = None
    tried: list[dict[str, Any]] = []

    if can_auto_pair:
        out["交易服务器"] = preferred["交易服务器"]
        out["行情服务器"] = preferred["行情服务器"]
        if probe:
            selected: dict[str, str] | None = None
            for candidate in simnow_front_candidates(now):
                result = probe_simnow_pair(
                    candidate["交易服务器"],
                    candidate["行情服务器"],
                    timeout=probe_timeout,
                )
                tried.append(
                    {
                        "env": candidate["env"],
                        "label": candidate["label"],
                        "交易服务器": candidate["交易服务器"],
                        "行情服务器": candidate["行情服务器"],
                        "ok": result["ok"],
                        "trade": result["trade"],
                        "market": result["market"],
                    }
                )
                if result["ok"]:
                    selected = candidate
                    probe_trade = result["trade"]
                    probe_market = result["market"]
                    break
            if selected is not None:
                out["交易服务器"] = selected["交易服务器"]
                out["行情服务器"] = selected["行情服务器"]
                fallback_used = selected["env"] != preferred["env"]
                reachable = True
            else:
                # Keep time-preferred fronts for error display; all probes failed.
                last = tried[-1] if tried else None
                if last:
                    probe_trade = last.get("trade")
                    probe_market = last.get("market")
                reachable = False
    elif auto:
        if not normalize_front(td) or is_known_simnow_front(td, role="td"):
            out["交易服务器"] = preferred["交易服务器"]
        if not normalize_front(md) or is_known_simnow_front(md, role="md"):
            out["行情服务器"] = preferred["行情服务器"]

    if probe and not can_auto_pair:
        # Manual / custom: probe saved fronts only — never switch pairs.
        result = probe_simnow_pair(
            out.get("交易服务器"),
            out.get("行情服务器"),
            timeout=probe_timeout,
        )
        probe_trade = result["trade"]
        probe_market = result["market"]
        reachable = result["ok"]
        tried.append(
            {
                "env": "manual" if not auto else "custom",
                "label": "手动指定" if not auto else "自定义",
                "交易服务器": out.get("交易服务器"),
                "行情服务器": out.get("行情服务器"),
                "ok": result["ok"],
                "trade": result["trade"],
                "market": result["market"],
            }
        )

    env, label = classify_fronts(out.get("交易服务器"), out.get("行情服务器"))
    if can_auto_pair and env != "custom":
        if fallback_used:
            label = f"{label}（自动回退）"
        elif reachable is not False:
            env, label = preferred["env"], preferred["label"]
    meta: dict[str, Any] = {
        "front_env": env,
        "front_label": label,
        "交易服务器": out.get("交易服务器"),
        "行情服务器": out.get("行情服务器"),
        "auto_front": auto,
        "front_preferred": preferred_label,
        "front_fallback": fallback_used,
    }
    if probe:
        meta["reachable"] = bool(reachable)
        meta["probe_trade"] = probe_trade
        meta["probe_market"] = probe_market
        meta["probe_tried"] = tried
    return out, meta
