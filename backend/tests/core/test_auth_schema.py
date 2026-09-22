"""内核认证基元测试。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.schema import AuthSchema


def _fake_db() -> AsyncSession:
    """构造未绑定连接的 AsyncSession（pydantic 会校验 ``db`` 字段类型）。

    返回:
    - AsyncSession: 未绑定连接的真实会话对象。
    """
    return AsyncSession()


class _FakeMenu:  # noqa: B903 — 测试用假对象，刻意保持最小实现
    """测试用菜单对象。"""

    def __init__(self, permission: str | None, status: str = "0") -> None:
        self.permission = permission
        self.status = status


class _FakeRole:
    """测试用角色对象。"""

    def __init__(self, permissions: list[str | None], status: str = "0") -> None:
        self.menus = [_FakeMenu(p) for p in permissions]
        self.status = status


class _FakeUser:
    """测试用用户对象。"""

    def __init__(self, perms: list[str | None], is_superuser: bool = False) -> None:
        self.roles = [_FakeRole(perms)]
        self.is_superuser = is_superuser
        self.id = 1
        self.username = "tester"


def test_auth_schema_accepts_structural_user() -> None:
    """AuthSchema 只要求结构化用户对象，不依赖 UserModel。"""
    user = _FakeUser(["system:user:query"])
    auth = AuthSchema(db=_fake_db(), user=user)
    assert auth.user is user
    assert auth.check_data_scope is True
    # 内核只按结构访问，不做 isinstance 校验（UserLike 仅用于静态类型标注）
    user_obj = auth.user
    assert user_obj is not None
    assert user_obj.roles[0].menus[0].permission == "system:user:query"


def test_auth_schema_user_optional() -> None:
    """user 可为 None（未认证态）。"""
    auth = AuthSchema(db=_fake_db())
    assert auth.user is None


def test_auth_permission_grants_superuser() -> None:
    """超管直接放行。"""

    async def _run() -> AuthSchema:
        from app.core.auth.permission import AuthPermission

        auth = AuthSchema(db=_fake_db(), user=_FakeUser(["x"], is_superuser=True))
        checker = AuthPermission(["system:user:create"])
        return await checker(auth=auth)

    import asyncio

    result = asyncio.run(_run())
    assert result.user is not None
    assert result.user.is_superuser is True


def test_auth_permission_denies_without_permission() -> None:
    """缺权限时抛 403。"""

    async def _run() -> None:
        from app.core.auth.permission import AuthPermission
        from app.core.exceptions import CustomException

        auth = AuthSchema(db=_fake_db(), user=_FakeUser([]))
        checker = AuthPermission(["system:user:create"])
        try:
            await checker(auth=auth)
        except CustomException as exc:
            assert exc.code == 10403
            return
        raise AssertionError("应抛出 403")

    import asyncio

    asyncio.run(_run())
