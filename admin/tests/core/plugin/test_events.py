"""事件总线测试。"""

from __future__ import annotations

import asyncio

from app.core.plugin.events import EventBus


def test_publish_calls_sync_and_async_handlers() -> None:
    """同步与异步处理器都能被调用。"""

    async def _run() -> list[str]:
        bus = EventBus()
        seen: list[str] = []

        def sync_handler(payload: dict) -> None:
            seen.append(f"sync:{payload['id']}")

        async def async_handler(payload: dict) -> None:
            seen.append(f"async:{payload['id']}")

        bus.subscribe("auth.login", sync_handler)
        bus.subscribe("auth.login", async_handler)
        await bus.publish("auth.login", {"id": 7})
        return seen

    assert asyncio.run(_run()) == ["sync:7", "async:7"]


def test_handler_exception_does_not_break_others() -> None:
    """单个处理器异常只记日志，不中断其它处理器。"""

    async def _run() -> list[str]:
        bus = EventBus()
        seen: list[str] = []

        async def boom(payload: dict) -> None:
            raise RuntimeError("boom")

        def ok(payload: dict) -> None:
            seen.append("ok")

        bus.subscribe("auth.login", boom)
        bus.subscribe("auth.login", ok)
        await bus.publish("auth.login", {})
        return seen

    assert asyncio.run(_run()) == ["ok"]


def test_publish_unknown_event_is_noop() -> None:
    """无人订阅的事件静默返回。"""

    async def _run() -> None:
        bus = EventBus()
        await bus.publish("nobody.cares", {})

    assert asyncio.run(_run()) is None


def test_clear_removes_handlers() -> None:
    """clear 后不再触发。"""
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("e", lambda payload: seen.append("x"))  # type: ignore[arg-type]
    bus.clear()
    asyncio.run(bus.publish("e", {}))
    assert seen == []
