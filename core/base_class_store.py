"""Strategy base-class catalog (EliteCtaTemplate etc.) persisted on MySQL."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from core.db import StrategyBaseClass, available, get_session

logger = logging.getLogger("stabx.base_class_store")

_SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(tz=_SHANGHAI).replace(microsecond=0).isoformat()


_DEFAULTS: list[dict[str, Any]] = [
    {
        "class_name": "EliteCtaTemplate",
        "display_name": "Elite CTA 模板",
        "module": "core.strategy_shim",
        "import_stmt": (
            "from core.strategy_shim import EliteCtaTemplate, HistoryManager, "
            "sma, cross_over, cross_below"
        ),
        "description": "对标 VeighNa Elite：TargetPosTemplate + HistoryManager / on_history",
        "base_chain": "CtaTemplate → TargetPosTemplate → EliteCtaTemplate",
        "enabled": 1,
        "is_default": 1,
        "sort_order": 10,
    },
    {
        "class_name": "TargetPosTemplate",
        "display_name": "目标仓位模板",
        "module": "vnpy_ctastrategy",
        "import_stmt": "from vnpy_ctastrategy import TargetPosTemplate",
        "description": "开源 vnpy 目标仓位模板（set_target / execute_trading）",
        "base_chain": "CtaTemplate → TargetPosTemplate",
        "enabled": 1,
        "is_default": 0,
        "sort_order": 20,
    },
    {
        "class_name": "CtaTemplate",
        "display_name": "CTA 基础模板",
        "module": "vnpy_ctastrategy",
        "import_stmt": "from vnpy_ctastrategy import CtaTemplate",
        "description": "开源 vnpy CTA 基础模板",
        "base_chain": "CtaTemplate",
        "enabled": 1,
        "is_default": 0,
        "sort_order": 30,
    },
]


def _row_dict(row: StrategyBaseClass) -> dict[str, Any]:
    return {
        "class_name": row.class_name,
        "display_name": row.display_name,
        "module": row.module,
        "import_stmt": row.import_stmt,
        "description": row.description,
        "base_chain": row.base_chain,
        "enabled": bool(row.enabled),
        "is_default": bool(row.is_default),
        "sort_order": int(row.sort_order or 0),
        "updated_at": row.updated_at,
    }


def ensure_defaults() -> None:
    """Seed built-in base classes when missing."""
    if not available():
        return
    db = get_session()
    try:
        for item in _DEFAULTS:
            existing = db.get(StrategyBaseClass, item["class_name"])
            if existing is not None:
                continue
            db.add(
                StrategyBaseClass(
                    class_name=item["class_name"],
                    display_name=item["display_name"],
                    module=item["module"],
                    import_stmt=item["import_stmt"],
                    description=item["description"],
                    base_chain=item["base_chain"],
                    enabled=int(item["enabled"]),
                    is_default=int(item["is_default"]),
                    sort_order=int(item["sort_order"]),
                    updated_at=_now(),
                )
            )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("seed strategy_base_classes failed")
    finally:
        db.close()


def list_base_classes(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    ensure_defaults()
    if not available():
        return [
            {
                **x,
                "enabled": bool(x["enabled"]),
                "is_default": bool(x["is_default"]),
                "updated_at": None,
            }
            for x in _DEFAULTS
            if (not enabled_only or x["enabled"])
        ]
    db = get_session()
    try:
        rows = list(db.scalars(select(StrategyBaseClass).order_by(StrategyBaseClass.sort_order)).all())
        out = [_row_dict(r) for r in rows]
        if enabled_only:
            out = [r for r in out if r["enabled"]]
        return out
    finally:
        db.close()


def get_base_class(class_name: str) -> dict[str, Any] | None:
    name = (class_name or "").strip()
    if not name:
        return None
    for row in list_base_classes():
        if row["class_name"] == name:
            return row
    return None


def get_default_base_class() -> dict[str, Any]:
    rows = list_base_classes(enabled_only=True)
    for row in rows:
        if row.get("is_default"):
            return row
    if rows:
        return rows[0]
    return {
        **_DEFAULTS[0],
        "enabled": True,
        "is_default": True,
        "updated_at": None,
    }


def upsert_base_class(payload: dict[str, Any]) -> dict[str, Any]:
    if not available():
        raise RuntimeError("database is not initialized")
    ensure_defaults()
    name = str(payload.get("class_name") or "").strip()
    if not name:
        raise ValueError("class_name 不能为空")
    db = get_session()
    try:
        make_default = bool(payload.get("is_default"))
        if make_default:
            for other in db.scalars(select(StrategyBaseClass)).all():
                other.is_default = 0
        row = db.get(StrategyBaseClass, name)
        if row is None:
            row = StrategyBaseClass(class_name=name)
            db.add(row)
        row.display_name = str(payload.get("display_name") or name)
        row.module = str(payload.get("module") or "")
        row.import_stmt = str(payload.get("import_stmt") or "")
        row.description = str(payload.get("description") or "")
        row.base_chain = str(payload.get("base_chain") or "")
        if "enabled" in payload:
            row.enabled = 1 if payload.get("enabled") else 0
        if "is_default" in payload:
            row.is_default = 1 if make_default else 0
        if "sort_order" in payload and payload.get("sort_order") is not None:
            row.sort_order = int(payload["sort_order"])
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
        return _row_dict(row)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_base_class(class_name: str) -> None:
    if not available():
        raise RuntimeError("database is not initialized")
    name = (class_name or "").strip()
    db = get_session()
    try:
        row = db.get(StrategyBaseClass, name)
        if row is None:
            return
        if row.is_default:
            raise ValueError("不能删除默认基类")
        db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
