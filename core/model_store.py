"""Strategy model catalog + versioning (产品「模型」≠ CTA 基类).

Model = 双均线 / RUMI 等后端模板；Instance pins a model_version_id on save,
and live/backtest loads that pinned snapshot (not necessarily latest).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select

from core.db import (
    StrategyBacktestRun,
    StrategyInstance,
    StrategyInstanceVersion,
    StrategyModel,
    StrategyModelVersion,
    available,
    get_session,
)

logger = logging.getLogger("stabx.model_store")

_SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(tz=_SHANGHAI).replace(microsecond=0).isoformat()


def _dumps(obj: Any) -> str:
    return json.dumps(obj if obj is not None else {}, ensure_ascii=False)


def _loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_SEED_MODELS: list[dict[str, Any]] = [
    {
        "code": "dual_ma",
        "name": "双均线策略",
        "description": "快慢均线交叉；基于 DualMaTest / DoubleMaStrategy 模板。",
        "class_name": "DualMaTest",
        "parent_template": "CtaTemplate",
        "default_params": {"fast_window": 10, "slow_window": 20, "fixed_size": 1},
        "sort_order": 10,
    },
    {
        "code": "double_ma_target",
        "name": "双均线目标仓位",
        "description": "TargetPosTemplate 双均线：金叉/死叉设置目标仓位。",
        "class_name": "DoubleMaStrategy",
        "parent_template": "TargetPosTemplate",
        "default_params": {
            "fast_window": 10,
            "slow_window": 20,
            "fixed_size": 1,
            "gateway_name": "",
        },
        "sort_order": 20,
    },
    {
        "code": "rumi",
        "name": "RUMI均线偏差策略",
        "description": "EliteCtaTemplate + HistoryManager：均线偏差与持仓/止损。",
        "class_name": "RumiStrategy",
        "parent_template": "EliteCtaTemplate",
        "default_params": {
            "bar_window": 1,
            "bar_interval": "1m",
            "bar_buffer": 100,
            "fast_window": 3,
            "slow_window": 50,
            "rumi_window": 30,
            "max_holding": 100,
            "stop_percent": 0.03,
            "risk_window": 10,
            "risk_capital": 1_000_000,
            "price_add": 5,
            "fixed_size": 1,
            "gateway_name": "",
        },
        "sort_order": 30,
    },
    {
        "code": "boll_channel",
        "name": "布林带通道策略",
        "description": "布林带通道突破/回归；基于 BollChannelStrategy 模板。",
        "class_name": "BollChannelStrategy",
        "parent_template": "CtaTemplate",
        "default_params": {
            "boll_window": 18,
            "boll_dev": 3.4,
            "cci_window": 10,
            "atr_window": 30,
            "sl_multiplier": 5.2,
            "fixed_size": 1,
        },
        "sort_order": 40,
    },
]


def _model_dict(row: StrategyModel, *, latest: StrategyModelVersion | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "class_name": row.class_name,
        "parent_template": row.parent_template,
        "default_params": _loads(row.default_params),
        "template_source": row.template_source,
        "latest_version_id": row.latest_version_id,
        "enabled": bool(row.enabled),
        "sort_order": int(row.sort_order or 0),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if latest is not None:
        out["latest_version"] = _version_dict(latest)
    return out


def _version_dict(row: StrategyModelVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "model_id": row.model_id,
        "version_no": row.version_no,
        "label": row.label,
        "note": row.note,
        "params": _loads(row.params),
        "template_source": row.template_source,
        "created_by": row.created_by,
        "created_at": row.created_at,
    }


def _instance_version_dict(row: StrategyInstanceVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "strategy_name": row.strategy_name,
        "version_no": row.version_no,
        "model_id": row.model_id,
        "model_version_id": row.model_version_id,
        "runtime_params": _loads(row.runtime_params),
        "source_code": row.source_code,
        "note": row.note,
        "created_by": row.created_by,
        "created_at": row.created_at,
    }


def _backtest_dict(row: StrategyBacktestRun) -> dict[str, Any]:
    return {
        "id": row.id,
        "strategy_name": row.strategy_name,
        "instance_version_id": row.instance_version_id,
        "model_version_id": row.model_version_id,
        "run_params": _loads(row.run_params),
        "statistics": _loads(row.statistics),
        "status": row.status,
        "note": row.note,
        "created_at": row.created_at,
    }


def ensure_defaults() -> None:
    """Seed built-in models + v1 when missing."""
    if not available():
        return
    for item in _SEED_MODELS:
        existing = get_model_by_code(item["code"])
        if existing is not None:
            continue
        try:
            create_model(
                code=item["code"],
                name=item["name"],
                description=item["description"],
                class_name=item["class_name"],
                parent_template=item["parent_template"],
                default_params=item["default_params"],
                sort_order=item["sort_order"],
                note="系统预置 v1",
            )
        except Exception:
            logger.exception("seed model %s failed", item["code"])


def list_models(*, enabled_only: bool = False) -> list[dict[str, Any]]:
    ensure_defaults()
    if not available():
        return []
    db = get_session()
    try:
        q = select(StrategyModel).order_by(StrategyModel.sort_order, StrategyModel.id)
        rows = list(db.scalars(q).all())
        out = []
        for row in rows:
            if enabled_only and not row.enabled:
                continue
            latest = db.get(StrategyModelVersion, row.latest_version_id) if row.latest_version_id else None
            out.append(_model_dict(row, latest=latest))
        return out
    finally:
        db.close()


def get_model(model_id: int) -> dict[str, Any] | None:
    if not available() or not model_id:
        return None
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            return None
        latest = db.get(StrategyModelVersion, row.latest_version_id) if row.latest_version_id else None
        return _model_dict(row, latest=latest)
    finally:
        db.close()


def get_model_by_code(code: str) -> dict[str, Any] | None:
    if not available() or not (code or "").strip():
        return None
    db = get_session()
    try:
        row = db.scalar(select(StrategyModel).where(StrategyModel.code == code.strip()))
        if row is None:
            return None
        latest = db.get(StrategyModelVersion, row.latest_version_id) if row.latest_version_id else None
        return _model_dict(row, latest=latest)
    finally:
        db.close()


def get_model_version(version_id: int) -> dict[str, Any] | None:
    if not available() or not version_id:
        return None
    db = get_session()
    try:
        row = db.get(StrategyModelVersion, int(version_id))
        return _version_dict(row) if row else None
    finally:
        db.close()


def list_model_versions(model_id: int) -> list[dict[str, Any]]:
    if not available():
        return []
    db = get_session()
    try:
        rows = list(
            db.scalars(
                select(StrategyModelVersion)
                .where(StrategyModelVersion.model_id == int(model_id))
                .order_by(desc(StrategyModelVersion.version_no))
            ).all()
        )
        return [_version_dict(r) for r in rows]
    finally:
        db.close()


def create_model(
    *,
    code: str,
    name: str,
    description: str = "",
    class_name: str,
    parent_template: str = "EliteCtaTemplate",
    default_params: dict[str, Any] | None = None,
    template_source: str | None = None,
    sort_order: int = 100,
    enabled: bool = True,
    note: str = "初始版本",
    user_id: int | None = None,
) -> dict[str, Any]:
    if not available():
        raise RuntimeError("database is not initialized")
    code = (code or "").strip()
    class_name = (class_name or "").strip()
    if not code or not class_name:
        raise ValueError("code / class_name 不能为空")
    if get_model_by_code(code):
        raise ValueError(f"模型编码已存在: {code}")
    db = get_session()
    try:
        row = StrategyModel(
            code=code,
            name=(name or code).strip(),
            description=description or "",
            class_name=class_name,
            parent_template=(parent_template or "EliteCtaTemplate").strip(),
            default_params=_dumps(default_params or {}),
            template_source=template_source,
            enabled=1 if enabled else 0,
            sort_order=int(sort_order),
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(row)
        db.flush()
        ver = StrategyModelVersion(
            model_id=row.id,
            version_no=1,
            label="v1",
            note=note or "初始版本",
            params=_dumps(default_params or {}),
            template_source=template_source,
            created_by=user_id,
            created_at=_now(),
        )
        db.add(ver)
        db.flush()
        row.latest_version_id = ver.id
        db.commit()
        db.refresh(row)
        db.refresh(ver)
        return _model_dict(row, latest=ver)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def update_model_meta(
    model_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
    class_name: str | None = None,
    parent_template: str | None = None,
    enabled: bool | None = None,
    sort_order: int | None = None,
) -> dict[str, Any]:
    """Update non-versioned metadata only (params/source go through save_model_version)."""
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            raise ValueError("模型不存在")
        if name is not None:
            row.name = name.strip() or row.name
        if description is not None:
            row.description = description
        if class_name is not None and class_name.strip():
            row.class_name = class_name.strip()
        if parent_template is not None and parent_template.strip():
            row.parent_template = parent_template.strip()
        if enabled is not None:
            row.enabled = 1 if enabled else 0
        if sort_order is not None:
            row.sort_order = int(sort_order)
        row.updated_at = _now()
        db.commit()
        latest = db.get(StrategyModelVersion, row.latest_version_id) if row.latest_version_id else None
        return _model_dict(row, latest=latest)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_model_version(
    model_id: int,
    *,
    params: dict[str, Any] | None = None,
    template_source: str | None = None,
    label: str = "",
    note: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """Persist a new model version (param/source change) and advance latest pointer."""
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            raise ValueError("模型不存在")
        last = db.scalar(
            select(StrategyModelVersion)
            .where(StrategyModelVersion.model_id == row.id)
            .order_by(desc(StrategyModelVersion.version_no))
            .limit(1)
        )
        next_no = int(last.version_no) + 1 if last else 1
        snap_params = params if params is not None else _loads(row.default_params)
        snap_source = template_source if template_source is not None else row.template_source
        ver = StrategyModelVersion(
            model_id=row.id,
            version_no=next_no,
            label=(label or f"v{next_no}").strip(),
            note=note or "",
            params=_dumps(snap_params),
            template_source=snap_source,
            created_by=user_id,
            created_at=_now(),
        )
        db.add(ver)
        db.flush()
        row.default_params = _dumps(snap_params)
        if template_source is not None:
            row.template_source = template_source
        row.latest_version_id = ver.id
        row.updated_at = _now()
        db.commit()
        db.refresh(ver)
        return _version_dict(ver)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def delete_model(model_id: int) -> None:
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            return
        for ver in db.scalars(
            select(StrategyModelVersion).where(StrategyModelVersion.model_id == row.id)
        ).all():
            db.delete(ver)
        db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def resolve_pinned_setting(
    *,
    strategy_name: str,
    runtime_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge pinned model-version params ← instance runtime params ← override.

    Used by init/start/backtest so runs honor the pinned model version, not latest.
    """
    base: dict[str, Any] = {}
    if not available():
        return dict(runtime_override or {})
    db = get_session()
    try:
        inst = db.scalar(
            select(StrategyInstance).where(StrategyInstance.strategy_name == strategy_name.strip())
        )
        if inst is None:
            return dict(runtime_override or {})
        if inst.model_version_id:
            mv = db.get(StrategyModelVersion, inst.model_version_id)
            if mv is not None:
                base.update(_loads(mv.params))
        # Current instance version runtime params (if any)
        if inst.current_version_id:
            iv = db.get(StrategyInstanceVersion, inst.current_version_id)
            if iv is not None:
                base.update(_loads(iv.runtime_params))
        else:
            base.update(_loads(inst.params))
        if runtime_override:
            base.update(runtime_override)
        return base
    finally:
        db.close()


def pin_instance_model(
    strategy_name: str,
    *,
    model_id: int | None = None,
    model_version_id: int | None = None,
    clear: bool = False,
) -> dict[str, Any]:
    """Bind instance to a model; default pin = model's latest version."""
    if not available():
        raise RuntimeError("database is not initialized")
    name = strategy_name.strip()
    db = get_session()
    try:
        inst = db.scalar(select(StrategyInstance).where(StrategyInstance.strategy_name == name))
        if inst is None:
            raise ValueError(f"策略实例不存在: {name}")
        if clear or (model_id is None and model_version_id is None and clear):
            inst.model_id = None
            inst.model_version_id = None
            inst.updated_at = _now()
            db.commit()
            return {"strategy_name": name, "model_id": None, "model_version_id": None}

        # Version-only update (keep existing model)
        if model_id is None and model_version_id is not None:
            mv = db.get(StrategyModelVersion, int(model_version_id))
            if mv is None:
                raise ValueError("模型版本不存在")
            model = db.get(StrategyModel, mv.model_id)
            if model is None:
                raise ValueError("模型不存在")
            inst.model_id = model.id
            inst.model_version_id = mv.id
            if model.class_name:
                inst.strategy_class = model.class_name
            inst.updated_at = _now()
            db.commit()
            return {
                "strategy_name": name,
                "model_id": inst.model_id,
                "model_version_id": inst.model_version_id,
                "class_name": inst.strategy_class,
            }

        if model_id is None:
            raise ValueError("model_id 不能为空")

        model = db.get(StrategyModel, int(model_id))
        if model is None:
            raise ValueError("模型不存在")
        vid = model_version_id or model.latest_version_id
        if vid:
            mv = db.get(StrategyModelVersion, int(vid))
            if mv is None or mv.model_id != model.id:
                raise ValueError("模型版本不存在或不属于该模型")
        inst.model_id = model.id
        inst.model_version_id = int(vid) if vid else None
        if model.class_name:
            inst.strategy_class = model.class_name
        inst.updated_at = _now()
        db.commit()
        return {
            "strategy_name": name,
            "model_id": inst.model_id,
            "model_version_id": inst.model_version_id,
            "class_name": inst.strategy_class,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_instance_version(
    strategy_name: str,
    *,
    runtime_params: dict[str, Any] | None = None,
    source_code: str | None = None,
    model_version_id: int | None = None,
    model_id: int | None = None,
    note: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """Create a new instance version and update current_version_id + pin."""
    if not available():
        raise RuntimeError("database is not initialized")
    name = strategy_name.strip()
    db = get_session()
    try:
        inst = db.scalar(select(StrategyInstance).where(StrategyInstance.strategy_name == name))
        if inst is None:
            raise ValueError(f"策略实例不存在: {name}")
        last = db.scalar(
            select(StrategyInstanceVersion)
            .where(StrategyInstanceVersion.strategy_name == name)
            .order_by(desc(StrategyInstanceVersion.version_no))
            .limit(1)
        )
        next_no = int(last.version_no) + 1 if last else 1
        mid = model_id if model_id is not None else inst.model_id
        mvid = model_version_id if model_version_id is not None else inst.model_version_id
        params = runtime_params if runtime_params is not None else _loads(inst.params)
        code = source_code if source_code is not None else inst.source_code
        ver = StrategyInstanceVersion(
            strategy_name=name,
            version_no=next_no,
            model_id=mid,
            model_version_id=mvid,
            runtime_params=_dumps(params),
            source_code=code,
            note=note or "",
            created_by=user_id,
            created_at=_now(),
        )
        db.add(ver)
        db.flush()
        inst.current_version_id = ver.id
        if mid is not None:
            inst.model_id = mid
        if mvid is not None:
            inst.model_version_id = mvid
        if runtime_params is not None:
            inst.params = _dumps(runtime_params)
        if source_code is not None:
            inst.source_code = source_code
        inst.updated_at = _now()
        db.commit()
        db.refresh(ver)
        return _instance_version_dict(ver)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_instance_versions(strategy_name: str) -> list[dict[str, Any]]:
    if not available():
        return []
    db = get_session()
    try:
        rows = list(
            db.scalars(
                select(StrategyInstanceVersion)
                .where(StrategyInstanceVersion.strategy_name == strategy_name.strip())
                .order_by(desc(StrategyInstanceVersion.version_no))
            ).all()
        )
        return [_instance_version_dict(r) for r in rows]
    finally:
        db.close()


def get_instance_version(version_id: int) -> dict[str, Any] | None:
    if not available() or not version_id:
        return None
    db = get_session()
    try:
        row = db.get(StrategyInstanceVersion, int(version_id))
        return _instance_version_dict(row) if row else None
    finally:
        db.close()


def record_backtest_run(
    *,
    strategy_name: str,
    instance_version_id: int | None = None,
    model_version_id: int | None = None,
    run_params: dict[str, Any] | None = None,
    statistics: dict[str, Any] | None = None,
    status: str = "done",
    note: str = "",
) -> dict[str, Any]:
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        name = strategy_name.strip()
        inst = db.scalar(select(StrategyInstance).where(StrategyInstance.strategy_name == name))
        iv = instance_version_id
        mv = model_version_id
        if inst is not None:
            if iv is None:
                iv = inst.current_version_id
            if mv is None:
                mv = inst.model_version_id
        row = StrategyBacktestRun(
            strategy_name=name,
            instance_version_id=iv,
            model_version_id=mv,
            run_params=_dumps(run_params or {}),
            statistics=_dumps(statistics or {}),
            status=status or "done",
            note=note or "",
            created_at=_now(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _backtest_dict(row)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_backtest_runs(
    strategy_name: str,
    *,
    instance_version_id: int | None = None,
) -> list[dict[str, Any]]:
    if not available():
        return []
    db = get_session()
    try:
        q = select(StrategyBacktestRun).where(
            StrategyBacktestRun.strategy_name == strategy_name.strip()
        )
        if instance_version_id is not None:
            q = q.where(StrategyBacktestRun.instance_version_id == int(instance_version_id))
        rows = list(db.scalars(q.order_by(desc(StrategyBacktestRun.id))).all())
        return [_backtest_dict(r) for r in rows]
    finally:
        db.close()


def instance_binding(strategy_name: str) -> dict[str, Any]:
    """Return model pin + current version summary for an instance."""
    if not available():
        return {}
    db = get_session()
    try:
        inst = db.scalar(
            select(StrategyInstance).where(StrategyInstance.strategy_name == strategy_name.strip())
        )
        if inst is None:
            return {}
        model = db.get(StrategyModel, inst.model_id) if inst.model_id else None
        mv = db.get(StrategyModelVersion, inst.model_version_id) if inst.model_version_id else None
        iv = db.get(StrategyInstanceVersion, inst.current_version_id) if inst.current_version_id else None
        return {
            "strategy_name": inst.strategy_name,
            "model_id": inst.model_id,
            "model_version_id": inst.model_version_id,
            "current_version_id": inst.current_version_id,
            "model": _model_dict(model) if model else None,
            "model_version": _version_dict(mv) if mv else None,
            "current_version": _instance_version_dict(iv) if iv else None,
        }
    finally:
        db.close()
