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
from core.sessions import current_trade_date, in_session_for_trade_date, parse_tick_dt, parse_trade_date, recent_trade_dates
from features.market.bars import INTERVALS, HistorySource, fetch_bars
from features.market.bar_aggregator import aggregate_recent
from features.market.subscriptions import (
    delete_subscription,
    list_user_subscriptions,
    upsert_subscription,
)
from features.market.tick_buffer import normalize_live_tick, session_ticks

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


def _downsample_to_minute(ticks: list[dict]) -> list[dict]:
    """Keep the last tick of each minute.

    Full SimNow tapes are 10k–70k rows / day (~MB JSON). The 分时 chart only
    needs minute buckets; shipping every tick made the browser sit on a single
    OMS snapshot (one blue dot + one fat volume bar) while the request crawled.
    Always bucket — even a few hundred rows — so first paint stays small.
    """
    if len(ticks) <= 1:
        return ticks
    buckets: dict[str, dict] = {}
    order: list[str] = []
    for row in ticks:
        dt = parse_tick_dt(row.get("datetime"))
        if dt is None:
            key = f"raw|{row.get('datetime')}|{row.get('last_price')}"
        else:
            key = dt.strftime("%Y-%m-%dT%H:%M")
        if key not in buckets:
            order.append(key)
        # Prefer the later print in the minute; keep the higher cumulative volume
        # so minute-to-minute delta still works on the client.
        prev = buckets.get(key)
        nxt = dict(row)
        nxt["last_volume"] = 0
        if prev is not None:
            try:
                if float(prev.get("volume") or 0) > float(nxt.get("volume") or 0):
                    nxt["volume"] = prev.get("volume")
            except (TypeError, ValueError):
                pass
        buckets[key] = nxt
    return [buckets[key] for key in order]


def _filter_session_clock(ticks: list[dict], exchange: str, trade_date) -> list[dict]:
    """Keep ticks inside real auction/trading segments (drop Fri→Mon idle hours)."""
    out: list[dict] = []
    for row in ticks:
        dt = parse_tick_dt(row.get("datetime"))
        if dt is None:
            if row.get("last_price"):
                out.append(row)
            continue
        if in_session_for_trade_date(dt, trade_date, exchange=exchange):
            out.append(row)
    return out


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
                # Do not force has_data=true for current — weekend "next Monday"
                # may only have night stubs; the UI needs an honest signal.
                "has_data": day in have,
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
    # Memory / ClickHouse rows are public market ticks for the contract. Do not
    # drop them when gateway_name differs (reconnect / renamed account) — that
    # left the UI with a single OMS snapshot and a flat 分时 line.
    mem = session_ticks(symbol, exchange, td) if td == current else []
    oms_raw = [normalize_live_tick(row) for row in _oms_ticks(symbol, exchange, gws)] if td == current else []
    # OMS snapshots are often re-stamped to "now" (weekend / frozen SimNow clock).
    # Merging them after session filter used to inject one out-of-session print
    # with full cumulative volume → single fat volume bar under a lone price pin.
    oms = [
        row
        for row in oms_raw
        if in_session_for_trade_date(parse_tick_dt(row.get("datetime")), td, exchange=exchange)
    ]
    ch_rows = query_ticks(symbol, exchange, td)
    ch_ok = ch_rows is not None
    # CH already session-filtered; memory may still hold break prints — tighten.
    hist = _filter_session_clock(_merge_ticks(ch_rows or [], mem), exchange, td)
    ticks = _downsample_to_minute(_merge_ticks(hist, oms))
    return {
        "trade_date": td.isoformat(),
        "is_current": td == current,
        "clickhouse": "ok" if ch_ok else "down",
        "ticks": ticks,
    }


@router.get("/api/market/bars")
def list_bars(
    symbol: str,
    exchange: str,
    interval: str = Query("1d"),
    source: HistorySource = Query("local"),
    user: User = Depends(current_user),
) -> dict:
    """Historical K-line from local MySQL (aggregated ticks).

    Production always serves source=local. Mock requires STABX_ALLOW_MOCK_BARS=1;
    empty local returns empty bars (never silent mock fallback).
    """
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


class AggregateBarsBody(BaseModel):
    days: int = 5
    symbol: str | None = None
    exchange: str | None = None


@router.post("/api/market/bars/aggregate")
def trigger_bar_aggregate(
    body: AggregateBarsBody | None = None,
    user: User = Depends(current_user),
) -> dict:
    """Manually (re)aggregate ClickHouse ticks → MySQL market_bars."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可触发归集")
    payload = body or AggregateBarsBody()
    days = max(1, min(int(payload.days or 5), 15))
    contracts = None
    if payload.symbol and payload.exchange:
        contracts = [(payload.symbol.strip(), payload.exchange.strip().upper())]
    summary = aggregate_recent(days=days, contracts=contracts)
    return {"ok": True, **summary}

def _last_price(symbol: str, exchange: str) -> float | None:
    want_ex = exchange.upper()
    want_sym = symbol.upper()
    for tick in runtime.oms.get_all_ticks():
        ex = getattr(getattr(tick, "exchange", None), "name", str(getattr(tick, "exchange", "")))
        if str(tick.symbol).upper() == want_sym and str(ex).upper() == want_ex:
            price = float(getattr(tick, "last_price", 0) or 0)
            return price if price > 0 else None
    return None


@router.get("/api/market/subscriptions")
def list_subscriptions(user: User = Depends(current_user)) -> list[dict]:
    """Persisted subscriptions for the current user (visible gateways only)."""
    gws = set(visible_gateways(user))
    return list_user_subscriptions(user.id, gateway_names=gws)


@router.post("/api/market/subscribe")
def subscribe(body: SubscribeBody, user: User = Depends(current_user)) -> dict:
    if body.gateway_name not in visible_gateways(user):
        raise HTTPException(status_code=403, detail="无权限订阅该账户")
    try:
        exchange = Exchange[body.exchange.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"invalid exchange: {body.exchange}") from exc
    # Persist first so a CTP hiccup cannot leave the UI subscribed without a durable row.
    row = upsert_subscription(
        user_id=user.id,
        gateway_name=body.gateway_name,
        symbol=body.symbol,
        exchange=body.exchange,
    )
    runtime.me.subscribe(SubscribeRequest(symbol=body.symbol, exchange=exchange), body.gateway_name)
    return {"ok": True, "subscription": {
        "gateway_name": row.gateway_name,
        "symbol": row.symbol,
        "exchange": row.exchange,
        "name": row.name or "",
        "vt_symbol": f"{row.symbol}.{row.exchange}",
    }}


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
    delete_subscription(
        user_id=user.id,
        gateway_name=body.gateway_name,
        symbol=body.symbol,
        exchange=body.exchange,
    )
    return {"ok": True}
