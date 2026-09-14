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
    for _key, app_cls, post_init in iter_optional_apps():
        engine = main_engine.add_app(app_cls)
        for method_name in post_init:
            method = getattr(engine, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as exc:  # noqa: BLE001
                    print(f"[mystabx] app post_init {_key}.{method_name} failed: {exc}")
    return main_engine, event_engine
