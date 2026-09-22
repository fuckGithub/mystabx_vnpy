"""内核槽位契约：内核定义接口，插件提供实现。

全部契约为结构化 Protocol —— 实现方无需继承，只要形状匹配即可。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    # 仅为静态检查引入：本模块的注解在运行期是字符串（``from __future__ import annotations``），
    # 运行期不需要 ``JobSpec``，故不做模块级导入以规避包初始化顺序风险。
    from app.core.plugin.context import JobSpec


@dataclass(slots=True)
class OperationLogEntry:
    """一条待落库的操作/登录日志。"""

    type: int
    request_path: str
    request_method: str
    request_payload: str
    request_ip: str | None
    login_location: str | None
    request_os: str | None
    request_browser: str | None
    response_code: int
    response_json: str
    process_time: str
    signature: str | None
    signed_fields: str | None
    description: str | None
    created_id: int | None
    updated_id: int | None
    username: str | None
    mobile: str | None
    login_platform: str | None
    status: str = "0"


@runtime_checkable
class OperationLogSink(Protocol):
    """操作日志落库槽位（``log.operation_sink``）。"""

    async def write(self, entry: OperationLogEntry, session: AsyncSession) -> None:
        """把日志写入存储。

        参数:
        - entry (OperationLogEntry): 日志内容。
        - session (AsyncSession): 由内核开启的数据库会话。

        返回:
        - None
        """
        ...


@runtime_checkable
class ParamsProvider(Protocol):
    """系统参数槽位（``config.params_provider``）。"""

    async def get_system_config(self, redis: Any) -> dict[str, Any]:
        """读取中间件所需的系统配置。

        参数:
        - redis (Any): Redis 客户端。

        返回:
        - dict[str, Any]: 配置字典。
        """
        ...

    def set_param(self, key: str, value: str, name: str | None = None) -> None:
        """写入/更新一条系统参数（调度器运行时状态用）。

        参数:
        - key (str): 配置键。
        - value (str): 配置值。
        - name (str | None): 配置名称（仅新建时使用）。

        返回:
        - None
        """
        ...


@runtime_checkable
class UserResolver(Protocol):
    """用户解析槽位（``auth.user_resolver``）。"""

    async def resolve(self, db: AsyncSession, username: str) -> Any | None:
        """按登录名加载用户（含角色/部门/岗位预加载）。

        参数:
        - db (AsyncSession): 数据库会话。
        - username (str): 登录名。

        返回:
        - Any | None: 用户对象；不存在时返回 ``None``。
        """
        ...


@runtime_checkable
class JobLogSink(Protocol):
    """定时任务日志槽位（``scheduler.job_log_sink``）。

    调用方是**内核调度器**（``app/core/ap_scheduler.py``）与**插件运行时**
    （``app/core/plugin/runtime.py``），实现方是插件（``module_task``）。方法集必须覆盖
    全部调用点，缺失任何一个都会在运行期抛 ``AttributeError``：

    ``create`` / ``update`` / ``update_pending`` / ``update_latest`` / ``on_removed`` /
    ``clear_all`` / ``cancel_pending`` / ``sync_jobs`` / ``register``。

    除 ``register`` 外全部为同步方法（与 APScheduler 的 ``ThreadPoolExecutor`` 线程模型
    一致）；``register`` 由插件启动阶段 ``await`` 调用，故必须为协程。
    """

    def create(
        self,
        job_id: str | int,
        job_name: str | None,
        trigger_type: str,
        status: str,
        next_run_time: str | None = None,
        job_state: str | None = None,
    ) -> int | None:
        """创建任务日志并返回主键。

        参数:
        - job_id (str | int): 任务 ID。
        - job_name (str | None): 任务名称。
        - trigger_type (str): 触发方式（``cron``/``interval``/``date``/``manual``）。
        - status (str): 初始状态。
        - next_run_time (str | None): 下次执行时间（内核从 APScheduler 任务对象读取）。
        - job_state (str | None): 任务状态快照（用于前端展示任务定义）。

        返回:
        - int | None: 新日志主键；写入失败时返回 ``None``。
        """
        ...

    def update(self, log_id: int, status: str, result: str | None, error: str | None) -> None:
        """按日志主键更新状态。

        参数:
        - log_id (int): 日志主键。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。

        返回:
        - None
        """
        ...

    def update_pending(
        self,
        job_id: str | int,
        status: str,
        result: str | None = None,
        error: str | None = None,
        next_run_time: str | None = None,
        job_state: str | None = None,
    ) -> None:
        """把该任务最新的 ``pending`` 日志更新为新状态。

        周期性任务提交执行时用它把 ``pending`` 推进为 ``running``。

        参数:
        - job_id (str | int): 任务 ID。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。
        - next_run_time (str | None): 下次执行时间。
        - job_state (str | None): 任务状态快照。

        返回:
        - None
        """
        ...

    def update_latest(
        self,
        job_id: str | int,
        status: str,
        result: str | None = None,
        error: str | None = None,
        next_run_time: str | None = None,
        job_state: str | None = None,
        job_name: str | None = None,
        trigger_type: str | None = None,
    ) -> None:
        """更新该任务最近一条日志；不存在时补建。

        参数:
        - job_id (str | int): 任务 ID。
        - status (str): 新状态。
        - result (str | None): 执行结果。
        - error (str | None): 错误信息。
        - next_run_time (str | None): 下次执行时间。
        - job_state (str | None): 任务状态快照。
        - job_name (str | None): 任务名称；补建日志时写入，避免前端列表列为空。
        - trigger_type (str | None): 触发方式；补建日志时写入，避免前端列表列为空。

        返回:
        - None
        """
        ...

    def on_removed(self, job_id: str | int) -> None:
        """任务从调度器移除时的收尾（把未完成日志标记为已取消）。

        参数:
        - job_id (str | int): 任务 ID。

        返回:
        - None
        """
        ...

    def clear_all(self) -> None:
        """清空全部任务日志。

        返回:
        - None
        """
        ...

    def cancel_pending(self) -> None:
        """把所有 ``pending`` 状态的日志标记为已取消。

        返回:
        - None
        """
        ...

    def sync_jobs(self, jobs_data: list[dict[str, str | None]]) -> int:
        """把调度器中的任务批量同步为 ``pending`` 日志。

        参数:
        - jobs_data (list[dict[str, str | None]]): 每项含 ``job_id``/``job_name``/
          ``trigger_type``/``next_run_time``/``job_state``。

        返回:
        - int: 新建的日志条数。
        """
        ...

    async def register(self, job: JobSpec) -> None:
        """把插件声明的定时任务注册进调度器（插件启动阶段 ``await``）。

        实现约定：按 ``JobSpec.trigger``（``"cron"``/``"interval"``/``"date"``）选触发器；
        ``trigger`` 缺省时按内核 ``add_*_job`` 的读取优先级推断（``trigger_args`` 先于
        ``cron`` / ``interval``）。无法确定触发器类型或参数非法时必须抛 ``ValueError``，
        不得静默跳过 —— 静默跳过会让任务永远不执行且无人察觉（调用方逐条隔离并记日志）。

        参数:
        - job (JobSpec): 任务定义。

        返回:
        - None

        异常:
        - ValueError: ``trigger`` 取值非法，或触发器类型/参数无法确定。
        """
        ...
