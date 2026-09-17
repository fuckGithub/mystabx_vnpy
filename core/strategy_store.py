"""Strategy class / instance metadata + source code persistence on MySQL."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from core.db import StrategyClass, StrategyInstance, available, get_session
from core.strategy_names import strategy_display_name

logger = logging.getLogger("stabx.strategy_store")

_SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(tz=_SHANGHAI).replace(microsecond=0).isoformat()


def upsert_strategy_class(
    *,
    class_name: str,
    display_name: str = "",
    file_name: str = "",
    file_path: str = "",
    module: str = "",
    source_code: str | None = None,
    editable: bool = True,
) -> None:
    if not available() or not class_name.strip():
        return
    name = class_name.strip()
    db = get_session()
    try:
        row = db.get(StrategyClass, name)
        if row is None:
            row = StrategyClass(
                class_name=name,
                display_name=display_name or strategy_display_name(name),
                file_name=file_name,
                file_path=file_path,
                module=module,
                source_code=source_code,
                editable=1 if editable else 0,
                updated_at=_now(),
            )
            db.add(row)
        else:
            if display_name:
                row.display_name = display_name
            if file_name:
                row.file_name = file_name
            if file_path:
                row.file_path = file_path
            if module:
                row.module = module
            if source_code is not None:
                row.source_code = source_code
            row.editable = 1 if editable else 0
            row.updated_at = _now()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("upsert strategy_class failed %s", name)
    finally:
        db.close()


def get_strategy_source(class_name: str) -> dict[str, Any] | None:
    if not available():
        return None
    db = get_session()
    try:
        row = db.get(StrategyClass, class_name.strip())
        if row is None or row.source_code is None:
            return None
        return {
            "class_name": row.class_name,
            "display_name": row.display_name,
            "file_name": row.file_name,
            "file_path": row.file_path,
            "module": row.module,
            "editable": bool(row.editable),
            "updated_at": row.updated_at,
            "content": row.source_code,
        }
    finally:
        db.close()


def save_strategy_source(
    *,
    class_name: str,
    content: str,
    file_name: str = "",
    file_path: str = "",
    module: str = "",
    editable: bool = True,
) -> dict[str, Any]:
    """Persist source to MySQL (caller still writes disk for CTA load)."""
    upsert_strategy_class(
        class_name=class_name,
        display_name=strategy_display_name(class_name),
        file_name=file_name,
        file_path=file_path,
        module=module,
        source_code=content,
        editable=editable,
    )
    return {
        "class_name": class_name,
        "file_path": file_path,
        "updated_at": _now(),
        "store": "mysql" if available() else "none",
    }


def sync_class_from_file(
    *,
    class_name: str,
    path: Path,
    module: str = "",
    editable: bool = True,
    project_root: Path | None = None,
) -> None:
    """Backfill MySQL from disk when row missing or empty source."""
    if not available() or not path.is_file():
        return
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return
    rel = str(path)
    if project_root is not None:
        try:
            rel = str(path.resolve().relative_to(project_root.resolve()))
        except ValueError:
            rel = str(path)
    db = get_session()
    try:
        row = db.get(StrategyClass, class_name.strip())
        if row is not None and (row.source_code or "").strip():
            return
    finally:
        db.close()
    upsert_strategy_class(
        class_name=class_name,
        display_name=strategy_display_name(class_name),
        file_name=path.name,
        file_path=rel,
        module=module,
        source_code=content,
        editable=editable,
    )


def materialize_source_to_file(class_name: str, path: Path) -> bool:
    """Write MySQL source to disk so CtaEngine can import it."""
    meta = get_strategy_source(class_name)
    if not meta:
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(meta["content"]), encoding="utf-8")
        return True
    except OSError:
        logger.exception("materialize strategy source failed %s → %s", class_name, path)
        return False


def upsert_instance_meta(
    *,
    strategy_name: str,
    strategy_class: str,
    vt_symbol: str,
    params: dict | None = None,
    status: str = "stopped",
    user_id: int | None = None,
    gateway_name: str | None = None,
) -> None:
    if not available() or not strategy_name.strip():
        return
    name = strategy_name.strip()
    db = get_session()
    try:
        row = db.scalar(select(StrategyInstance).where(StrategyInstance.strategy_name == name))
        payload = json.dumps(params or {}, ensure_ascii=False) if params is not None else None
        if row is None:
            db.add(
                StrategyInstance(
                    user_id=user_id,
                    gateway_name=gateway_name,
                    strategy_class=strategy_class,
                    strategy_name=name,
                    vt_symbol=vt_symbol,
                    params=payload,
                    status=status,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
        else:
            row.strategy_class = strategy_class
            row.vt_symbol = vt_symbol
            if params is not None:
                row.params = payload
            row.status = status
            if user_id is not None:
                row.user_id = user_id
            if gateway_name is not None:
                row.gateway_name = gateway_name
            row.updated_at = _now()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("upsert strategy_instance failed %s", name)
    finally:
        db.close()


def delete_instance_meta(strategy_name: str) -> None:
    if not available():
        return
    db = get_session()
    try:
        db.execute(
            delete(StrategyInstance).where(StrategyInstance.strategy_name == strategy_name.strip())
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("delete strategy_instance failed %s", strategy_name)
    finally:
        db.close()


def rename_instance_meta(old_name: str, new_name: str) -> None:
    if not available():
        return
    db = get_session()
    try:
        row = db.scalar(
            select(StrategyInstance).where(StrategyInstance.strategy_name == old_name.strip())
        )
        if row is None:
            return
        row.strategy_name = new_name.strip()
        row.updated_at = _now()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("rename strategy_instance failed %s → %s", old_name, new_name)
    finally:
        db.close()
