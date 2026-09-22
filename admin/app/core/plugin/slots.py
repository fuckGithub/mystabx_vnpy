"""命名槽位：内核定义接口，插件在启动时注入实现。

槽位缺失时 ``get()`` 返回默认值，调用方据此降级 —— 这是"删除任意插件应用仍可启动"的技术基石。
"""

from __future__ import annotations

from typing import Any

SLOT_AUTH_USER_RESOLVER = "auth.user_resolver"
"""``UserResolver``：token → 用户对象（由 module_system 提供）。"""

SLOT_AUTH_DATA_SCOPE_MODELS = "auth.data_scope_models"
"""``dict[str, Any]``：``{"dept_model": ..., "user_model": ...}``（由 module_system 提供）。"""

SLOT_LOG_OPERATION_SINK = "log.operation_sink"
"""``OperationLogSink``：操作日志落库（由 module_system 提供）。"""

SLOT_CONFIG_PARAMS_PROVIDER = "config.params_provider"
"""``ParamsProvider``：系统参数读写（由 module_system 提供）。"""

SLOT_SCHEDULER_JOB_LOG_SINK = "scheduler.job_log_sink"
"""``JobLogSink``：定时任务日志落库（由 module_task 提供）。"""

_slots: dict[str, Any] = {}


def provide(name: str, impl: Any) -> None:
    """注入槽位实现（后注入覆盖先注入）。

    参数:
    - name (str): 槽位名。
    - impl (Any): 实现对象。

    返回:
    - None
    """
    _slots[name] = impl


def get(name: str, default: Any = None) -> Any:
    """取槽位实现。

    参数:
    - name (str): 槽位名。
    - default (Any): 未注入时的返回值。

    返回:
    - Any: 实现对象或 ``default``。
    """
    return _slots.get(name, default)


def clear_slots() -> None:
    """清空全部槽位（测试隔离用）。

    返回:
    - None
    """
    _slots.clear()
