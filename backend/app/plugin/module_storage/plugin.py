"""storage 插件入口。"""

from __future__ import annotations

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext

MODEL_PATHS: tuple[str, ...] = (
    "node.model",
    "transfer.model",
    "workflow.model",
)


class Plugin(PluginBase):
    """存储管理插件：存储节点、传输任务、存储工作流。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型路径。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """
        ctx.add_models(*MODEL_PATHS)


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例。
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例）：``setup()``/``start()`` 都不会执行，
# 本插件声明的模型将静默丢失。
PLUGIN = Plugin()
