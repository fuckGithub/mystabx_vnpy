"""storage 插件入口。"""

from __future__ import annotations

from sqlalchemy import select

from app.config.setting import settings
from app.core.database import async_db_session
from app.core.logger import log
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.plugin.module_storage.node.model import StorageNodeModel
from app.utils.oss_util import OssUtil

MODEL_PATHS: tuple[str, ...] = (
    "node.model",
    "transfer.model",
    "workflow.model",
)

OSS_NODE_NAME = "Aliyun OSS"


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

    async def start(self) -> None:
        """OSS 就绪时幂等写入默认存储节点（不含密钥，use_settings=true）。"""
        if not settings.OSS_READY:
            log.info("OSS 未启用，跳过默认存储节点种子")
            return
        try:
            async with async_db_session() as session:
                async with session.begin():
                    result = await session.execute(
                        select(StorageNodeModel).where(
                            StorageNodeModel.name == OSS_NODE_NAME,
                            StorageNodeModel.is_deleted.is_(False),
                        )
                    )
                    existing = result.scalar_one_or_none()
                    config_json = OssUtil.settings_node_config_json()
                    if existing:
                        existing.type = "oss"
                        existing.config = config_json
                        existing.description = existing.description or "全局环境变量配置的阿里云 OSS"
                        log.info("已更新默认 OSS 存储节点配置")
                        return
                    session.add(
                        StorageNodeModel(
                            name=OSS_NODE_NAME,
                            type="oss",
                            config=config_json,
                            description="全局环境变量配置的阿里云 OSS",
                            status="0",
                        )
                    )
                    log.info("已创建默认 OSS 存储节点")
        except Exception as e:
            log.warning(f"种子 OSS 存储节点失败（可忽略）: {e}")


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例。
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例）：``setup()``/``start()`` 都不会执行，
# 本插件声明的模型将静默丢失。
PLUGIN = Plugin()
