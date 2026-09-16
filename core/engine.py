"""Headless vnpy MainEngine — no Qt UI imports (docs/01, docs/06 B2). Powered by vn.py MainEngine."""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway


def build_headless_engines() -> tuple[MainEngine, EventEngine]:
    """Create engines with CTP gateway class registered for later use.

    Strategy apps (CTA / backtester / …) are not loaded into the Web headless
    process until product direction is decided; Qt desktop may still load them
    via mystabx.config.apps.
    """
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # Named instances are registered later by AccountGatewayManager.
    _ = CtpGateway
    return main_engine, event_engine
