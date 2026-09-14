"""Web API for vnpy strategy applications (honest status + priority wiring)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from vnpy.trader.constant import Direction, Offset

from core.db import User
from core.deps import current_user
from features.apps import service as apps
from features.apps.catalog import CATALOG_BY_KEY

router = APIRouter(prefix="/api/apps", tags=["apps"])

_DIRECTION = {item.name: item for item in Direction}
_OFFSET = {item.name: item for item in Offset}


def _enum(mapping: dict, value: str, label: str):
    key = value.upper().replace("-", "_")
    if key in mapping:
        return mapping[key]
    compact = key.replace("_", "")
    for name, item in mapping.items():
        if name.replace("_", "") == compact:
            return item
    raise HTTPException(status_code=400, detail=f"invalid {label}: {value}")


class CtaAddBody(BaseModel):
    class_name: str
    strategy_name: str
    vt_symbol: str
    setting: dict[str, Any] = Field(default_factory=dict)


class BacktestBody(BaseModel):
    class_name: str
    vt_symbol: str
    interval: str = "1m"
    start: str
    end: str
    rate: float = 0.0
    slippage: float = 0.0
    size: float = 1
    pricetick: float = 0.01
    capital: float = 1_000_000
    setting: dict[str, Any] = Field(default_factory=dict)


class SymbolBody(BaseModel):
    vt_symbol: str


class RpcBody(BaseModel):
    rep_address: str = "tcp://*:2014"
    pub_address: str = "tcp://*:4102"


class PaperBody(BaseModel):
    trade_slippage: int | None = None
    timer_interval: int | None = None
    instant_trade: bool | None = None


class AlgoStartBody(BaseModel):
    template_name: str
    vt_symbol: str
    direction: str
    offset: str = "OPEN"
    price: float = 0
    volume: int = Field(gt=0)
    setting: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_apps(_: User = Depends(current_user)) -> list[dict]:
    return apps.list_statuses()


@router.get("/{key}")
def get_app(key: str, _: User = Depends(current_user)) -> dict:
    if key not in CATALOG_BY_KEY:
        raise HTTPException(status_code=404, detail="unknown app")
    return apps.status_for(key)


# ----- CTA -----


@router.get("/cta/classes")
def cta_classes(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    return {"classes": engine.get_all_strategy_class_names()}


@router.get("/cta/strategies")
def cta_strategies(_: User = Depends(current_user)) -> list[dict]:
    engine = apps.require_loaded("cta")
    return [apps.strategy_row(s) for s in engine.strategies.values()]


@router.post("/cta/strategies")
def cta_add(body: CtaAddBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    engine.add_strategy(body.class_name, body.strategy_name, body.vt_symbol, body.setting)
    return {"ok": True, "strategy_name": body.strategy_name}


@router.post("/cta/strategies/{name}/init")
def cta_init(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    engine.init_strategy(name)
    return {"ok": True}


@router.post("/cta/strategies/{name}/start")
def cta_start(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    engine.start_strategy(name)
    return {"ok": True}


@router.post("/cta/strategies/{name}/stop")
def cta_stop(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    engine.stop_strategy(name)
    return {"ok": True}


@router.delete("/cta/strategies/{name}")
def cta_remove(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("cta")
    ok = engine.remove_strategy(name)
    if not ok:
        raise HTTPException(status_code=400, detail="remove failed (stop trading first?)")
    return {"ok": True}


# ----- Backtester -----


@router.get("/backtester/classes")
def backtester_classes(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("backtester")
    return {"classes": engine.get_strategy_class_names()}


@router.post("/backtester/run")
def backtester_run(body: BacktestBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("backtester")
    started = engine.start_backtesting(
        body.class_name,
        body.vt_symbol,
        body.interval,
        apps.parse_dt(body.start),
        apps.parse_dt(body.end),
        body.rate,
        body.slippage,
        body.size,
        body.pricetick,
        body.capital,
        body.setting,
    )
    return {"ok": bool(started), "running": engine.thread is not None and engine.thread.is_alive()}


@router.get("/backtester/status")
def backtester_status(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("backtester")
    running = engine.thread is not None and engine.thread.is_alive()
    stats = engine.get_result_statistics()
    return {"running": running, "statistics": stats}


# ----- DataManager / Recorder -----


@router.get("/datamanager/overview")
def datamanager_overview(_: User = Depends(current_user)) -> list[dict]:
    engine = apps.require_loaded("datamanager")
    return [apps.bar_overview_row(row) for row in engine.get_bar_overview()]


@router.get("/recorder/recordings")
def recorder_list(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("recorder")
    return {
        "active": bool(getattr(engine, "active", False)),
        "tick": sorted(engine.tick_recordings.keys()),
        "bar": sorted(engine.bar_recordings.keys()),
    }


@router.post("/recorder/tick")
def recorder_add_tick(body: SymbolBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("recorder")
    engine.add_tick_recording(body.vt_symbol)
    return {"ok": True}


@router.delete("/recorder/tick/{vt_symbol}")
def recorder_remove_tick(vt_symbol: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("recorder")
    engine.remove_tick_recording(vt_symbol)
    return {"ok": True}


@router.post("/recorder/bar")
def recorder_add_bar(body: SymbolBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("recorder")
    engine.add_bar_recording(body.vt_symbol)
    return {"ok": True}


@router.delete("/recorder/bar/{vt_symbol}")
def recorder_remove_bar(vt_symbol: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("recorder")
    engine.remove_bar_recording(vt_symbol)
    return {"ok": True}


# ----- Risk / Algo / Paper / RPC -----


@router.get("/risk/rules")
def risk_rules(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("risk")
    names = engine.get_all_rule_names()
    return {
        "names": names,
        "rules": {name: apps.json_safe(engine.get_rule_data(name)) for name in names},
    }


@router.get("/algo/templates")
def algo_templates(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("algo")
    return {"templates": sorted(engine.algo_templates.keys())}


@router.get("/algo/algos")
def algo_list(_: User = Depends(current_user)) -> list[dict]:
    engine = apps.require_loaded("algo")
    rows = []
    for algo_name, algo in engine.algos.items():
        rows.append(
            {
                "algo_name": algo_name,
                "vt_symbol": getattr(algo, "vt_symbol", None),
                "active": bool(getattr(algo, "active", False)),
                "template": algo.__class__.__name__,
            }
        )
    return rows


@router.post("/algo/start")
def algo_start(body: AlgoStartBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("algo")
    algo_name = engine.start_algo(
        body.template_name,
        body.vt_symbol,
        _enum(_DIRECTION, body.direction, "direction"),
        _enum(_OFFSET, body.offset, "offset"),
        body.price,
        body.volume,
        body.setting,
    )
    return {"ok": True, "algo_name": algo_name}


@router.post("/algo/{algo_name}/stop")
def algo_stop(algo_name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("algo")
    engine.stop_algo(algo_name)
    return {"ok": True}


@router.get("/paper/settings")
def paper_settings(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("paper")
    return {
        "trade_slippage": engine.get_trade_slippage(),
        "timer_interval": engine.get_timer_interval(),
        "instant_trade": engine.get_instant_trade(),
    }


@router.post("/paper/settings")
def paper_update(body: PaperBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("paper")
    if body.trade_slippage is not None:
        engine.set_trade_slippage(body.trade_slippage)
    if body.timer_interval is not None:
        engine.set_timer_interval(body.timer_interval)
    if body.instant_trade is not None:
        engine.set_instant_trade(body.instant_trade)
    return paper_settings()


@router.get("/rpc/status")
def rpc_status(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("rpc")
    active = bool(engine.server.is_active()) if getattr(engine, "server", None) else False
    return {
        "active": active,
        "rep_address": getattr(engine, "rep_address", None),
        "pub_address": getattr(engine, "pub_address", None),
    }


@router.post("/rpc/start")
def rpc_start(body: RpcBody, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("rpc")
    ok = engine.start(body.rep_address, body.pub_address)
    return {"ok": ok, **rpc_status()}


@router.post("/rpc/stop")
def rpc_stop(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("rpc")
    ok = engine.stop()
    return {"ok": ok, **rpc_status()}


# ----- Status-only hooks -----


@router.get("/spread/status")
def spread_status(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("spread")
    return {"active": bool(getattr(engine, "active", False))}


@router.post("/spread/start")
def spread_start(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("spread")
    engine.start()
    return {"ok": True, "active": True}


@router.post("/spread/stop")
def spread_stop(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("spread")
    engine.stop()
    return {"ok": True, "active": False}


@router.get("/option/portfolios")
def option_portfolios(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("option")
    return {"names": engine.get_portfolio_names()}


@router.get("/portfolio/classes")
def portfolio_classes(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("portfolio")
    return {"classes": engine.get_all_strategy_class_names()}


@router.get("/portfolio/strategies")
def portfolio_strategies(_: User = Depends(current_user)) -> list[dict]:
    engine = apps.require_loaded("portfolio")
    return [apps.strategy_row(s) for s in engine.strategies.values()]


@router.post("/portfolio/strategies/{name}/start")
def portfolio_start(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("portfolio")
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    engine.start_strategy(name)
    return {"ok": True}


@router.post("/portfolio/strategies/{name}/stop")
def portfolio_stop(name: str, _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("portfolio")
    if name not in engine.strategies:
        raise HTTPException(status_code=404, detail="strategy not found")
    engine.stop_strategy(name)
    return {"ok": True}


@router.get("/portfolio_mgr/result")
def portfolio_mgr_result(reference: str = "", _: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("portfolio_mgr")
    if not reference:
        return {
            "reference": None,
            "result": None,
            "note": "传入 reference 查询；无数据时为空，不虚构盈亏。",
        }
    result = engine.get_portfolio_result(reference)
    payload = result.get_data() if hasattr(result, "get_data") else {"reference": reference}
    return {
        "reference": reference,
        "result": payload,
        "note": "数值来自引擎内存态；未交易时多为 0，不虚构盈亏曲线。",
    }


@router.get("/script/status")
def script_status(_: User = Depends(current_user)) -> dict:
    engine = apps.require_loaded("script")
    strategy_active = getattr(engine, "strategy_active", None)
    return {
        "engine": True,
        "strategy_active": bool(strategy_active) if strategy_active is not None else None,
        "note": "脚本文件由 ScriptTrader 本地目录管理；Web 仅暴露引擎状态。",
    }
