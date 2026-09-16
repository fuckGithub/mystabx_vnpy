"""CTA strategy REST API — admin write / user read (docs/09 阶段 A/D)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core.db import User
from core.deps import current_user, require_admin
from core.runtime import runtime
from core.serialize import cta_stop_order_payload, cta_strategy_payload

router = APIRouter(prefix="/api/cta", tags=["cta"])


def _cta():
    engine = runtime.cta
    if engine is None:
        raise HTTPException(status_code=503, detail="CTA 引擎未加载（缺少 vnpy_ctastrategy）")
    return engine


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
    engine = _cta()
    skip = {"EliteCtaTemplate", "CtaTemplate", "TargetPosTemplate"}
    rows = []
    for name in engine.get_all_strategy_class_names():
        if name in skip:
            continue
        try:
            params = engine.get_strategy_class_parameters(name)
        except Exception:
            params = {}
        rows.append({"class_name": name, "parameters": params})
    return rows


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
