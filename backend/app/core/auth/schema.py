"""内核认证基元：``AuthSchema`` / ``JWTPayloadSchema`` / ``UserLike``。

``user`` 字段声明为结构化 Protocol（``UserLike``），使内核不依赖任何具体业务模型
（如 ``module_system`` 的 ``UserModel``）。注意 ``UserLike`` 仅用于**静态类型标注**，
``AuthSchema.user`` 的运行时类型是 ``Any`` —— pydantic v2 在
``arbitrary_types_allowed=True`` 下仍会对字段做 ``isinstance`` 校验，而非
``@runtime_checkable`` 的 Protocol 会抛 ``TypeError``，故不能把 Protocol 直接当作字段类型。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession


class UserLike(Protocol):
    """当前登录用户所需的最小结构（由 module_system 的 UserModel 满足）。

    仅用于静态类型标注 —— **不加** ``@runtime_checkable``：它含数据成员，
    ``isinstance`` 检查在不同 Python 版本行为不一致，而内核只用结构访问。
    """

    id: int
    """用户主键。"""

    username: str
    """登录名。"""

    is_superuser: bool
    """是否超级管理员。"""

    status: str
    """状态（``"1"`` 表示停用）。"""

    roles: list[Any]
    """角色列表（每项含 ``status`` 与 ``menus``）。"""


class AuthSchema(BaseModel):
    """权限认证模型。"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: Any | None = Field(default=None, description="用户信息")
    check_data_scope: bool = Field(default=True, description="是否检查数据权限")
    db: AsyncSession = Field(description="数据库会话")


class JWTPayloadSchema(BaseModel):
    """JWT 载荷模型。"""

    sub: str = Field(..., description="用户登录信息")
    is_refresh: bool = Field(default=False, description="是否刷新 token")
    exp: datetime | int = Field(..., description="过期时间")

    @model_validator(mode="after")
    def validate_fields(self) -> JWTPayloadSchema:
        """校验 JWT 载荷字段的基本合法性。

        返回:
        - JWTPayloadSchema: 校验后的载荷实例。

        异常:
        - ValueError: 必填字段为空时抛出。
        """
        if not self.sub or len(self.sub.strip()) == 0:
            raise ValueError("会话编号不能为空")
        return self
