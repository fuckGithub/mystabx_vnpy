"""Assemble MainEngine: CTP gateway plus optional BaseApp modules."""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from mystabx.config.apps import iter_optional_apps


def build_engines() -> tuple[MainEngine, EventEngine]:
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    for _key, app_cls in iter_optional_apps():
        main_engine.add_app(app_cls)
    return main_engine, event_engine
