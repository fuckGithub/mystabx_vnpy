"""Strategy models = DB-backed CTA classes (models-only product UX).

Each STRATEGY_TITLE_ZH class is one model. Ordinary save updates the working
draft (code / params / 合约 / 基础配置). Version number bumps only on explicit
「保存为新版本」. Run loads draft or a selected version from MySQL, compiles via
strategy_loader, then persists results onto the model detail.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
from core.strategy_names import STRATEGY_TITLE_ZH, strategy_title_zh
from mystabx.paths import PROJECT_ROOT

logger = logging.getLogger("stabx.model_store")

_SHANGHAI = timezone(timedelta(hours=8))
_DEFAULT_VT_SYMBOL = "rb2501.SHFE"
_DEFAULT_BASE_CONFIG: dict[str, Any] = {
    "interval": "1m",
    "capital": 1_000_000,
    "rate": 0.0,
    "slippage": 0.0,
    "size": 10,
    "pricetick": 1.0,
}

_VT_SPLIT = re.compile(r"[,，;；\s]+")


def parse_vt_symbols(value: Any) -> list[str]:
    """Normalize model/instance contract binding to a de-duplicated vt_symbol list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_parts = [str(x) for x in value]
    else:
        text = str(value).strip()
        if not text:
            return []
        raw_parts = _VT_SPLIT.split(text)
    out: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        sym = part.strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def format_vt_symbols(value: Any) -> str:
    return ",".join(parse_vt_symbols(value))


def primary_vt_symbol(value: Any, *, default: str = _DEFAULT_VT_SYMBOL) -> str:
    symbols = parse_vt_symbols(value)
    return symbols[0] if symbols else default



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


def _loads_any(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _code_for_class(class_name: str) -> str:
    return _camel_to_snake(class_name)


# Hard-coded defaults when class annotations are awkward to parse.
_CLASS_DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    "TurtleSignalStrategy": {
        "entry_window": 20,
        "exit_window": 10,
        "atr_window": 20,
        "fixed_size": 1,
    },
    "DualThrustStrategy": {"k1": 0.4, "k2": 0.6, "fixed_size": 1},
    "BollChannelStrategy": {
        "boll_window": 18,
        "boll_dev": 3.4,
        "cci_window": 10,
        "atr_window": 30,
        "sl_multiplier": 5.2,
        "fixed_size": 1,
    },
    "AtrRsiStrategy": {
        "atr_length": 22,
        "atr_ma_length": 10,
        "rsi_length": 5,
        "rsi_entry": 16,
        "trailing_percent": 0.8,
        "fixed_size": 1,
    },
    "KingKeltnerStrategy": {
        "kk_length": 11,
        "kk_dev": 1.6,
        "trailing_percent": 0.8,
        "fixed_size": 1,
    },
    "MultiSignalStrategy": {
        "rsi_window": 14,
        "rsi_level": 20,
        "cci_window": 30,
        "cci_level": 10,
        "fast_window": 5,
        "slow_window": 20,
    },
    "MultiTimeframeStrategy": {
        "rsi_signal": 20,
        "rsi_window": 14,
        "fast_window": 5,
        "slow_window": 20,
        "fixed_size": 1,
    },
    "TestStrategy": {"test_trigger": 10},
    "DoubleMaStrategy": {
        "fast_window": 10,
        "slow_window": 20,
        "fixed_size": 1,
        "gateway_name": "",
    },
    "DualMaTest": {"fast_window": 10, "slow_window": 20, "fixed_size": 1},
    "RumiStrategy": {
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
}

_CLASS_PARENT: dict[str, str] = {
    "TurtleSignalStrategy": "CtaTemplate",
    "DualThrustStrategy": "CtaTemplate",
    "BollChannelStrategy": "CtaTemplate",
    "AtrRsiStrategy": "CtaTemplate",
    "KingKeltnerStrategy": "CtaTemplate",
    "MultiSignalStrategy": "TargetPosTemplate",
    "MultiTimeframeStrategy": "CtaTemplate",
    "TestStrategy": "CtaTemplate",
    "DoubleMaStrategy": "TargetPosTemplate",
    "DualMaTest": "CtaTemplate",
    "RumiStrategy": "EliteCtaTemplate",
}


def _resolve_seed_source_path(class_name: str) -> Path | None:
    snake = _camel_to_snake(class_name)
    candidates = [
        PROJECT_ROOT / "strategies" / f"{snake}.py",
        PROJECT_ROOT
        / ".venv"
        / "lib"
        / "python3.13"
        / "site-packages"
        / "vnpy_ctastrategy"
        / "strategies"
        / f"{snake}.py",
    ]
    try:
        import vnpy_ctastrategy

        pkg = Path(vnpy_ctastrategy.__file__).resolve().parent / "strategies" / f"{snake}.py"
        candidates.insert(1, pkg)
    except Exception:
        pass
    for path in candidates:
        if path.is_file():
            return path
    return None


def _load_seed_source(class_name: str) -> str:
    path = _resolve_seed_source_path(class_name)
    if path is not None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            logger.exception("read seed source failed %s", path)
    from core import strategy_loader

    parent = _CLASS_PARENT.get(class_name, "EliteCtaTemplate")
    return strategy_loader.default_strategy_source(class_name, parent)


def _seed_items() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for idx, (class_name, title) in enumerate(STRATEGY_TITLE_ZH.items()):
        items.append(
            {
                "code": _code_for_class(class_name),
                "name": title or strategy_title_zh(class_name),
                "description": f"{title}（{class_name}）— 库内策略类，运行前动态编译。",
                "class_name": class_name,
                "parent_template": _CLASS_PARENT.get(class_name, "CtaTemplate"),
                "default_params": dict(_CLASS_DEFAULT_PARAMS.get(class_name, {})),
                "template_source": _load_seed_source(class_name),
                "vt_symbol": _DEFAULT_VT_SYMBOL,
                "base_config": dict(_DEFAULT_BASE_CONFIG),
                "sort_order": (idx + 1) * 10,
            }
        )
    return items


def _model_dict(row: StrategyModel, *, latest: StrategyModelVersion | None = None) -> dict[str, Any]:
    symbols = parse_vt_symbols(row.vt_symbol)
    out: dict[str, Any] = {
        "id": row.id,
        "code": row.code,
        "name": row.name,
        "description": row.description,
        "class_name": row.class_name,
        "parent_template": row.parent_template,
        "default_params": _loads(row.default_params),
        "template_source": row.template_source,
        "vt_symbol": symbols[0] if symbols else "",
        "vt_symbols": symbols,
        "base_config": _loads(row.base_config) or dict(_DEFAULT_BASE_CONFIG),
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
    detail = _loads_any(row.result_detail)
    return {
        "id": row.id,
        "strategy_name": row.strategy_name,
        "model_id": row.model_id,
        "instance_version_id": row.instance_version_id,
        "model_version_id": row.model_version_id,
        "run_params": _loads(row.run_params),
        "statistics": _loads(row.statistics),
        "result_detail": detail if isinstance(detail, dict) else {},
        "status": row.status,
        "note": row.note,
        "created_at": row.created_at,
    }


def ensure_defaults() -> None:
    """Seed STRATEGY_TITLE_ZH models + v1 when missing; backfill source if empty."""
    if not available():
        return
    for item in _seed_items():
        existing = get_model_by_code(item["code"])
        if existing is None:
            try:
                create_model(
                    code=item["code"],
                    name=item["name"],
                    description=item["description"],
                    class_name=item["class_name"],
                    parent_template=item["parent_template"],
                    default_params=item["default_params"],
                    template_source=item["template_source"],
                    vt_symbol=item["vt_symbol"],
                    base_config=item["base_config"],
                    sort_order=item["sort_order"],
                    note="系统预置 v1",
                )
            except Exception:
                logger.exception("seed model %s failed", item["code"])
            continue
        # Backfill empty source / contract on older rows
        try:
            _backfill_model_seed(existing["id"], item)
        except Exception:
            logger.exception("backfill model %s failed", item["code"])


def _backfill_model_seed(model_id: int, item: dict[str, Any]) -> None:
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            return
        changed = False
        if not (row.template_source or "").strip() and item.get("template_source"):
            row.template_source = item["template_source"]
            changed = True
        if not (row.vt_symbol or "").strip():
            row.vt_symbol = item.get("vt_symbol") or _DEFAULT_VT_SYMBOL
            changed = True
        if not (row.base_config or "").strip():
            row.base_config = _dumps(item.get("base_config") or _DEFAULT_BASE_CONFIG)
            changed = True
        if changed:
            row.updated_at = _now()
            # Keep latest version source in sync if empty
            if row.latest_version_id:
                ver = db.get(StrategyModelVersion, row.latest_version_id)
                if ver is not None and not (ver.template_source or "").strip():
                    ver.template_source = row.template_source
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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


def get_model_by_class_name(class_name: str) -> dict[str, Any] | None:
    if not available() or not (class_name or "").strip():
        return None
    db = get_session()
    try:
        row = db.scalar(
            select(StrategyModel).where(StrategyModel.class_name == class_name.strip()).limit(1)
        )
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
    vt_symbol: str | None = None,
    base_config: dict[str, Any] | None = None,
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
    params = default_params or {}
    source = template_source
    if source is None:
        source = _load_seed_source(class_name)
    symbol = format_vt_symbols(vt_symbol) or _DEFAULT_VT_SYMBOL
    config = base_config or dict(_DEFAULT_BASE_CONFIG)
    db = get_session()
    try:
        row = StrategyModel(
            code=code,
            name=(name or code).strip(),
            description=description or "",
            class_name=class_name,
            parent_template=(parent_template or "EliteCtaTemplate").strip(),
            default_params=_dumps(params),
            template_source=source,
            vt_symbol=symbol,
            base_config=_dumps(config),
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
            params=_dumps(params),
            template_source=source,
            created_by=user_id,
            created_at=_now(),
        )
        db.add(ver)
        db.flush()
        row.latest_version_id = ver.id
        db.commit()
        db.refresh(row)
        db.refresh(ver)
        # Also sync strategy_classes so loader finds MySQL source
        try:
            from core import strategy_loader

            if source and source.strip():
                strategy_loader.save_class_source(class_name, source)
        except Exception:
            logger.debug("seed sync strategy_classes skipped for %s", class_name, exc_info=True)
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
    """Update non-versioned metadata only."""
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


def update_model_draft(
    model_id: int,
    *,
    params: dict[str, Any] | None = None,
    template_source: str | None = None,
    vt_symbol: str | None = None,
    base_config: dict[str, Any] | None = None,
    sync_class_store: bool = True,
) -> dict[str, Any]:
    """Save working copy without bumping version (普通保存)."""
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            raise ValueError("模型不存在")
        if params is not None:
            row.default_params = _dumps(params)
        if template_source is not None:
            if not template_source.strip():
                raise ValueError("源码不能为空")
            row.template_source = template_source
        if vt_symbol is not None:
            row.vt_symbol = format_vt_symbols(vt_symbol)
        if base_config is not None:
            row.base_config = _dumps(base_config)
        row.updated_at = _now()
        db.commit()
        latest = db.get(StrategyModelVersion, row.latest_version_id) if row.latest_version_id else None
        out = _model_dict(row, latest=latest)
        class_name = row.class_name
        source = row.template_source
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if sync_class_store and source and class_name:
        try:
            from core import strategy_loader

            strategy_loader.save_class_source(class_name, source)
        except Exception:
            logger.exception("draft sync strategy_classes failed for %s", class_name)
    return out


def save_model_version(
    model_id: int,
    *,
    params: dict[str, Any] | None = None,
    template_source: str | None = None,
    label: str = "",
    note: str = "",
    user_id: int | None = None,
) -> dict[str, Any]:
    """Explicit「保存为新版本」— immutable snapshot from args or current draft."""
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
        if snap_source is not None:
            row.template_source = snap_source
        row.latest_version_id = ver.id
        row.updated_at = _now()
        db.commit()
        db.refresh(ver)
        class_name = row.class_name
        source = snap_source
        out = _version_dict(ver)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if source and class_name:
        try:
            from core import strategy_loader

            strategy_loader.save_class_source(class_name, source)
        except Exception:
            logger.exception("version sync strategy_classes failed for %s", class_name)
    return out


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


def resolve_model_run_context(
    model_id: int,
    *,
    model_version_id: int | None = None,
    runtime_override: dict[str, Any] | None = None,
    prefer_draft: bool = False,
) -> dict[str, Any]:
    """Load 合约 / 参数 / 基础配置 / 源码 for run (selected version or draft)."""
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        row = db.get(StrategyModel, int(model_id))
        if row is None:
            raise ValueError("模型不存在")
        ver: StrategyModelVersion | None = None
        use_draft = prefer_draft or not model_version_id
        if model_version_id:
            ver = db.get(StrategyModelVersion, int(model_version_id))
            if ver is None or ver.model_id != row.id:
                raise ValueError("模型版本不存在或不属于该模型")
            use_draft = False

        if use_draft:
            source = row.template_source or ""
            params = _loads(row.default_params)
            version_id = row.latest_version_id
            version_no = None
            version_label = "draft"
            if version_id:
                latest = db.get(StrategyModelVersion, version_id)
                if latest is not None:
                    version_no = latest.version_no
        else:
            assert ver is not None
            source = (ver.template_source or row.template_source or "")
            params = _loads(ver.params) or _loads(row.default_params)
            version_id = ver.id
            version_no = ver.version_no
            version_label = ver.label or f"v{ver.version_no}"

        if not source.strip():
            raise ValueError(f"模型 {row.class_name} 无可用源码")

        setting = dict(params)
        if runtime_override:
            setting.update(runtime_override)

        base_config = _loads(row.base_config) or dict(_DEFAULT_BASE_CONFIG)
        symbols = parse_vt_symbols(row.vt_symbol)
        return {
            "model_id": row.id,
            "model_code": row.code,
            "model_name": row.name,
            "class_name": row.class_name,
            "parent_template": row.parent_template,
            "vt_symbol": symbols[0] if symbols else _DEFAULT_VT_SYMBOL,
            "vt_symbols": symbols,
            "base_config": base_config,
            "params": params,
            "setting": setting,
            "template_source": source,
            "model_version_id": version_id,
            "version_no": version_no,
            "version_label": version_label,
            "from_draft": use_draft,
        }
    finally:
        db.close()


def resolve_pinned_setting(
    *,
    strategy_name: str,
    runtime_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge pinned model-version params ← instance runtime params ← override."""
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
    strategy_name: str = "",
    model_id: int | None = None,
    instance_version_id: int | None = None,
    model_version_id: int | None = None,
    run_params: dict[str, Any] | None = None,
    statistics: dict[str, Any] | None = None,
    result_detail: dict[str, Any] | None = None,
    status: str = "done",
    note: str = "",
) -> dict[str, Any]:
    if not available():
        raise RuntimeError("database is not initialized")
    db = get_session()
    try:
        name = (strategy_name or "").strip()
        mid = model_id
        iv = instance_version_id
        mv = model_version_id
        if name:
            inst = db.scalar(select(StrategyInstance).where(StrategyInstance.strategy_name == name))
            if inst is not None:
                if iv is None:
                    iv = inst.current_version_id
                if mv is None:
                    mv = inst.model_version_id
                if mid is None:
                    mid = inst.model_id
        if not name and mid:
            model = db.get(StrategyModel, int(mid))
            if model is not None:
                name = model.code or model.class_name
        row = StrategyBacktestRun(
            strategy_name=name or (f"model:{mid}" if mid else "unknown"),
            model_id=mid,
            instance_version_id=iv,
            model_version_id=mv,
            run_params=_dumps(run_params or {}),
            statistics=_dumps(statistics or {}),
            result_detail=_dumps(result_detail) if result_detail is not None else None,
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
    strategy_name: str = "",
    *,
    model_id: int | None = None,
    instance_version_id: int | None = None,
    model_version_id: int | None = None,
) -> list[dict[str, Any]]:
    if not available():
        return []
    db = get_session()
    try:
        q = select(StrategyBacktestRun)
        if model_id is not None:
            q = q.where(StrategyBacktestRun.model_id == int(model_id))
        elif strategy_name.strip():
            q = q.where(StrategyBacktestRun.strategy_name == strategy_name.strip())
        if instance_version_id is not None:
            q = q.where(StrategyBacktestRun.instance_version_id == int(instance_version_id))
        if model_version_id is not None:
            q = q.where(StrategyBacktestRun.model_version_id == int(model_version_id))
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
