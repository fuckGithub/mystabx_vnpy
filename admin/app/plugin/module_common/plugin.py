"""common 插件入口（最小可运行集成员）。"""

from __future__ import annotations

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext


class Plugin(PluginBase):
    """通用模块插件：文件与健康检查。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型（本插件无 ORM 模型）。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """
        ctx.add_models()


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例；
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例），``setup()`` 不会执行。
PLUGIN = Plugin()
