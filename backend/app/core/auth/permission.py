"""内核权限校验依赖：只读取传入对象的结构化字段，不做任何数据库访问。"""

from __future__ import annotations

from fastapi import Depends

from app.core.auth.schema import AuthSchema
from app.core.dependencies import get_current_user
from app.core.exceptions import CustomException
from app.core.logger import log


class AuthPermission:
    """权限验证类（行为与改造前一致）。"""

    def __init__(
        self,
        permissions: list[str] | None = None,
        check_data_scope: bool = True,
    ) -> None:
        """初始化权限验证。

        参数:
        - permissions (list[str] | None): 权限标识列表。
        - check_data_scope (bool): 是否启用数据权限校验。
        """
        self.permissions = permissions or []
        self.check_data_scope = check_data_scope

    async def __call__(self, auth: AuthSchema = Depends(get_current_user)) -> AuthSchema:
        """执行权限校验。

        参数:
        - auth (AuthSchema): 认证信息对象。

        返回:
        - AuthSchema: 认证信息对象。

        异常:
        - CustomException: 无权限时抛出 403。
        """
        auth.check_data_scope = self.check_data_scope

        # 超级管理员直接通过
        if auth.user and getattr(auth.user, "is_superuser", False):
            return auth

        # 无需验证权限
        if not self.permissions:
            return auth

        # 超级管理员权限标识
        if "*" in self.permissions or "*:*:*" in self.permissions:
            return auth

        # 检查用户是否有角色
        roles = getattr(auth.user, "roles", None) if auth.user else None
        if not roles:
            raise CustomException(msg="无权限操作", code=10403, status_code=403)

        # 获取用户权限集合
        user_permissions = {
            menu.permission
            for role in roles
            for menu in getattr(role, "menus", [])
            if role.status == "0" and menu.permission and menu.status == "0"
        }

        # 权限验证 - 满足任一权限即可
        if not any(perm in user_permissions for perm in self.permissions):
            log.error(f"用户缺少任何所需的权限: {self.permissions}")
            raise CustomException(msg="无权限操作", code=10403, status_code=403)

        return auth
