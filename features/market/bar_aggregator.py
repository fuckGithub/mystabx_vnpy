"""Aggregate ClickHouse session ticks → MySQL market_bars (1m + 1d)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from core.clickhouse import query_ticks
from core.serialize import SHANGHAI, dt_iso
from core.sessions import current_trade_date, parse_tick_dt, recent_trade_dates
from features.market.bar_store import upsert_bars

logger = logging.getLogger("stabx.bar_aggregator")


def _f(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    if n != n:
        return 0.0
    return n


def ticks_to_minute_bars(
    ticks: list[dict[str, Any]],
    *,
    symbol: str,
    exchange: str,
    trade_date: date,
) -> list[dict[str, Any]]:
    """Build 1m OHLCV from session ticks (cumulative volume → per-minute delta)."""
    buckets: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    prev_cum = 0.0
    prev_turnover = 0.0

    sorted_ticks = sorted(
        ticks,
        key=lambda row: (
            parse_tick_dt(row.get("datetime")) or datetime.min.replace(tzinfo=SHANGHAI)
        ).timestamp(),
    )
    for row in sorted_ticks:
        dt = parse_tick_dt(row.get("datetime"))
        price = _f(row.get("last_price"))
        if dt is None or price <= 0:
            continue
        key = dt.strftime("%Y-%m-%dT%H:%M:00")
        cum = _f(row.get("volume"))
        turnover = _f(row.get("turnover"))
        last_vol = _f(row.get("last_volume"))
        if last_vol > 0:
            delta = last_vol
        elif cum >= prev_cum:
            delta = cum - prev_cum
        else:
            delta = 0.0
        turn_delta = max(0.0, turnover - prev_turnover) if turnover >= prev_turnover else 0.0
        if cum > 0:
            prev_cum = cum
        if turnover > 0:
            prev_turnover = turnover
        oi = _f(row.get("open_interest"))
        bar_time = dt.replace(second=0, microsecond=0)
        if key not in buckets:
            order.append(key)
            buckets[key] = {
                "symbol": symbol,
                "exchange": exchange,
                "interval": "1m",
                "trade_date": trade_date.isoformat(),
                "bar_time": dt_iso(bar_time) or key,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": delta,
                "turnover": turn_delta,
                "open_interest": oi,
            }
        else:
            b = buckets[key]
            b["high"] = max(b["high"], price)
            b["low"] = min(b["low"], price) if b["low"] > 0 else price
            b["close"] = price
            b["volume"] += delta
            b["turnover"] += turn_delta
            if oi > 0:
                b["open_interest"] = oi
    return [buckets[k] for k in order]


def minute_bars_to_daily(minute_bars: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not minute_bars:
        return None
    first = minute_bars[0]
    high = max(_f(b.get("high")) for b in minute_bars)
    low_vals = [_f(b.get("low")) for b in minute_bars if _f(b.get("low")) > 0]
    low = min(low_vals) if low_vals else _f(first.get("open"))
    close = _f(minute_bars[-1].get("close"))
    volume = sum(_f(b.get("volume")) for b in minute_bars)
    turnover = sum(_f(b.get("turnover")) for b in minute_bars)
    oi = _f(minute_bars[-1].get("open_interest"))
    trade_date = str(first.get("trade_date") or "")[:10]
    # Day bar timestamp = trade_date 15:00 Shanghai
    try:
        td = date.fromisoformat(trade_date)
        bar_dt = datetime(td.year, td.month, td.day, 15, 0, tzinfo=SHANGHAI)
        bar_time = dt_iso(bar_dt) or f"{trade_date}T15:00:00.000+08:00"
    except ValueError:
        bar_time = str(first.get("bar_time") or "")
    return {
        "symbol": first.get("symbol"),
        "exchange": first.get("exchange"),
        "interval": "1d",
        "trade_date": trade_date,
        "bar_time": bar_time,
        "open": _f(first.get("open")),
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "turnover": turnover,
        "open_interest": oi,
    }


def resample_minutes(
    minute_bars: list[dict[str, Any]],
    *,
    minutes: int,
    interval: str,
) -> list[dict[str, Any]]:
    if minutes <= 1 or not minute_bars:
        return minute_bars
    out: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal bucket
        if not bucket:
            return
        first = bucket[0]
        high = max(_f(b.get("high")) for b in bucket)
        low_vals = [_f(b.get("low")) for b in bucket if _f(b.get("low")) > 0]
        out.append(
            {
                "symbol": first.get("symbol"),
                "exchange": first.get("exchange"),
                "interval": interval,
                "trade_date": first.get("trade_date"),
                "bar_time": first.get("bar_time"),
                "open": _f(first.get("open")),
                "high": high,
                "low": min(low_vals) if low_vals else _f(first.get("open")),
                "close": _f(bucket[-1].get("close")),
                "volume": sum(_f(b.get("volume")) for b in bucket),
                "turnover": sum(_f(b.get("turnover")) for b in bucket),
                "open_interest": _f(bucket[-1].get("open_interest")),
            }
        )
        bucket = []

    for bar in minute_bars:
        dt = parse_tick_dt(bar.get("bar_time") or bar.get("datetime"))
        if dt is None:
            continue
        minute_index = dt.hour * 60 + dt.minute
        # Align to wall-clock multiples; session gaps start a new bucket.
        aligned = minute_index - (minute_index % minutes)
        key = (dt.date().isoformat(), aligned)
        if bucket:
            prev = parse_tick_dt(bucket[-1].get("bar_time"))
            prev_key = None
            if prev is not None:
                pm = prev.hour * 60 + prev.minute
                prev_key = (prev.date().isoformat(), pm - (pm % minutes))
            if prev_key != key:
                flush()
        if not bucket:
            # Rewrite open time to bucket start
            start = dt.replace(second=0, microsecond=0) - timedelta(
                minutes=dt.minute % minutes
            )
            bar = {**bar, "bar_time": dt_iso(start) or bar.get("bar_time")}
        bucket.append(bar)
    flush()
    return out


def aggregate_contract_day(symbol: str, exchange: str, trade_date: date) -> dict[str, int]:
    """Pull ticks for one 交易日, write 1m (+ 1d) into MySQL."""
    ticks = query_ticks(symbol, exchange, trade_date)
    if ticks is None:
        return {"ticks": 0, "1m": 0, "1d": 0, "clickhouse": 0}
    if not ticks:
        return {"ticks": 0, "1m": 0, "1d": 0, "clickhouse": 1}
    minute = ticks_to_minute_bars(ticks, symbol=symbol, exchange=exchange, trade_date=trade_date)
    written_m = upsert_bars(minute)
    daily = minute_bars_to_daily(minute)
    written_d = upsert_bars([daily]) if daily else 0
    # Also materialize common intraday intervals for faster replay.
    extras = 0
    for minutes, iv in ((5, "5m"), (15, "15m"), (30, "30m"), (60, "60m")):
        extras += upsert_bars(
            resample_minutes(minute, minutes=minutes, interval=iv)
        )
    return {
        "ticks": len(ticks),
        "1m": written_m,
        "1d": written_d,
        "intraday": extras,
        "clickhouse": 1,
    }


def subscribed_contracts() -> list[tuple[str, str]]:
    """Unique (symbol, exchange) from persisted subscriptions."""
    from core.db import MarketSubscription, get_session
    from sqlalchemy import select

    db = get_session()
    try:
        rows = db.execute(
            select(MarketSubscription.symbol, MarketSubscription.exchange).distinct()
        ).all()
        return [(str(r[0]), str(r[1]).upper()) for r in rows if r[0] and r[1]]
    finally:
        db.close()


def aggregate_recent(
    *,
    days: int = 5,
    contracts: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Aggregate last N weekdays for each contract (idempotent upsert)."""
    pairs = contracts or subscribed_contracts()
    if not pairs:
        return {"contracts": 0, "days": 0, "results": []}
    results: list[dict[str, Any]] = []
    dates = recent_trade_dates(max(1, days))
    for symbol, exchange in pairs:
        for td in dates:
            # Skip future empty current day mid-weekend if no ticks — still try.
            stats = aggregate_contract_day(symbol, exchange, td)
            results.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "trade_date": td.isoformat(),
                    **stats,
                }
            )
            if stats.get("1m"):
                logger.info(
                    "bars upsert %s.%s %s 1m=%s 1d=%s",
                    symbol,
                    exchange,
                    td.isoformat(),
                    stats.get("1m"),
                    stats.get("1d"),
                )
    return {"contracts": len(pairs), "days": len(dates), "results": results}


def aggregate_current_trade_dates() -> dict[str, Any]:
    """Refresh bars for the current 交易日 of each subscribed contract."""
    pairs = subscribed_contracts()
    results: list[dict[str, Any]] = []
    for symbol, exchange in pairs:
        td = current_trade_date(exchange)
        stats = aggregate_contract_day(symbol, exchange, td)
        results.append(
            {"symbol": symbol, "exchange": exchange, "trade_date": td.isoformat(), **stats}
        )
    return {"contracts": len(pairs), "results": results}
