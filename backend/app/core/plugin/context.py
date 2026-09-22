"""插件注册上下文：``setup(ctx)`` 期间收集注册项（不触达数据库）。"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict

from fastapi import APIRouter

SeedRow = dict[str, Any]
"""单条种子行。"""

EventHandler = Callable[[SeedRow], Awaitable[None] | None]
"""事件处理器：接收载荷字典，可同步可异步。"""

AsyncHook = Callable[[], Awaitable[None]]
"""启动/关闭钩子。"""

DEFAULT_CHILDREN_FIELD = "children"
"""嵌套子行字段名。"""

DEFAULT_PARENT_FIELD = "parent_id"
"""子行指向父行的外键字段名。"""


class JobSpec(TypedDict, total=False):
    """插件声明式定时任务。

    键集合与**实际读取**这些键的三处代码一一对应（15 个）：

    - ``SchedulerUtil._add_job_with_trigger`` 读 9 个（三种触发方式共用的落库字段）：
      ``args`` / ``coalesce`` / ``code`` / ``executor`` / ``func`` / ``job_id`` /
      ``job_name`` / ``jobstore`` / ``kwargs``；
    - 内核的三个触发器包装器读 5 个：``add_cron_job`` 读 ``trigger_args`` / ``cron`` /
      ``start_date`` / ``end_date``，``add_interval_job`` 再读 ``interval``，
      ``add_date_job`` 复用 ``trigger_args`` / ``cron`` 作执行时刻；
    - 插件侧 ``JobLogSinkImpl.register`` 读 1 个：``trigger``（显式触发器类型判别键，
      取值 ``"cron"`` / ``"interval"`` / ``"date"``；缺省时 ``register`` 按内核同样的读取
      优先级 —— ``trigger_args`` 先于 ``cron`` / ``interval`` —— 推断，见其 ``_infer_trigger``）。

    任务既可能来自数据库文本列（``NodeModel`` 的 ``Text``/``String`` 列），也可能由插件
    直接构造，因此「取值形态」同时接受两种写法，由内核统一归一化：

    - ``interval``：``int`` 表示秒数；``str`` 为触发器参数「秒 分 时 天 周」。
    - ``args``：``list`` 为位置参数序列；``str`` 为逗号分隔文本。
    - ``kwargs``：``dict`` 为关键字参数；``str`` 为 JSON 文本。

    遗留别名（仅为兼容既有调用方保留，新代码请用前者）：

    - ``func`` 是 ``code`` 的别名（内核按 ``code or func`` 取值）；``code`` 必须是**可执行
      代码块**，不要传节点编码。
    - ``trigger_args`` 是触发器参数的统一键，优先级高于 ``cron`` / ``interval``。
    """

    job_id: str | int
    job_name: str
    code: str
    func: str | None
    trigger: str | None
    trigger_args: str | None
    cron: str | None
    interval: str | int | None
    args: str | list[Any] | None
    kwargs: str | dict[str, Any] | None
    coalesce: bool | None
    jobstore: str | None
    executor: str | None
    start_date: str | None
    end_date: str | None


@dataclass(slots=True, frozen=True)
class RouterSpec:
    """插件声明的路由及其专属依赖（``dependencies=None`` 表示用运行时默认）。"""

    router: APIRouter
    """待挂载的路由实例。"""

    dependencies: list[Any] | None = None
    """该路由**专属**的 FastAPI 依赖；``None`` 表示沿用 ``mount()`` 的运行时默认依赖。"""


@dataclass(slots=True, frozen=True)
class SeedRelation:
    """种子行的外键解析规则。"""

    field: str
    """目标表待填字段，如 ``dict_type_id``。"""

    ref_table: str
    """引用表名，如 ``sys_dict_type``。"""

    ref_key: str
    """引用表用于匹配的字段（自然键），如 ``dict_type``。"""

    source_field: str
    """源行中承载引用键的字段，如 ``dict_type``。"""


@dataclass(slots=True)
class SeedSpec:
    """一份种子声明。"""

    table: str
    """目标表名（``__tablename__``）。"""

    rows: list[SeedRow]
    """待写入的行。"""

    natural_key: str | tuple[str, ...] | None = None
    """按行幂等的自然键；``None`` 时退化为"表空才写"。"""

    relations: list[SeedRelation] = field(default_factory=list)
    """外键解析规则（在查重前应用）。"""

    children_field: str = DEFAULT_CHILDREN_FIELD
    """嵌套子行字段名。"""

    parent_field: str = DEFAULT_PARENT_FIELD
    """子行外键字段名。"""


class PluginContext:
    """插件 ``setup()`` 可用的注册接口。

    只做收集，不做任何 IO 副作用（读种子文件除外），因此可在 ``create_app()``
    阶段安全调用（此时数据库尚未就绪）。
    """

    def __init__(self, plugin_name: str, base_dir: Path) -> None:
        """初始化上下文。

        参数:
        - plugin_name (str): 插件名，如 ``ai``。
        - base_dir (Path): 插件目录绝对路径，用于解析种子文件相对路径。
        """
        self.plugin_name = plugin_name
        self.base_dir = Path(base_dir)
        self.routers: list[RouterSpec] = []
        self.model_paths: list[str] = []
        self.seeds: list[SeedSpec] = []
        self.event_handlers: list[tuple[str, EventHandler]] = []
        self.startup_hooks: list[AsyncHook] = []
        self.shutdown_hooks: list[AsyncHook] = []
        self.scheduler_jobs: list[JobSpec] = []

    def add_router(self, router: APIRouter, dependencies: list[Any] | None = None) -> None:
        """注册目录扫描扫不到的路由（如 WebSocket、非 controller 文件中的路由）。

        参数:
        - router (APIRouter): 待挂载的路由实例。
        - dependencies (list[Any] | None): 该路由**专属**的 FastAPI 依赖，``None`` 表示沿用
          ``PluginRuntime.mount(dependencies=...)`` 的运行时默认依赖。仅当统一依赖不适用于
          该路由时才需要传 —— 例如 WebSocket 路由需要 ``WebSocketRateLimiter``，而运行时
          默认给的是 HTTP 用的 ``RateLimiter``（两者不可互换）。

        返回:
        - None
        """
        self.routers.append(RouterSpec(router=router, dependencies=dependencies))

    def add_models(self, *dotted_paths: str) -> None:
        """声明 ORM 模型模块（建表前统一导入，保证 metadata 完整）。

        参数:
        - *dotted_paths (str): 相对插件目录的点分路径，如 ``"model.model"``。

        返回:
        - None
        """
        self.model_paths.extend(dotted_paths)

    def add_seed(
        self,
        table: str,
        rows: list[SeedRow],
        *,
        natural_key: str | tuple[str, ...] | None = None,
        relations: list[SeedRelation] | None = None,
        children_field: str = DEFAULT_CHILDREN_FIELD,
        parent_field: str = DEFAULT_PARENT_FIELD,
    ) -> None:
        """声明内联种子行。

        参数:
        - table (str): 目标表名。
        - rows (list[SeedRow]): 待写入行。
        - natural_key (str | tuple[str, ...] | None): 按行幂等的自然键。
        - relations (list[SeedRelation] | None): 外键解析规则。
        - children_field (str): 嵌套子行字段名。
        - parent_field (str): 子行外键字段名。

        返回:
        - None
        """
        self.seeds.append(
            SeedSpec(
                table=table,
                rows=list(rows),
                natural_key=natural_key,
                relations=list(relations or []),
                children_field=children_field,
                parent_field=parent_field,
            )
        )

    def add_seed_file(
        self,
        table: str,
        relative_path: str,
        *,
        natural_key: str | tuple[str, ...] | None = None,
        relations: list[SeedRelation] | None = None,
        children_field: str = DEFAULT_CHILDREN_FIELD,
        parent_field: str = DEFAULT_PARENT_FIELD,
    ) -> None:
        """从插件目录下的 JSON 文件声明种子。

        参数:
        - table (str): 目标表名。
        - relative_path (str): 相对插件目录的路径，如 ``"seeds/sys_menu.json"``。
        - natural_key (str | tuple[str, ...] | None): 按行幂等的自然键。
        - relations (list[SeedRelation] | None): 外键解析规则。
        - children_field (str): 嵌套子行字段名。
        - parent_field (str): 子行外键字段名。

        返回:
        - None

        异常:
        - FileNotFoundError: 种子文件不存在。
        """
        path = self.base_dir / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"插件 {self.plugin_name} 的种子文件不存在: {path}")
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"种子文件必须是 JSON 数组: {path}")
        self.add_seed(
            table,
            rows,
            natural_key=natural_key,
            relations=relations,
            children_field=children_field,
            parent_field=parent_field,
        )

    def on(self, event: str, handler: EventHandler) -> None:
        """订阅事件。

        参数:
        - event (str): 事件名，如 ``"auth.login"``。
        - handler (EventHandler): 处理器。

        返回:
        - None
        """
        self.event_handlers.append((event, handler))

    def add_startup_hook(self, hook: AsyncHook) -> None:
        """注册启动钩子（DB 就绪后执行）。

        参数:
        - hook (AsyncHook): 无参协程。

        返回:
        - None
        """
        self.startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: AsyncHook) -> None:
        """注册关闭钩子（反序执行）。

        参数:
        - hook (AsyncHook): 无参协程。

        返回:
        - None
        """
        self.shutdown_hooks.append(hook)

    def add_scheduler_job(self, spec: JobSpec) -> None:
        """声明定时任务（由槽位 ``scheduler.job_sink`` 落地）。

        参数:
        - spec (JobSpec): 任务定义。

        返回:
        - None
        """
        self.scheduler_jobs.append(spec)
