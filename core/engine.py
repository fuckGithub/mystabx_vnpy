"""Headless vnpy MainEngine — no Qt UI imports (docs/01, docs/06 B2)."""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway


def build_headless_engines() -> tuple[MainEngine, EventEngine]:
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # Named instances are registered later by AccountGatewayManager.
    _ = CtpGateway
    return main_engine, event_engine
