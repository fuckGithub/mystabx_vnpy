"""CTA strategy REST API — admin write / user read (docs/09 阶段 A/D)."""

from __future__ import annotations

import inspect
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import User
from core.deps import current_user, require_admin
from core.runtime import runtime
from core.serialize import cta_stop_order_payload, cta_strategy_payload
from core.strategy_names import strategy_display_name
from core import strategy_loader, strategy_store
from core import base_class_store
from core import model_store
from mystabx.paths import PROJECT_ROOT

router = APIRouter(prefix="/api/cta", tags=["cta"])

_SKIP_CLASSES = {"EliteCtaTemplate", "CtaTemplate", "TargetPosTemplate"}
_STRATEGIES_DIR = (PROJECT_ROOT / "strategies").resolve()


def _cta():
    engine = runtime.cta
    if engine is None:
        raise HTTPException(status_code=503, detail="CTA 引擎未加载（缺少 vnpy_ctastrategy）")
    return engine


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _mtime_iso(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
    except OSError:
        return None


def _strategy_file_meta(engine, class_name: str) -> dict:
    """Resolve module / source file for a loaded CtaTemplate class (VeighNa-style)."""
    cls = getattr(engine, "classes", {}).get(class_name)
    module = getattr(cls, "__module__", "") or "" if cls is not None else ""
    file_name = ""
    file_path = ""
    abs_path: Path | None = None
    if cls is not None:
        try:
            abs_path = Path(inspect.getfile(cls)).resolve()
            file_name = abs_path.name
            try:
                file_path = str(abs_path.relative_to(PROJECT_ROOT.resolve()))
            except ValueError:
                file_path = str(abs_path)
        except (TypeError, OSError):
            abs_path = None
    if not file_name and class_name:
        file_name = f"{_camel_to_snake(class_name)}.py"
        abs_path = (_STRATEGIES_DIR / file_name).resolve()
        file_path = f"strategies/{file_name}"
    return {
        "module": module,
        "file_name": file_name,
        "file_path": file_path,
        "updated_at": _mtime_iso(abs_path) if abs_path else None,
        "editable": bool(abs_path and str(abs_path).startswith(str(_STRATEGIES_DIR))),
    }


def _strategy_class_rows(engine) -> list[dict]:
    rows = []
    for name in engine.get_all_strategy_class_names():
        if name in _SKIP_CLASSES:
            continue
        try:
            params = engine.get_strategy_class_parameters(name)
        except Exception:
            params = {}
        meta = _strategy_file_meta(engine, name)
        rows.append(
            {
                "class_name": name,
                "display_name": strategy_display_name(name),
                "parameters": params,
                **meta,
            }
        )
    return rows


def _instance_row(engine, strategy) -> dict:
    row = cta_strategy_payload(strategy)
    class_name = str(row.get("class_name") or "")
    meta = _strategy_file_meta(engine, class_name) if class_name else {}
    name = str(row.get("strategy_name") or getattr(strategy, "strategy_name", "") or "")
    binding = model_store.instance_binding(name) if name else {}
    backtests = model_store.list_backtest_runs(name) if name else []
    row.update(
        {
            "file_name": meta.get("file_name") or "",
            "file_path": meta.get("file_path") or "",
            "updated_at": meta.get("updated_at"),
            "editable": bool(meta.get("editable")),
            "backtest_count": len(backtests),
            "model_id": binding.get("model_id"),
            "model_version_id": binding.get("model_version_id"),
            "current_version_id": binding.get("current_version_id"),
            "model": binding.get("model"),
            "model_version": binding.get("model_version"),
            "current_version": binding.get("current_version"),
        }
    )
    return row


def _resolve_source_path(engine, class_name: str, *, for_write: bool) -> Path:
    if class_name not in getattr(engine, "classes", {}):
        raise HTTPException(status_code=404, detail=f"找不到策略类 {class_name}")
    meta = _strategy_file_meta(engine, class_name)
    raw = str(meta.get("file_path") or "")
    if not raw:
        raise HTTPException(status_code=404, detail="无法定位策略源文件")
    path = Path(raw)
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    if for_write:
        if path.suffix != ".py":
            raise HTTPException(status_code=400, detail="仅支持 .py 策略文件")
        if not str(path).startswith(str(_STRATEGIES_DIR)):
            raise HTTPException(status_code=403, detail="仅允许编辑项目 strategies/ 目录下的策略源码")
    return path


class InstanceCreate(BaseModel):
    class_name: str = ""
    strategy_name: str
    vt_symbol: str = ""
    vt_symbols: list[str] | None = None
    setting: dict = Field(default_factory=dict)
    model_id: int | None = None
    model_version_id: int | None = None


class InstanceEdit(BaseModel):
    setting: dict = Field(default_factory=dict)
    model_id: int | None = None
    model_version_id: int | None = None
    create_version: bool = True
    note: str = ""


class InstanceRename(BaseModel):
    strategy_name: str


class InstancePinBody(BaseModel):
    model_id: int | None = None
    model_version_id: int | None = None


class InstanceVersionBody(BaseModel):
    runtime_params: dict | None = None
    source_code: str | None = None
    model_id: int | None = None
    model_version_id: int | None = None
    note: str = ""


class StrategySourceBody(BaseModel):
    content: str
    reload: bool = True
    create_version: bool = True
    model_version_id: int | None = None
    note: str = ""


class ModelCreateBody(BaseModel):
    code: str
    name: str = ""
    description: str = ""
    class_name: str
    parent_template: str = "EliteCtaTemplate"
    default_params: dict = Field(default_factory=dict)
    template_source: str | None = None
    vt_symbol: str = "rb2501.SHFE"
    vt_symbols: list[str] | None = None
    base_config: dict = Field(default_factory=dict)
    sort_order: int = 100
    enabled: bool = True
    note: str = "初始版本"


class ModelMetaBody(BaseModel):
    name: str | None = None
    description: str | None = None
    class_name: str | None = None
    parent_template: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


class ModelVersionBody(BaseModel):
    params: dict | None = None
    template_source: str | None = None
    label: str = ""
    note: str = ""


class ModelDraftBody(BaseModel):
    """Ordinary save — updates working draft without version bump."""

    params: dict | None = None
    template_source: str | None = None
    vt_symbol: str | None = None
    vt_symbols: list[str] | None = None
    base_config: dict | None = None


def _ensure_from_db(class_name: str, *, strategy_name: str | None = None) -> None:
    """Compile MySQL source into CTA/backtester engines before init/start."""
    try:
        strategy_loader.ensure_class_loaded_from_db(class_name, strategy_name=strategy_name)
        if strategy_name:
            strategy_loader.rebind_live_instance(strategy_name, class_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"从数据库加载策略失败: {exc}") from exc


def _apply_pinned_params(name: str, strategy) -> dict:
    """Apply pinned model-version params onto a live strategy object when possible."""
    setting = model_store.resolve_pinned_setting(strategy_name=name)
    if not setting:
        return setting
    try:
        engine = _cta()
        engine.edit_strategy(name, setting)
    except Exception:
        # Best-effort: set attributes directly if edit_strategy rejects (e.g. trading)
        for key, value in setting.items():
            if hasattr(strategy, key):
                try:
                    setattr(strategy, key, value)
                except Exception:
                    pass
    return setting


@router.get("/strategies")
def list_strategy_classes(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    return _strategy_class_rows(_cta())


@router.get("/strategies/template")
def get_strategy_template(
    class_name: str = "UserStrategy",
    parent_class: str = "",
    user: User = Depends(current_user),
) -> dict:
    """Default IDE template inheriting selected / default base class."""
    _ = user
    name = (class_name or "UserStrategy").strip() or "UserStrategy"
    parent = (parent_class or "").strip() or None
    info = strategy_loader.parent_class_info(parent)
    return {
        "class_name": name,
        "content": strategy_loader.default_strategy_source(name, parent),
        "editable": True,
        "store": "default",
        "is_default": True,
        **info,
    }


class BaseClassBody(BaseModel):
    class_name: str = ""
    display_name: str = ""
    module: str = ""
    import_stmt: str = ""
    description: str = ""
    base_chain: str = ""
    enabled: bool = True
    is_default: bool = False
    sort_order: int = 100


class ApplyParentBody(BaseModel):
    content: str
    parent_class: str


@router.post("/source/apply-parent")
def apply_parent_class(body: ApplyParentBody, user: User = Depends(current_user)) -> dict:
    """Rewrite strategy source inheritance + import for a catalog parent class."""
    _ = user
    parent = (body.parent_class or "").strip()
    if not parent:
        raise HTTPException(status_code=400, detail="parent_class 不能为空")
    info = strategy_loader.parent_class_info(parent)
    content = strategy_loader.apply_parent_to_source(
        body.content or "",
        info["parent_class"],
        str(info.get("import_stmt") or ""),
    )
    return {"content": content, **info}


@router.get("/base-classes")
def list_base_classes(
    enabled_only: bool = False,
    user: User = Depends(current_user),
) -> list[dict]:
    _ = user
    return base_class_store.list_base_classes(enabled_only=enabled_only)


@router.get("/base-classes/{class_name}")
def get_base_class(class_name: str, user: User = Depends(current_user)) -> dict:
    _ = user
    row = base_class_store.get_base_class(class_name)
    if row is None:
        raise HTTPException(status_code=404, detail="基类不存在")
    return row


@router.put("/base-classes/{class_name}")
def put_base_class(
    class_name: str,
    body: BaseClassBody,
    user: User = Depends(require_admin),
) -> dict:
    _ = user
    payload = body.model_dump()
    payload["class_name"] = (class_name or body.class_name or "").strip()
    try:
        return base_class_store.upsert_base_class(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/base-classes")
def create_base_class(body: BaseClassBody, user: User = Depends(require_admin)) -> dict:
    _ = user
    try:
        return base_class_store.upsert_base_class(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/base-classes/{class_name}")
def remove_base_class(class_name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    try:
        base_class_store.delete_base_class(class_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.get("/models")
def list_models(enabled_only: bool = False, user: User = Depends(current_user)) -> list[dict]:
    _ = user
    return model_store.list_models(enabled_only=enabled_only)


@router.post("/models")
def create_model(body: ModelCreateBody, user: User = Depends(require_admin)) -> dict:
    _ = user
    try:
        symbols = body.vt_symbols if body.vt_symbols is not None else body.vt_symbol
        return model_store.create_model(
            code=body.code,
            name=body.name,
            description=body.description,
            class_name=body.class_name,
            parent_template=body.parent_template,
            default_params=body.default_params,
            template_source=body.template_source,
            vt_symbol=model_store.format_vt_symbols(symbols) or body.vt_symbol,
            base_config=body.base_config or None,
            sort_order=body.sort_order,
            enabled=body.enabled,
            note=body.note,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/models/{model_id}")
def get_model(model_id: int, user: User = Depends(current_user)) -> dict:
    _ = user
    row = model_store.get_model(model_id)
    if row is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return row


@router.patch("/models/{model_id}")
def patch_model(model_id: int, body: ModelMetaBody, user: User = Depends(require_admin)) -> dict:
    _ = user
    try:
        return model_store.update_model_meta(
            model_id,
            name=body.name,
            description=body.description,
            class_name=body.class_name,
            parent_template=body.parent_template,
            enabled=body.enabled,
            sort_order=body.sort_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/models/{model_id}/draft")
def put_model_draft(model_id: int, body: ModelDraftBody, user: User = Depends(require_admin)) -> dict:
    """普通保存：更新草稿（代码/参数/合约/基础配置），不升级版本号。"""
    _ = user
    try:
        symbols = None
        if body.vt_symbols is not None:
            symbols = model_store.format_vt_symbols(body.vt_symbols)
        elif body.vt_symbol is not None:
            symbols = model_store.format_vt_symbols(body.vt_symbol)
        return model_store.update_model_draft(
            model_id,
            params=body.params,
            template_source=body.template_source,
            vt_symbol=symbols,
            base_config=body.base_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/models/{model_id}/run-context")
def get_model_run_context(
    model_id: int,
    model_version_id: int | None = None,
    user: User = Depends(current_user),
) -> dict:
    """Preview what「运行」will load from DB (合约/参数/基础配置/源码)."""
    _ = user
    try:
        return model_store.resolve_model_run_context(model_id, model_version_id=model_version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/models/{model_id}/versions")
def create_model_version(
    model_id: int,
    body: ModelVersionBody,
    user: User = Depends(require_admin),
) -> dict:
    """「保存为新版本」— only this bumps version_no."""
    _ = user
    try:
        return model_store.save_model_version(
            model_id,
            params=body.params,
            template_source=body.template_source,
            label=body.label,
            note=body.note,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/models/{model_id}/versions")
def list_model_versions(model_id: int, user: User = Depends(current_user)) -> list[dict]:
    _ = user
    if model_store.get_model(model_id) is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model_store.list_model_versions(model_id)


@router.get("/models/{model_id}/backtests")
def list_model_backtests(model_id: int, user: User = Depends(current_user)) -> list[dict]:
    _ = user
    if model_store.get_model(model_id) is None:
        raise HTTPException(status_code=404, detail="模型不存在")
    return model_store.list_backtest_runs(model_id=model_id)


@router.get("/model-versions/{version_id}")
def get_model_version(version_id: int, user: User = Depends(current_user)) -> dict:
    _ = user
    row = model_store.get_model_version(version_id)
    if row is None:
        raise HTTPException(status_code=404, detail="模型版本不存在")
    return row


@router.delete("/models/{model_id}")
def delete_model(model_id: int, user: User = Depends(require_admin)) -> dict:
    _ = user
    try:
        model_store.delete_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/strategies/reload")
def reload_strategy_classes(user: User = Depends(require_admin)) -> list[dict]:
    """Re-scan strategies/ (+ vnpy built-ins) via CtaEngine.load_strategy_class()."""
    _ = user
    engine = _cta()
    try:
        engine.load_strategy_class()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重新加载策略类失败: {exc}") from exc
    return _strategy_class_rows(engine)


@router.get("/strategies/{class_name}/source")
def get_strategy_source(class_name: str, user: User = Depends(current_user)) -> dict:
    """Load source: MySQL class row → strategies/*.py → default EliteCtaTemplate template."""
    _ = user
    try:
        return strategy_loader.resolve_source_for_class(class_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/strategies/{class_name}/source")
def put_strategy_source(
    class_name: str,
    body: StrategySourceBody,
    user: User = Depends(require_admin),
) -> dict:
    """Save source to MySQL (authoritative) + materialize file + hot-compile into engines."""
    _ = user
    try:
        meta = strategy_loader.save_class_source(class_name, body.content)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"写入失败: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"编译失败: {exc}") from exc

    reloaded = False
    if body.reload:
        try:
            strategy_loader.ensure_class_loaded_from_db(class_name)
            reloaded = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"保存成功但热加载失败: {exc}") from exc
    return {
        "ok": True,
        "class_name": class_name,
        "file_path": meta.get("file_path"),
        "updated_at": meta.get("updated_at"),
        "reloaded": reloaded,
        "store": "mysql",
    }


@router.get("/instances/{name}/source")
def get_instance_source(name: str, user: User = Depends(current_user)) -> dict:
    """Effective source for an instance (instance override → class → default template)."""
    _ = user
    engine = _cta()
    strategy = engine.strategies.get(name)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    class_name = strategy.__class__.__name__
    return strategy_loader.resolve_source_for_instance(name, class_name)


@router.put("/instances/{name}/source")
def put_instance_source(
    name: str,
    body: StrategySourceBody,
    user: User = Depends(require_admin),
) -> dict:
    """Save instance IDE source to MySQL, pin model version, create instance version."""
    _ = user
    engine = _cta()
    strategy = engine.strategies.get(name)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    class_name = strategy.__class__.__name__
    # Ensure meta row exists
    strategy_store.upsert_instance_meta(
        strategy_name=name,
        strategy_class=class_name,
        vt_symbol=getattr(strategy, "vt_symbol", ""),
        params=dict(strategy.get_parameters()) if hasattr(strategy, "get_parameters") else {},
        status="trading" if getattr(strategy, "trading", False) else "stopped",
        user_id=user.id,
    )
    try:
        meta = strategy_loader.save_instance_source(name, class_name, body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"保存失败: {exc}") from exc

    version_row = None
    if body.create_version:
        try:
            runtime = dict(strategy.get_parameters()) if hasattr(strategy, "get_parameters") else {}
            version_row = model_store.save_instance_version(
                name,
                runtime_params=runtime,
                source_code=body.content,
                model_version_id=body.model_version_id,
                note=body.note or "保存源码",
                user_id=user.id,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"源码已保存但创建实例版本失败: {exc}") from exc

    reloaded = False
    if body.reload:
        try:
            _ensure_from_db(class_name, strategy_name=name)
            reloaded = True
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"保存成功但热加载失败: {exc}") from exc
    return {
        "ok": True,
        "strategy_name": name,
        "class_name": class_name,
        "updated_at": meta.get("updated_at"),
        "reloaded": reloaded,
        "store": "mysql_instance",
        "instance_version": version_row,
    }


@router.get("/instances")
def list_instances(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    engine = _cta()
    return [_instance_row(engine, s) for s in engine.strategies.values()]


@router.get("/instances/{name}")
def get_instance(name: str, user: User = Depends(current_user)) -> dict:
    _ = user
    engine = _cta()
    strategy = engine.strategies.get(name)
    if strategy is None:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    return _instance_row(engine, strategy)


@router.post("/instances")
def add_instance(body: InstanceCreate, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()

    class_name = (body.class_name or "").strip()
    setting = dict(body.setting or {})
    model_id = body.model_id
    model_version_id = body.model_version_id
    model: dict | None = None

    if model_id:
        model = model_store.get_model(model_id)
        if model is None:
            raise HTTPException(status_code=400, detail="模型不存在")
        class_name = class_name or str(model.get("class_name") or "")
        if model_version_id:
            mv = model_store.get_model_version(model_version_id)
            if mv is None or int(mv.get("model_id") or 0) != int(model_id):
                raise HTTPException(status_code=400, detail="模型版本无效")
            # Pin snapshot params as base; instance setting overrides
            base = dict(mv.get("params") or {})
            base.update(setting)
            setting = base
        else:
            model_version_id = model.get("latest_version_id")
            base = dict((model.get("latest_version") or {}).get("params") or model.get("default_params") or {})
            base.update(setting)
            setting = base

    if not class_name:
        raise HTTPException(status_code=400, detail="缺少策略类名 / 模型")

    # Prefer DB source before requiring class to already be in memory
    try:
        strategy_loader.ensure_class_loaded_from_db(class_name)
    except Exception:
        pass
    if class_name not in engine.classes:
        raise HTTPException(status_code=400, detail=f"找不到策略类 {class_name}")

    symbols = model_store.parse_vt_symbols(body.vt_symbols if body.vt_symbols is not None else body.vt_symbol)
    if not symbols and model is not None:
        symbols = list(model.get("vt_symbols") or []) or model_store.parse_vt_symbols(model.get("vt_symbol"))
    if not symbols:
        raise HTTPException(status_code=400, detail="请至少选择一个合约")

    base_name = (body.strategy_name or "").strip()
    if not base_name:
        raise HTTPException(status_code=400, detail="策略实例名称不能为空")

    def _instance_name(sym: str) -> str:
        if len(symbols) == 1:
            return base_name
        short = sym.split(".", 1)[0]
        return f"{base_name}_{short}"

    created: list[dict] = []
    for sym in symbols:
        name = _instance_name(sym)
        if name in engine.strategies:
            raise HTTPException(status_code=400, detail=f"策略实例名称已存在: {name}")
        engine.add_strategy(class_name, name, sym, setting)
        if name not in engine.strategies:
            raise HTTPException(status_code=400, detail=f"创建策略失败: {name}，请查看 CTA 日志")
        strategy_store.upsert_instance_meta(
            strategy_name=name,
            strategy_class=class_name,
            vt_symbol=sym,
            params=setting,
            status="stopped",
            user_id=user.id,
        )
        if model_id:
            try:
                model_store.pin_instance_model(
                    name,
                    model_id=model_id,
                    model_version_id=model_version_id,
                )
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            model_store.save_instance_version(
                name,
                runtime_params=setting,
                source_code=None,
                model_id=model_id,
                model_version_id=model_version_id,
                note="创建实例" if len(symbols) == 1 else f"创建实例（{sym}）",
                user_id=user.id,
            )
        except Exception:
            pass
        created.append({"strategy_name": name, "vt_symbol": sym})

    return {
        "ok": True,
        "strategy_name": created[0]["strategy_name"] if created else base_name,
        "created": created,
        "model_id": model_id,
        "model_version_id": model_version_id,
    }


@router.patch("/instances/{name}")
def edit_instance(name: str, body: InstanceEdit, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    if body.model_id is not None or body.model_version_id is not None:
        try:
            model_store.pin_instance_model(
                name,
                model_id=body.model_id,
                model_version_id=body.model_version_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    setting = model_store.resolve_pinned_setting(strategy_name=name, runtime_override=body.setting)
    engine.edit_strategy(name, setting)
    strategy = engine.strategies.get(name)
    if strategy is not None:
        strategy_store.upsert_instance_meta(
            strategy_name=name,
            strategy_class=strategy.__class__.__name__,
            vt_symbol=getattr(strategy, "vt_symbol", ""),
            params=setting,
            status="trading" if getattr(strategy, "trading", False) else "stopped",
            user_id=user.id,
        )
        if body.create_version:
            try:
                model_store.save_instance_version(
                    name,
                    runtime_params=setting,
                    note=body.note or "更新参数",
                    user_id=user.id,
                )
            except Exception:
                pass
    return {"ok": True, "setting": setting}


@router.post("/instances/{name}/pin-model")
def pin_instance_model(name: str, body: InstancePinBody, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    try:
        return model_store.pin_instance_model(
            name,
            model_id=body.model_id,
            model_version_id=body.model_version_id,
            clear=body.model_id is None and body.model_version_id is None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/instances/{name}/versions")
def list_instance_versions(name: str, user: User = Depends(current_user)) -> list[dict]:
    _ = user
    return model_store.list_instance_versions(name)


@router.post("/instances/{name}/versions")
def create_instance_version(
    name: str,
    body: InstanceVersionBody,
    user: User = Depends(require_admin),
) -> dict:
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    try:
        return model_store.save_instance_version(
            name,
            runtime_params=body.runtime_params,
            source_code=body.source_code,
            model_id=body.model_id,
            model_version_id=body.model_version_id,
            note=body.note,
            user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/instances/{name}/binding")
def get_instance_binding(name: str, user: User = Depends(current_user)) -> dict:
    _ = user
    return model_store.instance_binding(name)


@router.get("/instances/{name}/backtests")
def list_instance_backtests(
    name: str,
    instance_version_id: int | None = None,
    user: User = Depends(current_user),
) -> list[dict]:
    _ = user
    return model_store.list_backtest_runs(name, instance_version_id=instance_version_id)


@router.post("/instances/{name}/rename")
def rename_instance(name: str, body: InstanceRename, user: User = Depends(require_admin)) -> dict:
    """Rename instance via remove + re-add (must be stopped)."""
    _ = user
    engine = _cta()
    new_name = body.strategy_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="新实例名不能为空")
    if new_name == name:
        return {"ok": True, "strategy_name": name}
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    if new_name in engine.strategies:
        raise HTTPException(status_code=400, detail="新实例名已存在")
    strategy = engine.strategies[name]
    if getattr(strategy, "trading", False):
        raise HTTPException(status_code=400, detail="请先停止策略再重命名")
    class_name = strategy.__class__.__name__
    vt_symbol = getattr(strategy, "vt_symbol", "")
    setting = dict(strategy.get_parameters()) if hasattr(strategy, "get_parameters") else {}
    ok = engine.remove_strategy(name)
    if not ok:
        raise HTTPException(status_code=400, detail="移除旧实例失败（请确认已停止）")
    engine.add_strategy(class_name, new_name, vt_symbol, setting)
    if new_name not in engine.strategies:
        raise HTTPException(status_code=500, detail="重命名失败：新实例未创建成功")
    strategy_store.rename_instance_meta(name, new_name)
    strategy_store.upsert_instance_meta(
        strategy_name=new_name,
        strategy_class=class_name,
        vt_symbol=vt_symbol,
        params=setting,
        status="stopped",
        user_id=user.id,
    )
    return {"ok": True, "strategy_name": new_name}


@router.delete("/instances/{name}")
def remove_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    ok = engine.remove_strategy(name)
    if not ok:
        raise HTTPException(status_code=400, detail="移除失败（请先停止策略）")
    strategy_store.delete_instance_meta(name)
    return {"ok": True}


@router.post("/instances/init-all")
def init_all(user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    for s_name, strategy in list(engine.strategies.items()):
        _ensure_from_db(strategy.__class__.__name__, strategy_name=s_name)
    engine.init_all_strategies()
    return {"ok": True}


@router.post("/instances/start-all")
def start_all(user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    for s_name, strategy in list(engine.strategies.items()):
        _ensure_from_db(strategy.__class__.__name__, strategy_name=s_name)
    engine.start_all_strategies()
    return {"ok": True}


@router.post("/instances/stop-all")
def stop_all(user: User = Depends(require_admin)) -> dict:
    _ = user
    _cta().stop_all_strategies()
    return {"ok": True}


@router.post("/instances/{name}/init")
def init_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    strategy = engine.strategies[name]
    class_name = strategy.__class__.__name__
    _ensure_from_db(class_name, strategy_name=name)
    _apply_pinned_params(name, engine.strategies.get(name) or strategy)
    engine.init_strategy(name)
    return {"ok": True, "setting": model_store.resolve_pinned_setting(strategy_name=name)}


@router.post("/instances/{name}/start")
def start_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    strategy = engine.strategies[name]
    class_name = strategy.__class__.__name__
    _ensure_from_db(class_name, strategy_name=name)
    _apply_pinned_params(name, engine.strategies.get(name) or strategy)
    engine.start_strategy(name)
    return {"ok": True, "setting": model_store.resolve_pinned_setting(strategy_name=name)}


@router.post("/instances/{name}/stop")
def stop_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    engine.stop_strategy(name)
    return {"ok": True}


@router.get("/stop-orders")
def list_stop_orders(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    engine = _cta()
    orders = getattr(engine, "stop_orders", None) or {}
    return [cta_stop_order_payload(so) for so in orders.values()]
