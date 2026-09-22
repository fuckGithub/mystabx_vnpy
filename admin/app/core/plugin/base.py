"""插件基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.plugin.context import PluginContext


class PluginBase(ABC):
    """插件基类。

    子类至少实现 ``setup()``；``start()`` / ``stop()`` 按需覆写。
    无 ``plugin.py`` 的存量插件不继承本类，由目录扫描回退挂载其 controller。
    """

    @abstractmethod
    def setup(self, ctx: PluginContext) -> None:
        """声明插件提供给系统的全部能力。

        参数:
        - ctx (PluginContext): 注册接口。

        返回:
        - None
        """

    async def start(self) -> None:   # noqa: B027 — 可选钩子：默认空实现，子类按需覆写
        """数据库/Redis 就绪后的初始化（本基类实现为空）。

        返回:
        - None
        """

    def set_redis(self, redis: object | None) -> None:   # noqa: B027 — 可选钩子：默认空实现，子类按需覆写
        """由内核在 ``start()`` 前注入 Redis 客户端（本基类实现为空）。

        需要缓存的插件（如 module_system 的字典/参数缓存）覆写本方法保存引用。

        参数:
        - redis (object | None): Redis 客户端。

        返回:
        - None
        """

    async def stop(self) -> None:   # noqa: B027 — 可选钩子：默认空实现，子类按需覆写
        """应用关闭时的清理（本基类实现为空）。

        返回:
        - None
        """
