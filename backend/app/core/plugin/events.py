"""轻量事件总线：替代插件之间的直接 import。"""

from __future__ import annotations

from typing import Any

from app.core.logger import log
from app.core.plugin.context import EventHandler


class EventBus:
    """按事件名分发的极简事件总线。

    处理器异常只记日志，绝不影响发布方与其它订阅者。
    """

    def __init__(self) -> None:
        """初始化空订阅表。"""
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event: str, handler: EventHandler) -> None:
        """订阅事件。

        参数:
        - event (str): 事件名。
        - handler (EventHandler): 处理器。

        返回:
        - None
        """
        self._handlers.setdefault(event, []).append(handler)

    async def publish(self, event: str, payload: dict[str, Any]) -> None:
        """发布事件，依次调用全部订阅者。

        参数:
        - event (str): 事件名。
        - payload (dict[str, Any]): 载荷。

        返回:
        - None
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            log.debug(f"事件 {event} 无订阅者，跳过")
            return
        for handler in handlers:
            try:
                result = handler(payload)
                if hasattr(result, "__await__"):
                    await result  # type: ignore[misc]
            except Exception as exc:  # 单个订阅者失败不影响其它订阅者
                log.exception(f"❌ 事件 {event} 的处理器 {handler!r} 执行失败: {exc!s}")

    def clear(self) -> None:
        """清空全部订阅（测试隔离用）。

        返回:
        - None
        """
        self._handlers.clear()


event_bus = EventBus()
"""应用级事件总线单例。"""
