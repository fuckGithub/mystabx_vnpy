"""application 插件入口。"""

from __future__ import annotations

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext


class Plugin(PluginBase):
    """应用管理插件：门户应用与插件清单。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型路径（门户应用表 ``app_portal``）。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """
        ctx.add_models("portal.model")


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例；
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例），``setup()`` 不会执行。
PLUGIN = Plugin()
