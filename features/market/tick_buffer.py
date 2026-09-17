"""In-memory SimNow session ticks (Asia/Shanghai). Fed from EVENT_TICK only."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime
from threading import Lock
from typing import Any

from core.serialize import SHANGHAI, dt_iso
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


def normalize_live_tick(payload: dict[str, Any]) -> dict[str, Any]:
    """Re-stamp frozen / wrong-day SimNow datetimes so 分时 can bucket by wall clock.

    Exchange last_price often keeps updating while datetime stays put; bucketing
    by that stamp collapses the session to one minute (flat line, near-zero volume).
    """
    dt = parse_tick_dt(payload.get("datetime"))
    now = datetime.now(tz=SHANGHAI)
    if dt is None:
        out = dict(payload)
        out["datetime"] = dt_iso(now)
        return out
    lag = (now - dt).total_seconds()
    if lag > 120 or lag < -60:
        out = dict(payload)
        out["datetime"] = dt_iso(now)
        return out
    return payload


def record_tick(payload: dict[str, Any]) -> None:
    symbol = str(payload.get("symbol") or "")
    exchange = str(payload.get("exchange") or "")
    if not symbol or not exchange:
        return
    key = contract_key(exchange, symbol)
    dt = parse_tick_dt(payload.get("datetime"))
    start = session_start(dt, exchange=exchange)
    priced = bool(payload.get("last_price"))
    # SimNow may stamp CFFEX quotes after 15:00 or on a prior calendar day.
    # Still keep last_price so 分时 can plot the same quote as the left list.
    if dt is not None and dt < start and not priced:
        return
    with _lock:
        bucket = _store[key]
        bucket.append(dict(payload))
        while bucket and not priced:
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
            if row.get("last_price"):
                out.append(row)
            continue
        if trade_date_of(dt, exchange=exchange) == want:
            out.append(row)
    # Stale SimNow stamps (previous calendar day / 17:xx) still carry live last_price.
    if not out and rows:
        return list(rows)
    return out
