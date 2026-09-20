"""Historical K-line provider — local MySQL first; mock/RQData only as explicit fallback."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import Literal

from core.serialize import SHANGHAI, dt_iso

HistorySource = Literal["local", "mock", "rqdata"]
BarInterval = Literal["1m", "5m", "15m", "30m", "60m", "1d", "1w", "1M"]

INTERVALS: tuple[BarInterval, ...] = ("1m", "5m", "15m", "30m", "60m", "1d", "1w", "1M")

_COUNTS: dict[BarInterval, int] = {
    "1m": 240,
    "5m": 200,
    "15m": 200,
    "30m": 200,
    "60m": 200,
    "1d": 250,
    "1w": 160,
    "1M": 72,
}

_STEP: dict[BarInterval, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "60m": timedelta(minutes=60),
    "1d": timedelta(days=1),
    "1w": timedelta(days=7),
    "1M": timedelta(days=30),
}

_LIMITS: dict[BarInterval, int] = {
    "1m": 1200,
    "5m": 800,
    "15m": 600,
    "30m": 500,
    "60m": 500,
    "1d": 400,
    "1w": 200,
    "1M": 120,
}


def configured_source() -> HistorySource:
    raw = os.environ.get("STABX_HISTORY_SOURCE", "local").strip().lower()
    if raw == "rqdata":
        return "rqdata"
    if raw == "mock":
        return "mock"
    return "local"


def fetch_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    source: HistorySource | None = None,
    last_price: float | None = None,
) -> dict:
    """Fetch-boundary for historical bars. Default = local MySQL market_bars."""
    resolved: HistorySource = source or configured_source()
    if resolved == "rqdata":
        return fetch_rqdata_bars(symbol, exchange, interval, last_price=last_price)
    if resolved == "mock":
        return fetch_mock_bars(symbol, exchange, interval, last_price=last_price)
    return fetch_local_bars(symbol, exchange, interval)


def fetch_local_bars(symbol: str, exchange: str, interval: BarInterval) -> dict:
    from features.market.bar_aggregator import resample_minutes
    from features.market.bar_store import query_bars

    limit = _LIMITS.get(interval, 500)
    if interval in {"1m", "5m", "15m", "30m", "60m", "1d"}:
        stored_iv = interval if interval in {"1m", "5m", "15m", "30m", "60m", "1d"} else "1m"
        bars = query_bars(symbol, exchange, stored_iv, limit=limit)
        # If higher intraday missing, rebuild from 1m on the fly (not persisted).
        if not bars and interval.endswith("m") and interval != "1m":
            minutes = int(interval[:-1])
            raw = query_bars(symbol, exchange, "1m", limit=min(5000, minutes * limit))
            rebuilt = resample_minutes(raw, minutes=minutes, interval=interval)
            bars = [
                {
                    "datetime": b.get("bar_time") or b.get("datetime"),
                    "open": b.get("open"),
                    "high": b.get("high"),
                    "low": b.get("low"),
                    "close": b.get("close"),
                    "volume": b.get("volume"),
                    "open_interest": b.get("open_interest"),
                }
                for b in rebuilt[-limit:]
            ]
        else:
            bars = [
                {
                    "datetime": b.get("datetime"),
                    "open": b.get("open"),
                    "high": b.get("high"),
                    "low": b.get("low"),
                    "close": b.get("close"),
                    "volume": b.get("volume"),
                    "open_interest": b.get("open_interest"),
                }
                for b in bars
            ]
    elif interval == "1w":
        daily = query_bars(symbol, exchange, "1d", limit=limit * 7)
        bars = _roll_daily(daily, days=7, limit=limit)
    elif interval == "1M":
        daily = query_bars(symbol, exchange, "1d", limit=limit * 31)
        bars = _roll_daily(daily, days=30, limit=limit)
    else:
        bars = []

    return {
        "source": "local",
        "symbol": symbol,
        "exchange": exchange,
        "interval": interval,
        "bars": bars,
        "empty": not bars,
        "hint": (
            ""
            if bars
            else "本地尚无 K 线。请先订阅合约并等待 Tick 归集（收盘后或约 1 分钟刷新），"
            "也可调用 POST /api/market/bars/aggregate。"
        ),
    }


def _roll_daily(daily: list[dict], *, days: int, limit: int) -> list[dict]:
    if not daily:
        return []
    out: list[dict] = []
    bucket: list[dict] = []
    for bar in daily:
        bucket.append(bar)
        if len(bucket) >= days:
            out.append(_merge_bucket(bucket))
            bucket = []
    if bucket:
        out.append(_merge_bucket(bucket))
    return out[-limit:]


def _merge_bucket(bucket: list[dict]) -> dict:
    return {
        "datetime": bucket[-1].get("datetime"),
        "open": bucket[0].get("open"),
        "high": max(float(b.get("high") or 0) for b in bucket),
        "low": min(float(b.get("low") or 0) for b in bucket if float(b.get("low") or 0) > 0),
        "close": bucket[-1].get("close"),
        "volume": sum(float(b.get("volume") or 0) for b in bucket),
        "open_interest": bucket[-1].get("open_interest") or 0,
    }


def fetch_rqdata_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    last_price: float | None = None,
) -> dict:
    """Reserved RQData plug-in — not used on the default path."""
    _ = (symbol, exchange, interval, last_price)
    raise NotImplementedError("RQData 尚未对接；请使用 source=local（默认）从 MySQL 回放")


def fetch_mock_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    last_price: float | None = None,
) -> dict:
    """Explicit fallback only (source=mock). Not used for production charts."""
    count = _COUNTS[interval]
    step = _STEP[interval]
    now = datetime.now(tz=SHANGHAI)
    if interval in {"1d", "1w", "1M"}:
        cursor = now.replace(hour=15, minute=0, second=0, microsecond=0)
    else:
        cursor = now.replace(second=0, microsecond=0)

    seed = hashlib.sha256(f"{exchange}.{symbol}.{interval}".encode()).digest()
    state = int.from_bytes(seed[:8], "big") or 1
    anchor = float(last_price) if last_price and last_price > 0 else 3000 + (state % 5000)
    price = anchor * 0.92

    def rng() -> float:
        nonlocal state
        state = (state * 6364136223846793005 + 1) & ((1 << 64) - 1)
        return (state >> 11) / float(1 << 53)

    bars: list[dict] = []
    series: list[tuple[datetime, float, float, float, float, float]] = []
    for _ in range(count):
        ret = (rng() - 0.48) * (0.004 if interval.endswith("m") else 0.018)
        open_ = price
        close = max(0.5, open_ * (1 + ret))
        high = max(open_, close) * (1 + rng() * 0.004)
        low = min(open_, close) * (1 - rng() * 0.004)
        volume = 800 + rng() * (18_000 if interval.endswith("m") else 80_000)
        series.append((cursor, open_, high, low, close, volume))
        price = close
        cursor -= step

    if last_price and last_price > 0 and series:
        shift = last_price / series[0][4]
        series = [
            (ts, o * shift, h * shift, lo * shift, c * shift, vol) for ts, o, h, lo, c, vol in series
        ]

    for ts, o, h, lo, c, vol in reversed(series):
        bars.append(
            {
                "datetime": dt_iso(ts),
                "open": round(o, 4),
                "high": round(h, 4),
                "low": round(lo, 4),
                "close": round(c, 4),
                "volume": round(vol, 0),
                "open_interest": 0,
            }
        )

    return {
        "source": "mock",
        "symbol": symbol,
        "exchange": exchange,
        "interval": interval,
        "bars": bars,
        "empty": False,
        "hint": "模拟数据（source=mock），非正式行情",
    }
