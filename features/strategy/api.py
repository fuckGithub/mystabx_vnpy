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
from core import strategy_store
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
    row.update(
        {
            "file_name": meta.get("file_name") or "",
            "file_path": meta.get("file_path") or "",
            "updated_at": meta.get("updated_at"),
            "editable": bool(meta.get("editable")),
            # 尚无按实例持久化回测历史；有全局回测结果时前端可链到回测页
            "backtest_count": 0,
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
    class_name: str
    strategy_name: str
    vt_symbol: str
    setting: dict = Field(default_factory=dict)


class InstanceEdit(BaseModel):
    setting: dict = Field(default_factory=dict)


class InstanceRename(BaseModel):
    strategy_name: str


class StrategySourceBody(BaseModel):
    content: str
    reload: bool = True


@router.get("/strategies")
def list_strategy_classes(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    return _strategy_class_rows(_cta())


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
    _ = user
    engine = _cta()
    path = _resolve_source_path(engine, class_name, for_write=False)
    editable = str(path.resolve()).startswith(str(_STRATEGIES_DIR)) if path else False
    # Prefer MySQL (authoritative); fall back to strategies/*.py for CTA load path.
    stored = strategy_store.get_strategy_source(class_name)
    if stored and stored.get("content") is not None:
        return {
            "class_name": class_name,
            "file_path": stored.get("file_path") or (str(path.relative_to(PROJECT_ROOT.resolve())) if editable else str(path)),
            "editable": bool(stored.get("editable", editable)),
            "updated_at": stored.get("updated_at") or _mtime_iso(path),
            "content": stored["content"],
            "store": "mysql",
        }
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"源文件不存在: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"读取失败: {exc}") from exc
    rel = str(path.relative_to(PROJECT_ROOT.resolve())) if editable else str(path)
    if editable:
        strategy_store.sync_class_from_file(
            class_name=class_name,
            path=path,
            module=getattr(getattr(engine, "classes", {}).get(class_name), "__module__", "") or "",
            editable=True,
            project_root=PROJECT_ROOT,
        )
    return {
        "class_name": class_name,
        "file_path": rel,
        "editable": editable,
        "updated_at": _mtime_iso(path),
        "content": content,
        "store": "file",
    }


@router.put("/strategies/{class_name}/source")
def put_strategy_source(
    class_name: str,
    body: StrategySourceBody,
    user: User = Depends(require_admin),
) -> dict:
    _ = user
    engine = _cta()
    path = _resolve_source_path(engine, class_name, for_write=True)
    _STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    rel = str(path.relative_to(PROJECT_ROOT.resolve()))
    try:
        path.write_text(body.content, encoding="utf-8")
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"写入失败: {exc}") from exc
    strategy_store.save_strategy_source(
        class_name=class_name,
        content=body.content,
        file_name=path.name,
        file_path=rel,
        module=getattr(getattr(engine, "classes", {}).get(class_name), "__module__", "") or "",
        editable=True,
    )
    reloaded = False
    if body.reload:
        try:
            engine.load_strategy_class()
            reloaded = True
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"保存成功但重新加载失败: {exc}") from exc
    return {
        "ok": True,
        "class_name": class_name,
        "file_path": rel,
        "updated_at": _mtime_iso(path),
        "reloaded": reloaded,
        "store": "mysql",
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
    if body.strategy_name in engine.strategies:
        raise HTTPException(status_code=400, detail="策略实例名称已存在")
    if body.class_name not in engine.classes:
        raise HTTPException(status_code=400, detail=f"找不到策略类 {body.class_name}")
    engine.add_strategy(body.class_name, body.strategy_name, body.vt_symbol, body.setting)
    if body.strategy_name not in engine.strategies:
        raise HTTPException(status_code=400, detail="创建策略失败，请查看 CTA 日志")
    strategy_store.upsert_instance_meta(
        strategy_name=body.strategy_name,
        strategy_class=body.class_name,
        vt_symbol=body.vt_symbol,
        params=body.setting,
        status="stopped",
        user_id=user.id,
    )
    return {"ok": True, "strategy_name": body.strategy_name}


@router.patch("/instances/{name}")
def edit_instance(name: str, body: InstanceEdit, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    engine.edit_strategy(name, body.setting)
    strategy = engine.strategies.get(name)
    if strategy is not None:
        strategy_store.upsert_instance_meta(
            strategy_name=name,
            strategy_class=strategy.__class__.__name__,
            vt_symbol=getattr(strategy, "vt_symbol", ""),
            params=body.setting,
            status="trading" if getattr(strategy, "trading", False) else "stopped",
            user_id=user.id,
        )
    return {"ok": True}


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
    _cta().init_all_strategies()
    return {"ok": True}


@router.post("/instances/start-all")
def start_all(user: User = Depends(require_admin)) -> dict:
    _ = user
    _cta().start_all_strategies()
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
    engine.init_strategy(name)
    return {"ok": True}


@router.post("/instances/{name}/start")
def start_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    engine.start_strategy(name)
    return {"ok": True}


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
