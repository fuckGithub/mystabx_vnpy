"""In-memory SimNow session ticks (Asia/Shanghai). Fed from EVENT_TICK only."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date
from threading import Lock
from typing import Any

from core.sessions import (
    current_trade_date,
    parse_tick_dt,
    session_start,
    trade_date_of,
)

# ~1 tick/sec × 6h session with headroom; prune by session window anyway.
_MAX_TICKS = 24_000
_store: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=_MAX_TICKS))
_lock = Lock()


def contract_key(exchange: str, symbol: str) -> str:
    return f"{str(exchange or '').upper()}.{str(symbol or '').upper()}"


def record_tick(payload: dict[str, Any]) -> None:
    symbol = str(payload.get("symbol") or "")
    exchange = str(payload.get("exchange") or "")
    if not symbol or not exchange:
        return
    key = contract_key(exchange, symbol)
    start = session_start(parse_tick_dt(payload.get("datetime")), exchange=exchange)
    dt = parse_tick_dt(payload.get("datetime"))
    if dt is not None and dt < start:
        return
    with _lock:
        bucket = _store[key]
        bucket.append(dict(payload))
        while bucket:
            first_dt = parse_tick_dt(bucket[0].get("datetime"))
            if first_dt is None or first_dt >= start:
                break
            bucket.popleft()


def session_ticks(symbol: str, exchange: str, trade_date: date | None = None) -> list[dict[str, Any]]:
    key = contract_key(exchange, symbol)
    want = trade_date or current_trade_date(exchange)
    with _lock:
        rows = list(_store.get(key, ()))
    out: list[dict[str, Any]] = []
    for row in rows:
        dt = parse_tick_dt(row.get("datetime"))
        if dt is None:
            continue
        if trade_date_of(dt, exchange=exchange) == want:
            out.append(row)
    return out
