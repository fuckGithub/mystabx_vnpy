"""Asia/Shanghai futures trade dates and session windows.

Commodity night session starting 21:00 belongs to the next weekday trade date
(Friday 21:00 → Monday). CFFEX is day-only on the same calendar date.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from core.serialize import SHANGHAI

CFFEX = frozenset({"CFFEX", "CFX"})

# Night may start a few minutes early; day session ends 15:00.
_NIGHT_OPEN = time(20, 50)
_NIGHT_CUTOFF = time(3, 0)


def as_shanghai(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=SHANGHAI)
    return value.astimezone(SHANGHAI)


def parse_tick_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return as_shanghai(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return as_shanghai(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def is_cffex(exchange: str) -> bool:
    return str(exchange or "").upper() in CFFEX


def next_weekday(day: date) -> date:
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day


def prev_weekday(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def trade_date_of(dt: datetime | None, *, exchange: str = "") -> date:
    """Map a Shanghai tick time to its 交易日."""
    now = as_shanghai(dt) or datetime.now(tz=SHANGHAI)
    if is_cffex(exchange):
        return next_weekday(now.date()) if now.date().weekday() >= 5 else now.date()

    clock = now.timetz().replace(tzinfo=None) if now.tzinfo else now.time()
    if clock >= _NIGHT_OPEN:
        return next_weekday(now.date() + timedelta(days=1))
    if clock < _NIGHT_CUTOFF:
        return next_weekday(now.date())
    day = now.date()
    return next_weekday(day) if day.weekday() >= 5 else day


def current_trade_date(exchange: str = "", now: datetime | None = None) -> date:
    return trade_date_of(as_shanghai(now) or datetime.now(tz=SHANGHAI), exchange=exchange)


def recent_trade_dates(n: int = 10, *, exchange: str = "", now: datetime | None = None) -> list[date]:
    today = current_trade_date(exchange, now)
    out = [today]
    cursor = today - timedelta(days=1)
    while len(out) < n:
        if cursor.weekday() < 5:
            out.append(cursor)
        cursor -= timedelta(days=1)
        if (today - cursor).days > 40:
            break
    return out


def parse_trade_date(raw: str | date | None) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date) and not isinstance(raw, datetime):
        return raw
    text = str(raw).strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def session_range(trade_date: date, *, exchange: str = "") -> tuple[datetime, datetime]:
    """Inclusive-ish [start, end) covering night + day for one 交易日."""
    end = datetime.combine(trade_date, time(15, 15), tzinfo=SHANGHAI)
    if is_cffex(exchange):
        start = datetime.combine(trade_date, time(9, 15), tzinfo=SHANGHAI)
        return start, end
    prev = prev_weekday(trade_date - timedelta(days=1))
    start = datetime.combine(prev, _NIGHT_OPEN, tzinfo=SHANGHAI)
    return start, end


def session_start(now: datetime | None = None, *, exchange: str = "") -> datetime:
    td = current_trade_date(exchange, now)
    return session_range(td, exchange=exchange)[0]
