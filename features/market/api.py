"""Contracts, subscribe, session ticks, historical bars (docs/06 F7 / B10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from vnpy.trader.constant import Exchange
from vnpy.trader.object import SubscribeRequest

from core.clickhouse import list_stored_dates, query_ticks
from core.db import User
from core.deps import current_user, visible_gateways
from core.runtime import runtime
from core.serialize import contract_payload, tick_payload
from core.sessions import current_trade_date, parse_trade_date, recent_trade_dates
from features.market.bars import INTERVALS, HistorySource, fetch_bars
from features.market.tick_buffer import session_ticks

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


def _visible_ticks(rows: list[dict], gws: set[str]) -> list[dict]:
    allowed = {str(name).upper() for name in gws}
    return [
        row
        for row in rows
        if not row.get("gateway_name") or str(row.get("gateway_name")).upper() in allowed
    ]


def _merge_ticks(*groups: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for group in groups:
        for row in group:
            key = (
                f"{row.get('datetime') or ''}|"
                f"{row.get('last_price')}|{row.get('volume')}|{row.get('last_volume')}"
            )
            merged[key] = row
    return sorted(merged.values(), key=lambda row: str(row.get("datetime") or ""))


@router.get("/api/market/trade-dates")
def list_trade_dates(
    symbol: str = "",
    exchange: str = "",
    user: User = Depends(current_user),
) -> dict:
    """Last 10 weekday 交易日 for the 分时 day picker."""
    _ = user
    dates = recent_trade_dates(10, exchange=exchange)
    current = current_trade_date(exchange)
    stored = list_stored_dates(symbol, exchange, dates) if symbol and exchange else set()
    ch_ok = stored is not None
    have = stored or set()
    return {
        "current": current.isoformat(),
        "clickhouse": "ok" if ch_ok else "down",
        "dates": [
            {
                "date": day.isoformat(),
                "is_current": day == current,
                "has_data": day == current or day in have,
            }
            for day in dates
        ],
    }


def _oms_ticks(symbol: str, exchange: str, gws: set[str]) -> list[dict]:
    want_ex = exchange.upper()
    want_sym = symbol.upper()
    rows: list[dict] = []
    for tick in runtime.oms.get_all_ticks():
        if tick.gateway_name not in gws:
            continue
        ex = getattr(getattr(tick, "exchange", None), "name", str(getattr(tick, "exchange", "")))
        if str(tick.symbol).upper() == want_sym and str(ex).upper() == want_ex:
            rows.append(tick_payload(tick))
    return rows


@router.get("/api/market/session-ticks")
def list_session_ticks(
    symbol: str,
    exchange: str,
    trade_date: str | None = None,
    user: User = Depends(current_user),
) -> dict:
    """Ticks for one 交易日: today = memory + OMS + ClickHouse; past days = ClickHouse."""
    gws = set(visible_gateways(user))
    current = current_trade_date(exchange)
    td = parse_trade_date(trade_date) or current
    mem = _visible_ticks(session_ticks(symbol, exchange, td), gws) if td == current else []
    oms = _oms_ticks(symbol, exchange, gws) if td == current else []
    ch_rows = query_ticks(symbol, exchange, td)
    ch_ok = ch_rows is not None
    visible_ch = _visible_ticks(ch_rows or [], gws)
    return {
        "trade_date": td.isoformat(),
        "is_current": td == current,
        "clickhouse": "ok" if ch_ok else "down",
        "ticks": _merge_ticks(visible_ch, mem, oms),
    }


@router.get("/api/market/bars")
def list_bars(
    symbol: str,
    exchange: str,
    interval: str = Query("1d"),
    source: HistorySource = Query("mock"),
    user: User = Depends(current_user),
) -> dict:
    """Historical K-line. Default mock; source=rqdata is the future RQData plug-in."""
    _ = user
    if interval not in INTERVALS:
        raise HTTPException(status_code=400, detail=f"invalid interval: {interval}")
    last_price = _last_price(symbol, exchange)
    try:
        return fetch_bars(
            symbol,
            exchange,
            interval,  # type: ignore[arg-type]
            source=source,
            last_price=last_price,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc


def _last_price(symbol: str, exchange: str) -> float | None:
    want_ex = exchange.upper()
    want_sym = symbol.upper()
    for tick in runtime.oms.get_all_ticks():
        ex = getattr(getattr(tick, "exchange", None), "name", str(getattr(tick, "exchange", "")))
        if str(tick.symbol).upper() == want_sym and str(ex).upper() == want_ex:
            price = float(getattr(tick, "last_price", 0) or 0)
            return price if price > 0 else None
    return None


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


@router.post("/api/market/unsubscribe")
def unsubscribe(body: SubscribeBody, user: User = Depends(current_user)) -> dict:
    """Stop CTP market-data for one contract (vnpy BaseGateway has no unsubscribe)."""
    if body.gateway_name not in visible_gateways(user):
        raise HTTPException(status_code=403, detail="无权限退订该账户")
    try:
        Exchange[body.exchange.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"invalid exchange: {body.exchange}") from exc

    gateway = runtime.me.get_gateway(body.gateway_name)
    if gateway is None:
        raise HTTPException(status_code=404, detail="账户不存在")

    symbol = body.symbol
    md_api = getattr(gateway, "md_api", None)
    if md_api is not None:
        subscribed = getattr(md_api, "subscribed", None)
        if isinstance(subscribed, set):
            subscribed.discard(symbol)
        if bool(getattr(md_api, "login_status", False)):
            unsub = getattr(md_api, "unSubscribeMarketData", None)
            if callable(unsub):
                unsub(symbol)
    return {"ok": True}
