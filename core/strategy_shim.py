"""Elite-style CTA helpers on open-source vnpy (docs/09 阶段 C).

Provides HistoryManager, sma/wma/cross helpers, and EliteCtaTemplate
(TargetPosTemplate + on_history). Not VeighNa Elite — local shim only.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any

import numpy as np
from vnpy.trader.object import BarData, TickData, TradeData
from vnpy_ctastrategy import ArrayManager, BarGenerator, TargetPosTemplate

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None  # type: ignore


def sma(array: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average (same length as input; leading NaN)."""
    data = np.asarray(array, dtype=float)
    out = np.full_like(data, np.nan, dtype=float)
    if window <= 0 or len(data) < window:
        return out
    cumsum = np.cumsum(data)
    out[window - 1 :] = (cumsum[window - 1 :] - np.concatenate(([0.0], cumsum[:-window]))) / window
    return out


def wma(array: np.ndarray, window: int) -> np.ndarray:
    """Weighted moving average (linear weights 1..window)."""
    data = np.asarray(array, dtype=float)
    out = np.full_like(data, np.nan, dtype=float)
    if window <= 0 or len(data) < window:
        return out
    weights = np.arange(1, window + 1, dtype=float)
    denom = weights.sum()
    for i in range(window - 1, len(data)):
        out[i] = float(np.dot(data[i - window + 1 : i + 1], weights) / denom)
    return out


def cross_over(array: np.ndarray, value: float = 0.0) -> bool:
    """True when array crosses above value on the latest bar."""
    data = np.asarray(array, dtype=float)
    if len(data) < 2:
        return False
    prev, last = data[-2], data[-1]
    if np.isnan(prev) or np.isnan(last):
        return False
    return bool(prev <= value < last)


def cross_below(array: np.ndarray, value: float = 0.0) -> bool:
    """True when array crosses below value on the latest bar."""
    data = np.asarray(array, dtype=float)
    if len(data) < 2:
        return False
    prev, last = data[-2], data[-1]
    if np.isnan(prev) or np.isnan(last):
        return False
    return bool(prev >= value > last)


class HistoryManager:
    """Fixed-length bar buffer with numpy OHLCV accessors."""

    def __init__(self, size: int = 100) -> None:
        self.size = max(1, int(size))
        self._bars: deque[BarData] = deque(maxlen=self.size)
        self._count = 0

    def update_bar(self, bar: BarData) -> None:
        self._bars.append(bar)
        self._count += 1

    def bar_count(self) -> int:
        return self._count

    @property
    def inited(self) -> bool:
        return len(self._bars) >= self.size

    def _col(self, attr: str) -> np.ndarray:
        return np.array([getattr(b, attr) for b in self._bars], dtype=float)

    @property
    def datetime(self) -> np.ndarray:
        return np.array([b.datetime for b in self._bars], dtype=object)

    @property
    def open(self) -> np.ndarray:
        return self._col("open_price")

    @property
    def high(self) -> np.ndarray:
        return self._col("high_price")

    @property
    def low(self) -> np.ndarray:
        return self._col("low_price")

    @property
    def close(self) -> np.ndarray:
        return self._col("close_price")

    @property
    def volume(self) -> np.ndarray:
        return self._col("volume")

    @property
    def turnover(self) -> np.ndarray:
        return self._col("turnover")

    @property
    def open_interest(self) -> np.ndarray:
        return self._col("open_interest")

    def to_dataframe(self):
        if pd is None:
            raise RuntimeError("pandas not installed")
        rows = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "turnover": self.turnover,
            "open_interest": self.open_interest,
        }
        index = [b.datetime for b in self._bars]
        return pd.DataFrame(rows, index=index)


class TheoreticalPosition:
    """Track theoretical entry bar / average prices for Elite-style helpers."""

    def __init__(self) -> None:
        self.target: int = 0
        self.pos: int = 0
        self.bar_index: int = 0
        self.entry_bar: int | None = None
        self.long_cost: float = 0.0
        self.long_volume: float = 0.0
        self.short_cost: float = 0.0
        self.short_volume: float = 0.0

    def on_bar(self) -> None:
        self.bar_index += 1

    def set_target(self, target: int) -> None:
        prev = self.target
        self.target = int(target)
        if prev == 0 and self.target != 0:
            self.entry_bar = self.bar_index
        if self.target == 0:
            self.entry_bar = None
            self.long_cost = self.long_volume = 0.0
            self.short_cost = self.short_volume = 0.0

    def on_trade(self, trade: TradeData) -> None:
        price = float(trade.price)
        volume = float(trade.volume)
        direction = str(getattr(getattr(trade, "direction", None), "name", trade.direction))
        if direction == "LONG":
            self.long_cost += price * volume
            self.long_volume += volume
            self.pos += int(volume)
        elif direction == "SHORT":
            self.short_cost += price * volume
            self.short_volume += volume
            self.pos -= int(volume)

    def bar_since_entry(self) -> int:
        if self.entry_bar is None:
            return 0
        return max(0, self.bar_index - self.entry_bar)

    def long_average_price(self) -> float:
        if self.long_volume <= 0:
            return 0.0
        return self.long_cost / self.long_volume

    def short_average_price(self) -> float:
        if self.short_volume <= 0:
            return 0.0
        return self.short_cost / self.short_volume

    def calculate_volume(
        self,
        close: np.ndarray,
        risk_capital: float,
        risk_window: int,
        max_volume: int = 0,
        min_volume: int = 0,
    ) -> int:
        """ATR-ish sizing: risk_capital / mean(abs close change) over risk_window."""
        data = np.asarray(close, dtype=float)
        if len(data) < risk_window + 1 or risk_window <= 0:
            return max(min_volume, 1)
        diffs = np.abs(np.diff(data[-(risk_window + 1) :]))
        risk = float(np.mean(diffs)) if len(diffs) else 0.0
        if risk <= 0:
            size = max(min_volume, 1)
        else:
            size = int(risk_capital / risk)
        if max_volume > 0:
            size = min(size, max_volume)
        if min_volume > 0:
            size = max(size, min_volume)
        return max(size, 0)


class EliteCtaTemplate(TargetPosTemplate):
    """TargetPosTemplate with HistoryManager + on_history callback."""

    bar_window: int = 1
    bar_interval: str = "1m"
    bar_buffer: int = 100

    parameters = ["bar_window", "bar_interval", "bar_buffer"]

    def __init__(self, cta_engine: Any, strategy_name: str, vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.hm = HistoryManager(self.bar_buffer)
        self.am = ArrayManager(self.bar_buffer)
        self._theo = TheoreticalPosition()
        self.bg: BarGenerator | None = None

    def on_init(self) -> None:
        self.write_log("策略初始化")
        interval = str(self.bar_interval or "1m")
        window = int(self.bar_window or 1)
        if interval == "1m" and window > 1:
            self.bg = BarGenerator(self.on_bar, window, self.on_window_bar)
        else:
            self.bg = BarGenerator(self.on_bar)
        self.load_bar(10)

    def on_tick(self, tick: TickData) -> None:
        super().on_tick(tick)
        if self.bg:
            self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        super().on_bar(bar)
        if self.bg and int(self.bar_window or 1) > 1 and str(self.bar_interval) == "1m":
            self.bg.update_bar(bar)
        else:
            self._push_history(bar)

    def on_window_bar(self, bar: BarData) -> None:
        self._push_history(bar)

    def _push_history(self, bar: BarData) -> None:
        self.hm.update_bar(bar)
        self.am.update_bar(bar)
        self._theo.on_bar()
        if self.hm.inited:
            self.on_history(self.hm)

    def on_history(self, hm: HistoryManager) -> None:
        """Override in subclass — called when HistoryManager is inited."""

    def on_trade(self, trade: TradeData) -> None:
        self._theo.on_trade(trade)
        self.put_event()

    # --- Elite-style aliases ---
    def set_target(self, target: int) -> None:
        self._theo.set_target(target)

    def get_target(self) -> int:
        return self._theo.target

    def execute_trading(self, price_add: float = 0) -> None:
        if price_add:
            self.tick_add = price_add
        self.set_target_pos(self._theo.target)

    def calculate_volume(
        self,
        risk_capital: float,
        risk_window: int,
        max_volume: int = 0,
        min_volume: int = 0,
    ) -> int:
        return self._theo.calculate_volume(
            self.hm.close, risk_capital, risk_window, max_volume, min_volume
        )

    def bar_since_entry(self) -> int:
        return self._theo.bar_since_entry()

    def long_average_price(self) -> float:
        return self._theo.long_average_price()

    def short_average_price(self) -> float:
        return self._theo.short_average_price()
