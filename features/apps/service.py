"""Helpers: resolve vnpy app engines and serialize honest status / light payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from core.runtime import runtime
from features.apps.catalog import CATALOG, CATALOG_BY_KEY
from mystabx.config.apps import probe_package


def _registry() -> dict[str, dict[str, Any]]:
    raw = runtime.extra.get("apps")
    return raw if isinstance(raw, dict) else {}


def get_engine(app_name: str):
    if runtime.main_engine is None:
        raise HTTPException(status_code=503, detail="engine not started")
    engine = runtime.me.get_engine(app_name)
    if engine is None:
        raise HTTPException(status_code=503, detail=f"app engine not loaded: {app_name}")
    return engine


def try_engine(app_name: str):
    if not app_name or runtime.main_engine is None:
        return None
    # Prefer registry / apps map to avoid MainEngine "找不到引擎" log noise.
    if app_name not in runtime.me.engines and app_name not in runtime.me.apps:
        return None
    return runtime.me.get_engine(app_name)


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def status_for(key: str) -> dict[str, Any]:
    meta = CATALOG_BY_KEY[key]
    reg = _registry().get(key) or {}
    package = meta["package"]
    importable, import_error = probe_package(package)

    if meta["wiring"] == "na":
        state = "na"
    elif not importable:
        state = "missing"
    elif reg.get("loaded"):
        state = "loaded"
    elif reg.get("selected") is False:
        state = "disabled"
    else:
        state = "failed" if reg.get("error") else "missing"

    return {
        "key": key,
        "title": meta["title"],
        "package": package,
        "class_name": meta["class_name"],
        "app_name": meta.get("app_name") or reg.get("app_name"),
        "wiring": meta["wiring"],
        "summary": meta["summary"],
        "state": state,
        "loaded": bool(reg.get("loaded")),
        "importable": importable,
        "import_error": import_error,
        "load_error": reg.get("error"),
        "post_init_ok": reg.get("post_init_ok"),
        "link_path": meta.get("link_path"),
        "platform_note": meta.get("platform_note"),
        "engine_present": bool(reg.get("loaded")) and try_engine(meta.get("app_name") or "") is not None,
    }


def list_statuses() -> list[dict[str, Any]]:
    return [status_for(item["key"]) for item in CATALOG]


def require_loaded(key: str):
    st = status_for(key)
    if st["wiring"] == "na":
        raise HTTPException(status_code=400, detail=st["summary"])
    if not st["loaded"]:
        raise HTTPException(
            status_code=503,
            detail=f"{st['title']} 未加载: {st.get('load_error') or st.get('import_error') or st['state']}",
        )
    return get_engine(st["app_name"])


def strategy_row(strategy) -> dict[str, Any]:
    data = strategy.get_data() if hasattr(strategy, "get_data") else {}
    return {
        **data,
        "inited": bool(getattr(strategy, "inited", False)),
        "trading": bool(getattr(strategy, "trading", False)),
        "pos": getattr(strategy, "pos", None),
    }


def bar_overview_row(item) -> dict[str, Any]:
    exchange = getattr(item, "exchange", None)
    interval = getattr(item, "interval", None)
    start = getattr(item, "start", None)
    end = getattr(item, "end", None)
    return {
        "symbol": getattr(item, "symbol", None),
        "exchange": exchange.value if hasattr(exchange, "value") else str(exchange) if exchange else None,
        "interval": interval.value if hasattr(interval, "value") else str(interval) if interval else None,
        "count": getattr(item, "count", None),
        "start": start.isoformat() if isinstance(start, datetime) else start,
        "end": end.isoformat() if isinstance(end, datetime) else end,
    }


def parse_dt(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid datetime: {value}") from exc
