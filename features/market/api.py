"""Contracts and subscribe (docs/06 F7 / B10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from vnpy.trader.constant import Exchange
from vnpy.trader.object import SubscribeRequest

from core.db import User
from core.deps import current_user, visible_gateways
from core.runtime import runtime
from core.serialize import contract_payload, tick_payload

router = APIRouter(tags=["market"])


class SubscribeBody(BaseModel):
    gateway_name: str
    symbol: str
    exchange: str


@router.get("/api/contracts")
def list_contracts(user: User = Depends(current_user), q: str = "") -> list[dict]:
    gws = set(visible_gateways(user))
    keyword = q.strip().lower()
    rows = []
    for contract in runtime.oms.get_all_contracts():
        if contract.gateway_name not in gws:
            continue
        payload = contract_payload(contract)
        blob = f"{payload['symbol']} {payload['name']} {payload['exchange']}".lower()
        if keyword and keyword not in blob:
            continue
        rows.append(payload)
    return rows[:500]


@router.get("/api/ticks")
def list_ticks(user: User = Depends(current_user)) -> list[dict]:
    gws = set(visible_gateways(user))
    return [tick_payload(t) for t in runtime.oms.get_all_ticks() if t.gateway_name in gws]


@router.post("/api/market/subscribe")
def subscribe(body: SubscribeBody, user: User = Depends(current_user)) -> dict:
    if body.gateway_name not in visible_gateways(user):
        raise HTTPException(status_code=403, detail="无权限订阅该账户")
    try:
        exchange = Exchange[body.exchange.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"invalid exchange: {body.exchange}") from exc
    runtime.me.subscribe(SubscribeRequest(symbol=body.symbol, exchange=exchange), body.gateway_name)
    return {"ok": True}
