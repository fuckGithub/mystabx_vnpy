"""vnpy BaseDatabase adapter: load bars from MySQL `market_bars` (SimNow tick 归集)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import (
    DB_TZ,
    BarOverview,
    BaseDatabase,
    TickOverview,
    convert_tz,
)
from vnpy.trader.object import BarData, TickData

from core.serialize import SHANGHAI
from core.sessions import parse_tick_dt
from features.market.bar_store import query_bars_range

logger = logging.getLogger("stabx.backtest.db")

# vnpy Interval.value ↔ market_bars.interval
_INTERVAL_TO_STORE: dict[str, tuple[str, ...]] = {
    "1m": ("1m",),
    "1h": ("1h", "60m"),
    "d": ("1d", "d"),
    "w": ("1w", "w"),
    "tick": ("tick",),
}


def _store_intervals(interval: Interval) -> tuple[str, ...]:
    key = getattr(interval, "value", str(interval))
    return _INTERVAL_TO_STORE.get(key, (key, f"1{key}" if len(key) == 1 else key))


def _to_bar(symbol: str, exchange: Exchange, interval: Interval, row: dict[str, Any]) -> BarData | None:
    raw = row.get("datetime") or row.get("bar_time")
    dt = parse_tick_dt(raw) if not isinstance(raw, datetime) else raw
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SHANGHAI)
    dt = convert_tz(dt.astimezone(DB_TZ))
    return BarData(
        symbol=symbol,
        exchange=exchange,
        datetime=dt,
        interval=interval,
        volume=float(row.get("volume") or 0),
        turnover=float(row.get("turnover") or 0),
        open_interest=float(row.get("open_interest") or 0),
        open_price=float(row.get("open") or 0),
        high_price=float(row.get("high") or 0),
        low_price=float(row.get("low") or 0),
        close_price=float(row.get("close") or 0),
        gateway_name="DB",
    )


class MarketBarsDatabase(BaseDatabase):
    """Read-focused bar store backed by business MySQL market_bars."""

    def save_bar_data(self, bars: list[BarData], stream: bool = False) -> bool:
        _ = stream
        if not bars:
            return True
        from features.market.bar_store import upsert_bars

        rows: list[dict[str, Any]] = []
        for bar in bars:
            iv = getattr(bar.interval, "value", str(bar.interval or "1m"))
            if iv == "d":
                iv = "1d"
            elif iv == "1h":
                iv = "60m"
            dt = bar.datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=DB_TZ)
            rows.append(
                {
                    "symbol": bar.symbol,
                    "exchange": bar.exchange.value if hasattr(bar.exchange, "value") else str(bar.exchange),
                    "interval": iv,
                    "trade_date": dt.astimezone(SHANGHAI).date().isoformat(),
                    "bar_time": dt.astimezone(SHANGHAI).isoformat(timespec="milliseconds"),
                    "open": bar.open_price,
                    "high": bar.high_price,
                    "low": bar.low_price,
                    "close": bar.close_price,
                    "volume": bar.volume,
                    "turnover": bar.turnover,
                    "open_interest": bar.open_interest,
                }
            )
        return upsert_bars(rows) > 0

    def save_tick_data(self, ticks: list[TickData], stream: bool = False) -> bool:
        _ = ticks, stream
        return True

    def load_bar_data(
        self,
        symbol: str,
        exchange: Exchange,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[BarData]:
        ex = exchange.value if hasattr(exchange, "value") else str(exchange)
        out: list[BarData] = []
        for iv in _store_intervals(interval):
            rows = query_bars_range(symbol, ex, iv, start=start, end=end)
            if not rows:
                continue
            for row in rows:
                bar = _to_bar(symbol, exchange, interval, row)
                if bar is not None:
                    out.append(bar)
            if out:
                break
        logger.info(
            "load_bar_data %s.%s %s %s→%s → %s bars",
            symbol,
            ex,
            getattr(interval, "value", interval),
            start,
            end,
            len(out),
        )
        return out

    def load_tick_data(
        self,
        symbol: str,
        exchange: Exchange,
        start: datetime,
        end: datetime,
    ) -> list[TickData]:
        _ = symbol, exchange, start, end
        return []

    def delete_bar_data(self, symbol: str, exchange: Exchange, interval: Interval) -> int:
        _ = symbol, exchange, interval
        return 0

    def delete_tick_data(self, symbol: str, exchange: Exchange) -> int:
        _ = symbol, exchange
        return 0

    def get_bar_overview(self) -> list[BarOverview]:
        from sqlalchemy import func, select

        from core.db import MarketBar, get_session

        db = get_session()
        try:
            rows = db.execute(
                select(
                    MarketBar.symbol,
                    MarketBar.exchange,
                    MarketBar.interval,
                    func.count(),
                    func.min(MarketBar.bar_time),
                    func.max(MarketBar.bar_time),
                ).group_by(MarketBar.symbol, MarketBar.exchange, MarketBar.interval)
            ).all()
        finally:
            db.close()
        out: list[BarOverview] = []
        for sym, ex, iv, count, start_s, end_s in rows:
            try:
                exchange = Exchange(str(ex).upper())
            except Exception:
                continue
            iv_key = "d" if iv in ("1d", "d") else ("1h" if iv in ("1h", "60m") else str(iv))
            try:
                interval = Interval(iv_key)
            except Exception:
                continue
            start_dt = parse_tick_dt(start_s)
            end_dt = parse_tick_dt(end_s)
            out.append(
                BarOverview(
                    symbol=str(sym),
                    exchange=exchange,
                    interval=interval,
                    count=int(count or 0),
                    start=convert_tz(start_dt.astimezone(DB_TZ)) if start_dt else None,
                    end=convert_tz(end_dt.astimezone(DB_TZ)) if end_dt else None,
                )
            )
        return out

    def get_tick_overview(self) -> list[TickOverview]:
        return []


def install_market_bars_database() -> None:
    """Point vnpy get_database() at MySQL market_bars for CTA backtester."""
    from vnpy.trader import database as db_mod

    db_mod.database = MarketBarsDatabase()
    try:
        from vnpy_ctastrategy.backtesting import load_bar_data, load_tick_data

        load_bar_data.cache_clear()
        load_tick_data.cache_clear()
    except Exception:
        logger.debug("load_bar_data cache clear skipped", exc_info=True)
    logger.info("vnpy database → MySQL market_bars (local SimNow replay)")
