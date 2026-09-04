"""Project MainWindow wrapper. Official docks stay; only title and layout hooks."""

from __future__ import annotations

from functools import partial
from importlib import import_module

import vnpy
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow
from vnpy.trader.ui import mainwindow as vnpy_mainwindow
from vnpy.trader.ui.qt import QtCore, QtGui, QtWidgets
from vnpy.trader.ui.widget import (
    AboutDialog,
    AccountMonitor,
    ActiveOrderMonitor,
    ContractManager,
    LogMonitor,
    OrderMonitor,
    PositionMonitor,
    TickMonitor,
    TradeMonitor,
    TradingWidget,
)
from vnpy.trader.utility import TRADER_DIR, get_icon_path


class StabxMainWindow(MainWindow):
    """Own workspace shell around vnpy monitors. No web order channel."""

    def init_ui(self) -> None:
        self.window_title = f"Stabx Trader - {vnpy.__version__} [{TRADER_DIR}]"
        super().init_ui()

    def init_dock(self) -> None:
        """Official widgets; default areas: trade left, ticks right, books bottom."""
        self.trading_widget, trading_dock = self.create_dock(
            TradingWidget, "交易", QtCore.Qt.DockWidgetArea.LeftDockWidgetArea
        )
        tick_widget, tick_dock = self.create_dock(
            TickMonitor, "行情", QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        _order_widget, order_dock = self.create_dock(
            OrderMonitor, "委托", QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        _active_widget, active_dock = self.create_dock(
            ActiveOrderMonitor, "活动", QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        _trade_widget, trade_dock = self.create_dock(
            TradeMonitor, "成交", QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        )
        _log_widget, log_dock = self.create_dock(
            LogMonitor, "日志", QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        _account_widget, account_dock = self.create_dock(
            AccountMonitor, "资金", QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )
        position_widget, position_dock = self.create_dock(
            PositionMonitor, "持仓", QtCore.Qt.DockWidgetArea.BottomDockWidgetArea
        )

        self.tabifyDockWidget(tick_dock, order_dock)
        self.tabifyDockWidget(order_dock, active_dock)
        self.tabifyDockWidget(active_dock, trade_dock)
        self.tabifyDockWidget(account_dock, position_dock)
        tick_dock.raise_()
        account_dock.raise_()

        self.save_window_setting("default")

        tick_widget.itemDoubleClicked.connect(self.trading_widget.update_with_cell)
        position_widget.itemDoubleClicked.connect(self.trading_widget.update_with_cell)
        _ = (trading_dock, log_dock)

    def init_menu(self) -> None:
        """Official menus; skip optional apps whose UI module is missing."""
        bar: QtWidgets.QMenuBar = self.menuBar()
        bar.setNativeMenuBar(False)

        sys_menu: QtWidgets.QMenu = bar.addMenu("系统")
        for name in self.main_engine.get_all_gateway_names():
            self.add_action(
                sys_menu,
                f"连接{name}",
                get_icon_path(vnpy_mainwindow.__file__, "connect.ico"),
                partial(self.connect_gateway, name),
            )
        sys_menu.addSeparator()
        self.add_action(
            sys_menu,
            "退出",
            get_icon_path(vnpy_mainwindow.__file__, "exit.ico"),
            self.close,
        )

        app_menu: QtWidgets.QMenu = bar.addMenu("功能")
        for app in self.main_engine.get_all_apps():
            try:
                ui_module = import_module(app.app_module + ".ui")
                widget_class = getattr(ui_module, app.widget_name)
            except (ModuleNotFoundError, ImportError, AttributeError) as exc:
                print(f"[mystabx] skip optional app UI {app.app_name}: {exc}")
                continue
            self.add_action(
                app_menu,
                app.display_name,
                app.icon_name,
                partial(self.open_widget, widget_class, app.app_name),
                True,
            )

        action: QtGui.QAction = QtGui.QAction("配置", self)
        action.triggered.connect(self.edit_global_setting)
        bar.addAction(action)

        help_menu: QtWidgets.QMenu = bar.addMenu("帮助")
        self.add_action(
            help_menu,
            "查询合约",
            get_icon_path(vnpy_mainwindow.__file__, "contract.ico"),
            partial(self.open_widget, ContractManager, "contract"),
            True,
        )
        self.add_action(
            help_menu,
            "还原窗口",
            get_icon_path(vnpy_mainwindow.__file__, "restore.ico"),
            self.restore_window_setting,
        )
        self.add_action(
            help_menu,
            "测试邮件",
            get_icon_path(vnpy_mainwindow.__file__, "email.ico"),
            self.send_test_email,
        )
        self.add_action(
            help_menu,
            "关于",
            get_icon_path(vnpy_mainwindow.__file__, "about.ico"),
            partial(self.open_widget, AboutDialog, "about"),
        )


def build_main_window(main_engine: MainEngine, event_engine: EventEngine) -> StabxMainWindow:
    return StabxMainWindow(main_engine, event_engine)
