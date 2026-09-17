"""双均线测试策略 — 用于跑通 Web CTA 添加 / 初始化 / 启停流程。

作者：Stabx（流程验证用，非生产策略）
"""

from __future__ import annotations

from vnpy_ctastrategy import (
    ArrayManager,
    BarData,
    BarGenerator,
    CtaTemplate,
    OrderData,
    StopOrder,
    TickData,
    TradeData,
)


class DualMaTest(CtaTemplate):
    """快慢均线交叉测试：金叉做多、死叉做空（固定手数）。"""

    author = "Stabx"

    fast_window: int = 10
    slow_window: int = 20
    fixed_size: int = 1

    fast_ma0: float = 0.0
    slow_ma0: float = 0.0

    parameters = ["fast_window", "slow_window", "fixed_size"]
    variables = ["fast_ma0", "slow_ma0"]

    def on_init(self) -> None:
        self.write_log("双均线测试策略初始化")
        self.bg = BarGenerator(self.on_bar)
        self.am = ArrayManager()
        self.load_bar(10)

    def on_start(self) -> None:
        self.write_log("双均线测试策略启动")
        self.put_event()

    def on_stop(self) -> None:
        self.write_log("双均线测试策略停止")
        self.put_event()

    def on_tick(self, tick: TickData) -> None:
        self.bg.update_tick(tick)

    def on_bar(self, bar: BarData) -> None:
        self.cancel_all()

        am = self.am
        am.update_bar(bar)
        if not am.inited:
            return

        fast_ma = am.sma(self.fast_window, array=True)
        slow_ma = am.sma(self.slow_window, array=True)
        self.fast_ma0 = float(fast_ma[-1])
        self.slow_ma0 = float(slow_ma[-1])
        fast_ma1 = float(fast_ma[-2])
        slow_ma1 = float(slow_ma[-2])

        cross_over = self.fast_ma0 > self.slow_ma0 and fast_ma1 <= slow_ma1
        cross_below = self.fast_ma0 < self.slow_ma0 and fast_ma1 >= slow_ma1

        if cross_over:
            if self.pos < 0:
                self.cover(bar.close_price, abs(self.pos))
            self.buy(bar.close_price, int(self.fixed_size))
        elif cross_below:
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))
            self.short(bar.close_price, int(self.fixed_size))

        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_stop_order(self, stop_order: StopOrder) -> None:
        pass
