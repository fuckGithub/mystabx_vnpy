"""Headless vnpy MainEngine — no Qt UI imports (docs/01, docs/06 B2). Powered by vn.py MainEngine."""

from __future__ import annotations

import logging

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

logger = logging.getLogger("stabx.engine")


def build_headless_engines() -> tuple[MainEngine, EventEngine]:
    """Create engines with CTP gateway + soft-loaded CTA / backtester apps."""
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # Named instances are registered later by AccountGatewayManager.
    _ = CtpGateway

    try:
        from vnpy_ctastrategy import CtaStrategyApp

        main_engine.add_app(CtaStrategyApp)
        logger.info("CtaStrategyApp loaded")
    except ImportError:
        logger.warning("vnpy_ctastrategy not installed — CTA engine disabled")

    try:
        from vnpy_ctabacktester import CtaBacktesterApp

        main_engine.add_app(CtaBacktesterApp)
        logger.info("CtaBacktesterApp loaded")
    except ImportError:
        logger.warning("vnpy_ctabacktester not installed — backtester disabled")

    return main_engine, event_engine
