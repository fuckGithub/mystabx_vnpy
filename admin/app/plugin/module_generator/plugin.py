"""generator 插件入口。

路由由 ``app/core/discover.py`` 目录扫描挂载（``module_generator/**/controller.py`` →
容器前缀 ``/generator``）；本文件的 ``setup()`` 声明 ORM 模型。
"""

from __future__ import annotations

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext

MODEL_PATHS: tuple[str, ...] = ("gencode.model",)
"""本插件声明的 ORM 模型模块（相对 ``app.plugin.module_generator`` 的点分路径）。"""


class Plugin(PluginBase):
    """代码生成插件：基于数据表与模板生成前后端代码。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型。

        参数:
        - ctx (PluginContext): 注册接口。

        返回:
        - None
        """
        ctx.add_models(*MODEL_PATHS)


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例；
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例），``setup()`` 不会执行。
PLUGIN = Plugin()
