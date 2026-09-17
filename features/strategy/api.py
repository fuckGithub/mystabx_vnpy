"""CTA strategy REST API — admin write / user read (docs/09 阶段 A/D)."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import User
from core.deps import current_user, require_admin
from core.runtime import runtime
from core.serialize import cta_stop_order_payload, cta_strategy_payload
from core.strategy_names import strategy_display_name

router = APIRouter(prefix="/api/cta", tags=["cta"])

_SKIP_CLASSES = {"EliteCtaTemplate", "CtaTemplate", "TargetPosTemplate"}


def _cta():
    engine = runtime.cta
    if engine is None:
        raise HTTPException(status_code=503, detail="CTA 引擎未加载（缺少 vnpy_ctastrategy）")
    return engine


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _strategy_file_meta(engine, class_name: str) -> dict:
    """Resolve module / source file for a loaded CtaTemplate class (VeighNa-style)."""
    cls = getattr(engine, "classes", {}).get(class_name)
    module = getattr(cls, "__module__", "") or "" if cls is not None else ""
    file_name = ""
    file_path = ""
    if cls is not None:
        try:
            path = Path(inspect.getfile(cls)).resolve()
            file_name = path.name
            cwd = Path.cwd().resolve()
            try:
                file_path = str(path.relative_to(cwd))
            except ValueError:
                file_path = str(path)
        except (TypeError, OSError):
            pass
    if not file_name and class_name:
        file_name = f"{_camel_to_snake(class_name)}.py"
        if not file_path:
            file_path = f"strategies/{file_name}"
    return {"module": module, "file_name": file_name, "file_path": file_path}


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


class InstanceCreate(BaseModel):
    class_name: str
    strategy_name: str
    vt_symbol: str
    setting: dict = Field(default_factory=dict)


class InstanceEdit(BaseModel):
    setting: dict = Field(default_factory=dict)


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

@router.get("/instances")
def list_instances(user: User = Depends(current_user)) -> list[dict]:
    _ = user
    engine = _cta()
    return [cta_strategy_payload(s) for s in engine.strategies.values()]


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
    return {"ok": True, "strategy_name": body.strategy_name}


@router.patch("/instances/{name}")
def edit_instance(name: str, body: InstanceEdit, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    engine.edit_strategy(name, body.setting)
    return {"ok": True}


@router.delete("/instances/{name}")
def remove_instance(name: str, user: User = Depends(require_admin)) -> dict:
    _ = user
    engine = _cta()
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="策略实例不存在")
    ok = engine.remove_strategy(name)
    if not ok:
        raise HTTPException(status_code=400, detail="移除失败（请先停止策略）")
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
