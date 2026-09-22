"""数据权限模型槽位实现。"""

from __future__ import annotations

from typing import Any

from app.plugin.module_system.dept.model import DeptModel
from app.plugin.module_system.user.model import UserModel


def data_scope_models() -> dict[str, Any]:
    """返回数据权限过滤所需的模型映射。

    返回:
    - dict[str, Any]: ``{"dept_model": DeptModel, "user_model": UserModel}``
    """
    return {"dept_model": DeptModel, "user_model": UserModel}
