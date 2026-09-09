"""Historical K-line provider. source=mock now; RQData plugs in at fetch_rqdata_bars."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import Literal

from core.serialize import SHANGHAI, dt_iso

HistorySource = Literal["mock", "rqdata"]
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


def configured_source() -> HistorySource:
    raw = os.environ.get("STABX_HISTORY_SOURCE", "mock").strip().lower()
    return "rqdata" if raw == "rqdata" else "mock"


def fetch_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    source: HistorySource | None = None,
    last_price: float | None = None,
) -> dict:
    """Fetch-boundary for historical bars. Flip source to rqdata after wiring the API."""
    resolved: HistorySource = source or configured_source()
    if resolved == "rqdata":
        return fetch_rqdata_bars(symbol, exchange, interval, last_price=last_price)
    return fetch_mock_bars(symbol, exchange, interval, last_price=last_price)


def fetch_rqdata_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    last_price: float | None = None,
) -> dict:
    """TODO: 对接 RQData（rqdatac.get_price / futures.get_dominant）后在此撮合 K 线。

    预期映射：vnpy symbol+exchange → RQData order_book_id（如 rb2510.SHFE → RBxxxx.XSGE），
    frequency 对应 1m/5m/15m/30m/60m/1d/1w/1M，返回字段对齐 mock bars。
    """
    _ = (symbol, exchange, interval, last_price)
    raise NotImplementedError("RQData 尚未对接，请保持 source=mock")


def fetch_mock_bars(
    symbol: str,
    exchange: str,
    interval: BarInterval,
    *,
    last_price: float | None = None,
) -> dict:
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

    # Walk ends at `anchor` so mock close matches the live last when possible.
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
    }
