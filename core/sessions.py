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
    """Loose [start, end) bounding box for one 交易日 (may span a weekend).

    Prefer ``session_segments`` / ``in_session_for_trade_date`` for filtering —
    this box alone includes Sat/Sun idle hours between Friday night and Monday
    day, which would pollute 分时 if used as the only gate.
    """
    end = datetime.combine(trade_date, time(15, 15), tzinfo=SHANGHAI)
    if is_cffex(exchange):
        start = datetime.combine(trade_date, time(9, 15), tzinfo=SHANGHAI)
        return start, end
    prev = prev_weekday(trade_date - timedelta(days=1))
    start = datetime.combine(prev, _NIGHT_OPEN, tzinfo=SHANGHAI)
    return start, end


def session_segments(trade_date: date, *, exchange: str = "") -> list[tuple[datetime, datetime]]:
    """Exact trading segments [start, end) for one 交易日.

    Commodity Monday includes Friday 21:00–Saturday 02:30 and Monday day
    session — not Saturday/Sunday day hours. CFFEX is day-only on trade_date.
    """
    if is_cffex(exchange):
        return [
            (
                datetime.combine(trade_date, time(9, 30), tzinfo=SHANGHAI),
                datetime.combine(trade_date, time(11, 30), tzinfo=SHANGHAI),
            ),
            (
                datetime.combine(trade_date, time(13, 0), tzinfo=SHANGHAI),
                datetime.combine(trade_date, time(15, 0), tzinfo=SHANGHAI),
            ),
        ]
    prev = prev_weekday(trade_date - timedelta(days=1))
    night_end_day = prev + timedelta(days=1)
    return [
        (
            datetime.combine(prev, time(21, 0), tzinfo=SHANGHAI),
            datetime.combine(night_end_day, time(0, 0), tzinfo=SHANGHAI),
        ),
        (
            datetime.combine(night_end_day, time(0, 0), tzinfo=SHANGHAI),
            datetime.combine(night_end_day, time(2, 30), tzinfo=SHANGHAI),
        ),
        (
            datetime.combine(trade_date, time(9, 0), tzinfo=SHANGHAI),
            datetime.combine(trade_date, time(10, 15), tzinfo=SHANGHAI),
        ),
        (
            datetime.combine(trade_date, time(10, 30), tzinfo=SHANGHAI),
            datetime.combine(trade_date, time(11, 30), tzinfo=SHANGHAI),
        ),
        (
            datetime.combine(trade_date, time(13, 30), tzinfo=SHANGHAI),
            datetime.combine(trade_date, time(15, 0), tzinfo=SHANGHAI),
        ),
    ]


def in_session_for_trade_date(
    dt: datetime | None,
    trade_date: date,
    *,
    exchange: str = "",
    include_auction: bool = True,
) -> bool:
    """True when ``dt`` falls inside a real auction/trading segment of trade_date."""
    now = as_shanghai(dt)
    if now is None:
        return False
    segments = session_segments(trade_date, exchange=exchange)
    if include_auction and is_cffex(exchange):
        segments = [
            (
                datetime.combine(trade_date, time(9, 15), tzinfo=SHANGHAI),
                datetime.combine(trade_date, time(9, 30), tzinfo=SHANGHAI),
            ),
            *segments,
        ]
    elif include_auction and not is_cffex(exchange):
        prev = prev_weekday(trade_date - timedelta(days=1))
        segments = [
            (
                datetime.combine(prev, _NIGHT_OPEN, tzinfo=SHANGHAI),
                datetime.combine(prev, time(21, 0), tzinfo=SHANGHAI),
            ),
            *segments,
        ]
    return any(start <= now < end for start, end in segments)


def session_start(now: datetime | None = None, *, exchange: str = "") -> datetime:
    td = current_trade_date(exchange, now)
    return session_range(td, exchange=exchange)[0]
