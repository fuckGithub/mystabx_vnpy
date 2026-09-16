"""Orders / positions / trades + place / cancel (docs/03, docs/06 B10/B11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from vnpy.trader.constant import Direction, Exchange, Offset, OrderType
from vnpy.trader.object import OrderRequest

from core.db import User
from core.deps import current_user, visible_gateways
from core.metrics import metrics
from core.runtime import runtime
from core.serialize import order_payload, position_payload, trade_payload

router = APIRouter(tags=["trade"])

_OFFSET = {item.name: item for item in Offset}
_DIRECTION = {item.name: item for item in Direction}
_ORDER_TYPE = {item.name: item for item in OrderType}
_EXCHANGE = {item.name: item for item in Exchange}


def _enum(mapping: dict, value: str, label: str):
    key = value.upper().replace("-", "_")
    if key in mapping:
        return mapping[key]
    compact = key.replace("_", "")
    for name, item in mapping.items():
        if name.replace("_", "") == compact:
            return item
    raise HTTPException(status_code=400, detail=f"invalid {label}: {value}")


class OrderBody(BaseModel):
    gateway_name: str
    symbol: str
    exchange: str
    direction: str
    offset: str = "OPEN"
    type: str = "LIMIT"
    price: float = 0
    volume: float = Field(gt=0)


class CancelBody(BaseModel):
    vt_orderid: str
    gateway_name: str


def _filter(user: User, items, payload_fn):
    gws = set(visible_gateways(user))
    return [payload_fn(item) for item in items if item.gateway_name in gws]


@router.get("/api/positions")
def list_positions(user: User = Depends(current_user)) -> list[dict]:
    return _filter(user, runtime.oms.get_all_positions(), position_payload)


@router.get("/api/orders")
def list_orders(user: User = Depends(current_user), active: bool = False) -> list[dict]:
    orders = runtime.oms.get_all_active_orders() if active else runtime.oms.get_all_orders()
    return _filter(user, orders, order_payload)


@router.get("/api/trades")
def list_trades(user: User = Depends(current_user)) -> list[dict]:
    return _filter(user, runtime.oms.get_all_trades(), trade_payload)


@router.post("/api/orders")
def send_order(body: OrderBody, user: User = Depends(current_user)) -> dict:
    if body.gateway_name not in visible_gateways(user):
        raise HTTPException(status_code=403, detail="无权限在该账户下单")
    exchange = _enum(_EXCHANGE, body.exchange, "exchange")
    request = OrderRequest(
        symbol=body.symbol,
        exchange=exchange,
        direction=_enum(_DIRECTION, body.direction, "direction"),
        type=_enum(_ORDER_TYPE, body.type, "type"),
        price=body.price,
        volume=body.volume,
        offset=_enum(_OFFSET, body.offset, "offset"),
        reference=f"web:{user.id}",
    )
    vt_orderid = runtime.me.send_order(request, body.gateway_name)
    if not vt_orderid:
        raise HTTPException(status_code=400, detail="下单失败：网关未连接")
    metrics.observe_tick_to_trade(body.symbol, exchange.name)
    return {"vt_orderid": vt_orderid}


@router.post("/api/orders/cancel")
def cancel_order(body: CancelBody, user: User = Depends(current_user)) -> dict:
    if body.gateway_name not in visible_gateways(user):
        raise HTTPException(status_code=403, detail="无权限撤单")
    order = runtime.oms.get_order(body.vt_orderid)
    if not order or order.gateway_name != body.gateway_name:
        raise HTTPException(status_code=404, detail="委托不存在")
    runtime.me.cancel_order(order.create_cancel_request(), body.gateway_name)
    return {"ok": True}
