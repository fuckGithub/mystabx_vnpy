"""task 插件入口：定时任务与工作流。"""

from __future__ import annotations

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, provide

from .job_log_sink import JobLogSinkImpl


class Plugin(PluginBase):
    """定时任务插件。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型路径。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """
        ctx.add_models(
            "cronjob.job.model",
            "cronjob.node.model",
        )

    async def start(self) -> None:
        """注入调度器日志槽位。

        返回:
        - None
        """
        provide(SLOT_SCHEDULER_JOB_LOG_SINK, JobLogSinkImpl())


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例。
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例）：``setup()``/``start()`` 都不会执行，
# 本插件声明的模型与调度器日志槽位将静默丢失。
PLUGIN = Plugin()
