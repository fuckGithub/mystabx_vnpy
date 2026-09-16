"""Demo double-MA CTA strategy using TargetPosTemplate (open-source vnpy)."""

from __future__ import annotations

from vnpy_ctastrategy import (
    ArrayManager,
    BarData,
    BarGenerator,
    OrderData,
    StopOrder,
    TargetPosTemplate,
    TickData,
    TradeData,
)


class DoubleMaStrategy(TargetPosTemplate):
    """Fast/slow SMA cross → set_target_pos (EliteTargetTemplate-style)."""

    author = "Stabx"

    fast_window: int = 10
    slow_window: int = 20
    fixed_size: int = 1
    gateway_name: str = ""

    fast_ma0: float = 0.0
    fast_ma1: float = 0.0
    slow_ma0: float = 0.0
    slow_ma1: float = 0.0

    parameters = ["fast_window", "slow_window", "fixed_size", "gateway_name"]
    variables = ["fast_ma0", "fast_ma1", "slow_ma0", "slow_ma1"]

    def on_init(self) -> None:
        self.write_log("策略初始化")
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        self.load_bar(10)

    def on_start(self) -> None:
        self.write_log("策略启动")
        self.put_event()

    def on_stop(self) -> None:
        self.write_log("策略停止")
        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        super().on_tick(tick)
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        super().on_bar(bar)
        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        fast_ma = am.sma(self.fast_window, array=True)
        slow_ma = am.sma(self.slow_window, array=True)
        self.fast_ma0 = float(fast_ma[-1])
        self.fast_ma1 = float(fast_ma[-2])
        self.slow_ma0 = float(slow_ma[-1])
        self.slow_ma1 = float(slow_ma[-2])

        cross_over = self.fast_ma0 > self.slow_ma0 and self.fast_ma1 < self.slow_ma1
        cross_below = self.fast_ma0 < self.slow_ma0 and self.fast_ma1 > self.slow_ma1

        if cross_over:
            self.set_target_pos(int(self.fixed_size))
        elif cross_below:
            self.set_target_pos(-int(self.fixed_size))

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        super().on_order(order)

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass
