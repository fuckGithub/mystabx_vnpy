"""Rumi-style demo using EliteCtaTemplate shim (docs/09 阶段 C)."""

from __future__ import annotations

from numpy import ndarray

from core import strategy_shim as _shim

_HistoryManager = _shim.HistoryManager
_cross_below = _shim.cross_below
_cross_over = _shim.cross_over
_sma = _shim.sma


class RumiStrategy(_shim.EliteCtaTemplate):
    """MA deviation (RUMI) + holding / stop exit — open-source shim port."""

    author = "Stabx"

    bar_window: int = 1
    bar_interval: str = "1m"
    bar_buffer: int = 100

    fast_window: int = 3
    slow_window: int = 50
    rumi_window: int = 30
    max_holding: int = 100
    stop_percent: float = 0.03
    risk_window: int = 10
    risk_capital: float = 1_000_000
    price_add: float = 5
    fixed_size: int = 1
    gateway_name: str = ""

    trading_size: int = 1
    rumi_0: float = 0.0
    rumi_1: float = 0.0

    parameters = [
        "bar_window",
        "bar_interval",
        "bar_buffer",
        "fast_window",
        "slow_window",
        "rumi_window",
        "max_holding",
        "stop_percent",
        "risk_window",
        "risk_capital",
        "price_add",
        "fixed_size",
        "gateway_name",
    ]
    variables = ["trading_size", "rumi_0", "rumi_1"]

    def on_history(self, hm: _HistoryManager) -> None:
        fast_array: ndarray = _sma(hm.close, self.fast_window)
        slow_array: ndarray = _sma(hm.close, self.slow_window)
        diff_array = fast_array - slow_array
        rumi_array: ndarray = _sma(diff_array, self.rumi_window)

        self.rumi_0 = float(rumi_array[-1]) if len(rumi_array) else 0.0
        self.rumi_1 = float(rumi_array[-2]) if len(rumi_array) > 1 else 0.0

        long_signal = _cross_over(rumi_array, 0)
        short_signal = _cross_below(rumi_array, 0)

        sized = self.calculate_volume(self.risk_capital, self.risk_window, 1000, 1)
        self.trading_size = sized if sized > 0 else int(self.fixed_size)

        last_target = self.get_target()
        new_target = last_target

        if long_signal:
            new_target = self.trading_size
        elif short_signal:
            new_target = -self.trading_size

        if self.bar_since_entry() >= self.max_holding:
            new_target = 0

        close_price = float(hm.close[-1])
        if last_target > 0:
            stop_price = self.long_average_price() * (1 - self.stop_percent)
            if stop_price > 0 and close_price <= stop_price:
                new_target = 0
        elif last_target < 0:
            stop_price = self.short_average_price() * (1 + self.stop_percent)
            if stop_price > 0 and close_price >= stop_price:
                new_target = 0

        self.set_target(new_target)
        self.execute_trading(self.price_add)
        self.put_event()
