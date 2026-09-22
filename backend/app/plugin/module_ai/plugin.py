"""ai 插件入口（可选插件，可整目录移除）。

HTTP 路由由 ``app/core/discover.py`` 目录扫描挂载（``module_ai/**/controller.py`` →
容器前缀 ``/ai``，走运行时统一限流）；本文件的 ``setup()`` 补三样目录扫描扫不到的东西：

- ``ctx.add_models(...)``：本插件的 ORM 模型（``ai_provider`` / ``ai_model``）；
- ``ctx.add_seed_file(...)``：供应商/模型引导数据（``seeds/data/*.json``）；
- ``ctx.add_router(WS_AI, ...)``：``chat/ws.py`` 的 WebSocket 路由。该文件不是
  ``controller.py``，扫描不到；且它需要 ``WsRateLimiter``（WebSocket 版）而非运行时的
  HTTP ``RateLimiter``，故在此声明**专属**依赖（逐路由依赖见 ``PluginContext.add_router``）。
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from starlette.websockets import WebSocket

from app.core.http_limit import WsRateLimiter, build_limiter, ws_limit_callback
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext, SeedRelation
from app.plugin.module_ai.chat.ws import WS_AI

MODEL_PATHS: tuple[str, ...] = ("model.model",)
"""本插件声明的 ORM 模型模块（相对 ``app.plugin.module_ai`` 的点分路径）。

``model.model`` 内两个模型互相以字符串名引用（``AiProviderModel`` → ``AiModelModel``），
SQLAlchemy 初始化 mapper 时需要完整注册表，故一次性声明整个模块。
"""

SEED_DIR: str = "seeds/data"
"""种子 JSON 目录（相对本插件目录，供 ``ctx.add_seed_file`` 解析）。"""

# WebSocket 限流策略：1 次 / 5 秒（比全站 HTTP 更严格）
_WS_MAX_REQUESTS = 1
_WS_WINDOW_SECONDS = 5

_ws_limiter: WsRateLimiter | None = None
"""惰性初始化的 WebSocket 限流器，lifespan start 后可用。"""

_redis_ref: Any | None = None
"""set_redis 注入的 Redis 客户端引用，供 start() 构建限流器使用。"""


async def _ws_rate_limit(ws: WebSocket) -> Any:
    """可切换的 WebSocket 限流依赖：lifespan start 后指向真实限流器。"""
    if _ws_limiter is not None:
        await _ws_limiter(ws)


class Plugin(PluginBase):
    """AI 插件：供应商/模型管理与聊天会话（含 WebSocket）。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明模型、种子与 WebSocket 路由（必须在 setup 期完成）。

        ``PluginRuntime.mount()``（阶段 3）只读取 ``setup()`` 期间收集的注册项，``start()``
        （阶段 4）在其之后执行；把 ``add_router`` 放进 ``start()`` 路由就永远挂不上
        （只建应用、不进 lifespan 的场景更是如此）。

        参数:
        - ctx (PluginContext): 注册接口。

        返回:
        - None
        """
        ctx.add_models(*MODEL_PATHS)
        # 声明顺序即写入顺序：provider 必须先于 model，后者的 provider_id 才有得解析。
        ctx.add_seed_file("ai_provider", f"{SEED_DIR}/ai_provider.json", natural_key="name")
        # 自然键取解析后的真实列 provider_id（+model_key）：来源键 provider_name 会被列
        # 过滤剥掉，不能作为幂等依据；同一供应商下不允许重名模型，该组合已足够唯一。
        ctx.add_seed_file(
            "ai_model",
            f"{SEED_DIR}/ai_model.json",
            natural_key=("provider_id", "model_key"),
            relations=[
                SeedRelation(
                    field="provider_id",
                    ref_table="ai_provider",
                    ref_key="name",
                    source_field="provider_name",
                )
            ],
        )
        # 使用函数依赖 + 惰性 limiter：setup 阶段 Redis 尚未就绪，
        # 真实的 WsRateLimiter 在 start() 中构建。
        ctx.add_router(WS_AI, dependencies=[Depends(_ws_rate_limit)])

    def set_redis(self, redis: Any | None) -> None:
        """保存 Redis 客户端引用（内核在 start() 前注入）。"""
        global _redis_ref
        _redis_ref = redis

    async def start(self) -> None:
        """lifespan 阶段：构建 WebSocket 限流器（Redis 已就绪）。"""
        global _ws_limiter
        backend = await build_limiter(
            _redis_ref,
            max_requests=_WS_MAX_REQUESTS,
            window_seconds=_WS_WINDOW_SECONDS,
        )
        _ws_limiter = WsRateLimiter(
            backend=backend,
            callback=ws_limit_callback,
        )


# 插件运行时按 ``runtime.ENTRY_VAR == "PLUGIN"`` 取模块级实例；
# 缺少该绑定时入口会被判为不可用（ERROR + 降级为无实例）：``setup()`` 不会执行，
# 模型与 WebSocket 路由都会静默丢失。
PLUGIN = Plugin()
