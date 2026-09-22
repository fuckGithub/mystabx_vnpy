"""system 插件入口（最小可运行集成员）。

路由由 ``app/core/discover.py`` 目录扫描挂载（``module_system/**/controller.py`` →
容器前缀 ``/system``）；``setup()`` 声明模型与种子数据，``start()`` 注入内核槽位实现并把
系统配置、数据字典预热到 Redis（内核 lifespan 不再直接调用本插件的 service）。
"""

from __future__ import annotations

from typing import cast

from redis.asyncio.client import Redis

from app.core.logger import log
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext, SeedRelation
from app.core.plugin.slots import (
    SLOT_AUTH_DATA_SCOPE_MODELS,
    SLOT_AUTH_USER_RESOLVER,
    SLOT_CONFIG_PARAMS_PROVIDER,
    SLOT_LOG_OPERATION_SINK,
    provide,
)
from app.plugin.module_system.dict.service import DictDataService
from app.plugin.module_system.log.service import OperationLogSinkImpl
from app.plugin.module_system.params.service import ParamsProviderImpl, ParamsService
from app.plugin.module_system.permission_provider import data_scope_models
from app.plugin.module_system.user.service import UserResolverImpl

MODEL_PATHS: tuple[str, ...] = (
    "auth.schema",
    "dept.model",
    "dict.model",
    "log.model",
    "menu.model",
    "notice.model",
    "params.model",
    "position.model",
    "role.model",
    "tenant.model",
    "user.model",
)
"""本插件声明的 ORM 模型模块（相对 ``app.plugin.module_system`` 的点分路径）。

本插件内部模型以字符串名互相引用（如 ``OperationLogModel`` → ``UserModel``），
SQLAlchemy 初始化 mapper 时需要**完整**的注册表，故使用方需一次性导入全部路径：
运行时由 ``setup()`` 声明并经 ``loader.import_plugin_models`` 导入；测试等同理。
"""

SEED_DIR: str = "seeds/data"
"""种子 JSON 目录（相对本插件目录，供 ``ctx.add_seed_file`` 解析）。"""


class Plugin(PluginBase):
    """系统插件：提供认证、权限、参数与操作日志等内核槽位实现。"""

    def __init__(self) -> None:
        """初始化插件状态（Redis 客户端由内核在 ``start()`` 前注入）。"""
        self._redis: Redis | None = None

    def setup(self, ctx: PluginContext) -> None:
        """声明模型与种子数据。

        声明顺序即写入顺序，被引用表必须排在引用表之前：字典类型先于字典数据，用户与
        角色先于用户角色关联。

        参数:
        - ctx (PluginContext): 注册接口。

        返回:
        - None
        """
        ctx.add_models(*MODEL_PATHS)

        ctx.add_seed_file("sys_tenant", f"{SEED_DIR}/sys_tenant.json", natural_key="code")
        # 菜单的自然键是 (route_path, name)：135 条按钮行（type=3）的 route_path 为
        # NULL，单用 route_path 会让 `route_path IS NULL` 命中已插入的第一条按钮行，
        # 首启即静默丢掉其余按钮（实测 177 行只落 43 行）。名字补齐 NULL 分支的区分度。
        ctx.add_seed_file(
            "sys_menu",
            f"{SEED_DIR}/sys_menu.json",
            natural_key=("route_path", "name"),
        )
        ctx.add_seed_file("sys_param", f"{SEED_DIR}/sys_param.json", natural_key="config_key")
        ctx.add_seed_file("sys_dept", f"{SEED_DIR}/sys_dept.json", natural_key="code")
        ctx.add_seed_file("sys_role", f"{SEED_DIR}/sys_role.json", natural_key="code")
        ctx.add_seed_file(
            "sys_dict_type", f"{SEED_DIR}/sys_dict_type.json", natural_key="dict_type"
        )
        ctx.add_seed_file(
            "sys_dict_data",
            f"{SEED_DIR}/sys_dict_data.json",
            natural_key=("dict_type", "dict_value"),
            relations=[
                SeedRelation(
                    field="dict_type_id",
                    ref_table="sys_dict_type",
                    ref_key="dict_type",
                    source_field="dict_type",
                )
            ],
        )
        # sys_position 暂无引导数据（空数组占位）：自然键取真实列 ``name``（该模型
        # **没有** ``code`` 列），保证将来补数据时仍能按行幂等。
        ctx.add_seed_file("sys_position", f"{SEED_DIR}/sys_position.json", natural_key="name")
        ctx.add_seed_file("sys_user", f"{SEED_DIR}/sys_user.json", natural_key="username")
        # 该表无业务列可作自然键：user_name/role_code 仅用于解析出 user_id/role_id
        # （列过滤会剥掉这两个来源键），幂等判定落在解析结果上。
        ctx.add_seed_file(
            "sys_user_roles",
            f"{SEED_DIR}/sys_user_roles.json",
            natural_key=("user_id", "role_id"),
            relations=[
                SeedRelation(
                    field="user_id",
                    ref_table="sys_user",
                    ref_key="username",
                    source_field="user_name",
                ),
                SeedRelation(
                    field="role_id",
                    ref_table="sys_role",
                    ref_key="code",
                    source_field="role_code",
                ),
            ],
        )

    def set_redis(self, redis: object | None) -> None:
        """保存内核注入的 Redis 客户端。

        参数:
        - redis (object | None): Redis 客户端；未启用 Redis 时内核传 ``None``。

        返回:
        - None
        """
        self._redis = cast("Redis | None", redis)

    async def start(self) -> None:
        """注入内核槽位实现，并预热系统配置与数据字典缓存。

        返回:
        - None
        """
        provide(SLOT_LOG_OPERATION_SINK, OperationLogSinkImpl())
        provide(SLOT_CONFIG_PARAMS_PROVIDER, ParamsProviderImpl())
        provide(SLOT_AUTH_USER_RESOLVER, UserResolverImpl())
        provide(SLOT_AUTH_DATA_SCOPE_MODELS, data_scope_models())

        if self._redis is None:
            log.warning(
                "⚠️ 未注入 Redis（REDIS_ENABLE=False？）：跳过系统配置与数据字典缓存预热，"
                "演示模式/IP 名单等中间件策略将按默认值（全部关闭/空）执行"
            )
            return
        await ParamsService().init_config_service(redis=self._redis)
        log.info("✅ Redis系统配置初始化完成")
        await DictDataService().init_dict_service(redis=self._redis)
        log.info("✅ Redis数据字典初始化完成")


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例；
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例），``setup()``/``start()``
# 都不会执行（槽位将全部缺失）。
PLUGIN = Plugin()
