"""Process-wide engine / gateway / loop holders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine, OmsEngine

from core.gateways import AccountGatewayManager


@dataclass
class Runtime:
    main_engine: MainEngine | None = None
    event_engine: EventEngine | None = None
    gateways: AccountGatewayManager | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def me(self) -> MainEngine:
        if self.main_engine is None:
            raise RuntimeError("engine not started")
        return self.main_engine

    @property
    def gw(self) -> AccountGatewayManager:
        if self.gateways is None:
            raise RuntimeError("gateway manager not started")
        return self.gateways

    @property
    def oms(self) -> OmsEngine:
        """OMS lives on a child engine; MainEngine only copies methods at runtime."""
        engine = self.me.get_engine("oms")
        if not isinstance(engine, OmsEngine):
            raise RuntimeError("oms engine not started")
        return engine


runtime = Runtime()
