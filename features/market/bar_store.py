"""MySQL market_bars: upsert + query for local K-line replay."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert

from core.db import MarketBar, _now, get_session

logger = logging.getLogger("stabx.bar_store")


def upsert_bars(rows: list[dict[str, Any]]) -> int:
    """Idempotent upsert by (symbol, exchange, interval, bar_time). Returns row count."""
    if not rows:
        return 0
    payload: list[dict[str, Any]] = []
    stamp = _now()
    for row in rows:
        sym = str(row.get("symbol") or "").strip()
        ex = str(row.get("exchange") or "").strip().upper()
        interval = str(row.get("interval") or "").strip()
        bar_time = str(row.get("bar_time") or row.get("datetime") or "").strip()
        trade_date = str(row.get("trade_date") or "")[:10]
        if not sym or not ex or not interval or not bar_time:
            continue
        payload.append(
            {
                "symbol": sym,
                "exchange": ex,
                "interval": interval,
                "trade_date": trade_date,
                "bar_time": bar_time,
                "open": float(row.get("open") or 0),
                "high": float(row.get("high") or 0),
                "low": float(row.get("low") or 0),
                "close": float(row.get("close") or 0),
                "volume": float(row.get("volume") or 0),
                "turnover": float(row.get("turnover") or 0),
                "open_interest": float(row.get("open_interest") or 0),
                "updated_at": stamp,
            }
        )
    if not payload:
        return 0
    db = get_session()
    try:
        stmt = mysql_insert(MarketBar).values(payload)
        update = {
            "trade_date": stmt.inserted.trade_date,
            "open": stmt.inserted.open,
            "high": stmt.inserted.high,
            "low": stmt.inserted.low,
            "close": stmt.inserted.close,
            "volume": stmt.inserted.volume,
            "turnover": stmt.inserted.turnover,
            "open_interest": stmt.inserted.open_interest,
            "updated_at": stmt.inserted.updated_at,
        }
        db.execute(stmt.on_duplicate_key_update(**update))
        db.commit()
        return len(payload)
    except Exception:
        db.rollback()
        logger.exception("upsert market_bars failed (%s rows)", len(payload))
        return 0
    finally:
        db.close()


def query_bars(
    symbol: str,
    exchange: str,
    interval: str,
    *,
    limit: int = 500,
    trade_date: date | str | None = None,
) -> list[dict[str, Any]]:
    sym = symbol.strip()
    ex = exchange.strip().upper()
    iv = interval.strip()
    db = get_session()
    try:
        stmt = (
            select(MarketBar)
            .where(
                MarketBar.symbol == sym,
                MarketBar.exchange == ex,
                MarketBar.interval == iv,
            )
            .order_by(MarketBar.bar_time.desc())
            .limit(max(1, min(limit, 5000)))
        )
        if trade_date is not None:
            td = trade_date.isoformat() if isinstance(trade_date, date) else str(trade_date)[:10]
            stmt = stmt.where(MarketBar.trade_date == td)
        rows = list(db.scalars(stmt))
        rows.reverse()
        return [_bar_dict(row) for row in rows]
    finally:
        db.close()


def count_bars(symbol: str, exchange: str, interval: str) -> int:
    from sqlalchemy import func

    db = get_session()
    try:
        return int(
            db.scalar(
                select(func.count())
                .select_from(MarketBar)
                .where(
                    MarketBar.symbol == symbol.strip(),
                    MarketBar.exchange == exchange.strip().upper(),
                    MarketBar.interval == interval.strip(),
                )
            )
            or 0
        )
    finally:
        db.close()


def list_bar_contracts() -> list[tuple[str, str]]:
    """Distinct (symbol, exchange) already stored or to be filled."""
    db = get_session()
    try:
        rows = db.execute(
            select(MarketBar.symbol, MarketBar.exchange).distinct()
        ).all()
        return [(str(r[0]), str(r[1])) for r in rows]
    finally:
        db.close()


def _bar_dict(row: MarketBar) -> dict[str, Any]:
    return {
        "datetime": row.bar_time,
        "trade_date": row.trade_date,
        "open": round(float(row.open), 4),
        "high": round(float(row.high), 4),
        "low": round(float(row.low), 4),
        "close": round(float(row.close), 4),
        "volume": round(float(row.volume), 0),
        "turnover": round(float(row.turnover), 2),
        "open_interest": round(float(row.open_interest), 0),
    }
