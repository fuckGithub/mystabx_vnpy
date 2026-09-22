"""种子应用器测试：按行幂等、外键解析、层级递归。

异步用例一律用 ``asyncio.run`` + 独立 SQLite 引擎，避免依赖 pytest 异步插件。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.base_model import MappedBase
from app.core.plugin.context import SeedRelation

# 确保目标模型及其关联模型已注册到 metadata（module_system 的模型互相以字符串名
# 引用，mapper 初始化需要完整注册表；自 T18 起不再由包导入连带加载，改用插件
# 声明的模型清单，与运行时同源）
from app.core.plugin.loader import import_plugin_models
from app.core.seed import SeedApplier, resolve_model
from app.plugin.module_system.dept.model import DeptModel
from app.plugin.module_system.menu.model import MenuModel  # noqa: F401
from app.plugin.module_system.plugin import MODEL_PATHS
from app.plugin.module_system.role.model import RoleModel
from app.plugin.module_system.user.model import UserModel, UserRolesModel

import_plugin_models("system", list(MODEL_PATHS))


def _run(coro: Coroutine[Any, Any, Any]) -> Any:
    """在独立事件循环中执行协程。

    参数:
    - coro (Coroutine): 待执行协程。

    返回:
    - Any: 协程返回值。
    """
    return asyncio.run(coro)


async def _with_session(tmp_path: Path, body: Any) -> Any:
    """建库、建表、开会话并执行 ``body(session)``，结束后销毁引擎。

    参数:
    - tmp_path (Path): 临时目录。
    - body (Any): 接收 AsyncSession 的协程函数。

    返回:
    - Any: ``body`` 的返回值。
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'seed.db'}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(MappedBase.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            result = await body(session)
            await session.commit()
            return result
    finally:
        await engine.dispose()


def test_resolve_model_known_and_unknown() -> None:
    """已知表名可解析到模型类，未知返回 None。"""
    assert resolve_model("sys_dept") is DeptModel
    assert resolve_model("no_such_table") is None


def test_apply_writes_rows(tmp_path: Path) -> None:
    """首次写入成功并返回写入行数。"""

    async def body(session: Any) -> int:
        applier = SeedApplier(session)
        return await applier.apply(
            SeedSpecFactory.dept([{"name": "总公司", "code": "GROUP", "status": "0"}])
        )

    assert _run(_with_session(tmp_path, body)) == 1


def test_apply_is_idempotent_by_natural_key(tmp_path: Path) -> None:
    """相同自然键第二次写入被跳过。"""

    async def body(session: Any) -> tuple[int, int, int]:
        applier = SeedApplier(session)
        spec = SeedSpecFactory.dept([{"name": "总公司", "code": "GROUP", "status": "0"}])
        first = await applier.apply(spec)
        await session.commit()
        second = await applier.apply(spec)
        await session.commit()
        total = await session.scalar(select(func.count()).select_from(DeptModel))
        return first, second, int(total or 0)

    first, second, total = _run(_with_session(tmp_path, body))
    assert (first, second, total) == (1, 0, 1)


def test_apply_resolves_relation(tmp_path: Path) -> None:
    """relations 把引用表主键填入目标字段。"""

    async def body(session: Any) -> int | None:
        applier = SeedApplier(session)
        await applier.apply(
            SeedSpecFactory.dept([{"name": "总公司", "code": "GROUP", "status": "0"}])
        )
        await session.commit()
        await applier.apply(
            SeedSpecFactory.dept([
                {"name": "分公司", "code": "BRANCH", "status": "0", "parent_code": "GROUP"}
            ])
        )
        await session.commit()
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "BRANCH"))
        return None if child is None else int(child.parent_id)  # type: ignore[arg-type]

    assert _run(_with_session(tmp_path, body)) == 1


def test_apply_skips_row_when_relation_unresolved(tmp_path: Path) -> None:
    """引用键解析不到时跳过该行，不写脏数据（既返回 0，也没有行落库）。"""

    async def body(session: Any) -> tuple[int, int]:
        applier = SeedApplier(session)
        written = await applier.apply(
            SeedSpecFactory.dept([
                {"name": "分公司", "code": "BRANCH", "status": "0", "parent_code": "MISSING"}
            ])
        )
        await session.commit()
        total = await session.scalar(select(func.count()).select_from(DeptModel))
        return written, int(total or 0)

    assert _run(_with_session(tmp_path, body)) == (0, 0)


def test_apply_treats_explicit_null_relation_as_no_relation(tmp_path: Path) -> None:
    """显式写 ``parent_code: None`` 视为「根节点、无父」，该行照常写入。"""

    async def body(session: Any) -> tuple[int, int | None]:
        applier = SeedApplier(session)
        written = await applier.apply(
            SeedSpecFactory.dept([
                {"name": "根部门", "code": "ROOT", "status": "0", "parent_code": None}
            ])
        )
        await session.commit()
        root = await session.scalar(select(DeptModel).where(DeptModel.code == "ROOT"))
        assert root is not None, "显式 null 的行被整行丢弃了"
        return written, root.parent_id

    written, parent_id = _run(_with_session(tmp_path, body))
    assert written == 1
    assert parent_id is None


def test_apply_writes_children_recursively(tmp_path: Path) -> None:
    """嵌套 children 递归写入并回填 parent_id。"""

    async def body(session: Any) -> tuple[int, int | None]:
        applier = SeedApplier(session)
        written = await applier.apply(
            SeedSpecFactory.dept([
                {
                    "name": "集团",
                    "code": "GROUP",
                    "status": "0",
                    "children": [{"name": "子公司", "code": "SUB", "status": "0"}],
                }
            ])
        )
        await session.commit()
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "SUB"))
        return written, None if child is None else int(child.parent_id)  # type: ignore[arg-type]

    written, parent_id = _run(_with_session(tmp_path, body))
    assert written == 2
    assert parent_id == 1


def test_apply_overwrites_explicit_null_parent_id_of_child(tmp_path: Path) -> None:
    """子行显式带 ``parent_id: None`` 时仍挂到父行，不留孤儿行。"""

    async def body(session: Any) -> tuple[int, int | None, int]:
        applier = SeedApplier(session)
        written = await applier.apply(
            SeedSpecFactory.dept([
                {
                    "name": "集团",
                    "code": "GROUP",
                    "status": "0",
                    "children": [
                        {"name": "子公司", "code": "SUB", "status": "0", "parent_id": None}
                    ],
                }
            ])
        )
        await session.commit()
        parent = await session.scalar(select(DeptModel).where(DeptModel.code == "GROUP"))
        assert parent is not None, "父行未落库"
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "SUB"))
        assert child is not None, "子行未落库"
        return written, child.parent_id, int(parent.id)

    written, child_parent_id, parent_id = _run(_with_session(tmp_path, body))
    assert written == 2
    assert child_parent_id == parent_id, "子行没挂到父行，成了孤儿行"


def test_apply_backfills_children_when_parent_row_exists(tmp_path: Path) -> None:
    """父行已存在（自然键命中）时，新子行仍被补齐并挂到既有父行主键。"""

    async def body(session: Any) -> tuple[int, int | None, int]:
        applier = SeedApplier(session)
        await applier.apply(
            SeedSpecFactory.dept([{"name": "集团", "code": "GROUP", "status": "0"}])
        )
        await session.commit()
        written = await applier.apply(
            SeedSpecFactory.dept([
                {
                    "name": "集团",
                    "code": "GROUP",
                    "status": "0",
                    "children": [{"name": "子公司", "code": "SUB", "status": "0"}],
                }
            ])
        )
        await session.commit()
        parent = await session.scalar(select(DeptModel).where(DeptModel.code == "GROUP"))
        assert parent is not None, "父行未落库"
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "SUB"))
        assert child is not None, "父行已存在时子行被静默丢弃"
        return written, child.parent_id, int(parent.id)

    written, child_parent_id, parent_id = _run(_with_session(tmp_path, body))
    assert written == 1
    assert child_parent_id == parent_id, "子行没挂到既有父行主键"


def test_apply_is_idempotent_for_parent_and_children(tmp_path: Path) -> None:
    """同一含父子树的声明连跑两次：第二次不重复写任何层级的行。"""

    def build_spec() -> Any:
        return SeedSpecFactory.dept([
            {
                "name": "集团",
                "code": "GROUP",
                "status": "0",
                "children": [
                    {
                        "name": "子公司",
                        "code": "SUB",
                        "status": "0",
                        "children": [{"name": "孙公司", "code": "LEAF", "status": "0"}],
                    }
                ],
            }
        ])

    async def body(session: Any) -> tuple[int, int, int]:
        applier = SeedApplier(session)
        first = await applier.apply(build_spec())
        await session.commit()
        second = await applier.apply(build_spec())
        await session.commit()
        total = await session.scalar(select(func.count()).select_from(DeptModel))
        return first, second, int(total or 0)

    assert _run(_with_session(tmp_path, body)) == (3, 0, 3)


def test_apply_nested_position_wins_over_child_parent_code(tmp_path: Path) -> None:
    """子行自带**可解析**的 ``parent_code`` 时，父键仍以嵌套位置为准（不被二次改写）。"""

    async def body(session: Any) -> tuple[int, int | None, int, int]:
        applier = SeedApplier(session)
        # 先写一个「别的父行」：子行的 parent_code 正指向它，用来证伪「引用优先」。
        await applier.apply(
            SeedSpecFactory.dept([{"name": "外部公司", "code": "OTHER", "status": "0"}])
        )
        await session.commit()
        written = await applier.apply(
            SeedSpecFactory.dept([
                {
                    "name": "集团",
                    "code": "GROUP",
                    "status": "0",
                    "children": [
                        {
                            "name": "子公司",
                            "code": "SUB",
                            "status": "0",
                            "parent_code": "OTHER",
                        }
                    ],
                }
            ])
        )
        await session.commit()
        nested_parent = await session.scalar(select(DeptModel).where(DeptModel.code == "GROUP"))
        other = await session.scalar(select(DeptModel).where(DeptModel.code == "OTHER"))
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "SUB"))
        assert nested_parent is not None, "嵌套父行未落库"
        assert other is not None, "被 parent_code 指向的行未落库"
        assert child is not None, "子行未落库"
        return written, child.parent_id, int(nested_parent.id), int(other.id)

    written, child_parent_id, nested_parent_id, other_id = _run(_with_session(tmp_path, body))
    assert written == 2
    assert child_parent_id != other_id, "子行被 parent_code 改写到引用目标（静默挂错父行）"
    assert child_parent_id == nested_parent_id, "子行没挂到嵌套位置的父行"


def test_apply_keeps_child_with_stale_parent_code(tmp_path: Path) -> None:
    """子行带**解析不到**的 ``parent_code`` 时仍被写入（嵌套位置已定父键，不走整行跳过）。"""

    async def body(session: Any) -> tuple[int, int | None]:
        applier = SeedApplier(session)
        written = await applier.apply(
            SeedSpecFactory.dept([
                {
                    "name": "集团",
                    "code": "GROUP",
                    "status": "0",
                    "children": [
                        {
                            "name": "子公司",
                            "code": "SUB",
                            "status": "0",
                            "parent_code": "NOT_EXIST",
                        }
                    ],
                }
            ])
        )
        await session.commit()
        child = await session.scalar(select(DeptModel).where(DeptModel.code == "SUB"))
        assert child is not None, "子行因陈旧 parent_code 被整行丢弃"
        return written, child.parent_id

    written, parent_id = _run(_with_session(tmp_path, body))
    assert written == 2
    assert parent_id == 1


def test_apply_without_natural_key_writes_only_when_table_empty(tmp_path: Path) -> None:
    """无自然键时退化为"表空才写"。"""

    async def body(session: Any) -> tuple[int, int]:
        applier = SeedApplier(session)
        spec = SeedSpecFactory.dept([{"name": "总公司", "code": "GROUP", "status": "0"}])
        spec.natural_key = None
        first = await applier.apply(spec)
        await session.commit()
        second = await applier.apply(spec)
        await session.commit()
        return first, second

    assert _run(_with_session(tmp_path, body)) == (1, 0)


def test_apply_writes_association_table_without_id(tmp_path: Path) -> None:
    """无 ``id`` 列的复合主键关联表也能按自然键写入并幂等（回归）。

    应用器曾无条件读写 ``model.id`` / ``obj.id``，而 ``sys_user_roles`` 只有复合主键
    ``(user_id, role_id)``：首启即 ``AttributeError``，整个插件的种子被回滚（实测）。
    """

    async def body(session: Any) -> tuple[int, int, int, tuple[int, int], tuple[int, int]]:
        applier = SeedApplier(session)
        await applier.apply(SeedSpecFactory.role([{"name": "管理员角色", "code": "ADMIN"}]))
        await applier.apply(
            SeedSpecFactory.user([{"username": "super", "password": "x", "name": "超管"}])
        )
        await session.commit()

        spec = SeedSpecFactory.user_roles([{"user_name": "super", "role_code": "ADMIN"}])
        first = await applier.apply(spec)
        await session.commit()
        second = await applier.apply(spec)
        await session.commit()

        rows = int(await session.scalar(select(func.count()).select_from(UserRolesModel)) or 0)
        link = await session.scalar(select(UserRolesModel))
        user_id = await session.scalar(select(UserModel.id).where(UserModel.username == "super"))
        role_id = await session.scalar(select(RoleModel.id).where(RoleModel.code == "ADMIN"))
        assert link is not None
        return first, second, rows, (link.user_id, link.role_id), (int(user_id), int(role_id))

    first, second, rows, link, expected = _run(_with_session(tmp_path, body))
    assert (first, second, rows) == (1, 0, 1)
    # user_name/role_code 不是表列，必须被剥掉并解析成真实的 user_id/role_id
    assert link == expected


def test_apply_skips_children_of_composite_pk_table(tmp_path: Path) -> None:
    """复合主键表不可能充当父行：带 ``children`` 的声明只写父行，不落孤儿行。"""

    async def body(session: Any) -> int:
        applier = SeedApplier(session)
        await applier.apply(SeedSpecFactory.role([{"name": "管理员角色", "code": "ADMIN"}]))
        await applier.apply(
            SeedSpecFactory.user([
                {"username": "super", "password": "x", "name": "超管"},
                {"username": "admin", "password": "x", "name": "管理员"},
            ])
        )
        await session.commit()

        spec = SeedSpecFactory.user_roles([
            {
                "user_name": "super",
                "role_code": "ADMIN",
                "children": [{"user_name": "admin", "role_code": "ADMIN"}],
            }
        ])
        await applier.apply(spec)
        await session.commit()
        return int(await session.scalar(select(func.count()).select_from(UserRolesModel)) or 0)

    # 子行可解析（admin 存在）却不能被写成行：否则就是一条挂不上父行的孤儿关联
    assert _run(_with_session(tmp_path, body)) == 1


class SeedSpecFactory:
    """测试用种子声明工厂。"""

    @staticmethod
    def dept(rows: list[dict]) -> Any:
        """构造 sys_dept 种子声明（自然键 code，parent_code → parent_id 关系）。

        参数:
        - rows (list[dict]): 种子行。

        返回:
        - SeedSpec: 种子声明。
        """
        from app.core.plugin.context import SeedSpec

        return SeedSpec(
            table="sys_dept",
            rows=rows,
            natural_key="code",
            relations=[
                SeedRelation(
                    field="parent_id",
                    ref_table="sys_dept",
                    ref_key="code",
                    source_field="parent_code",
                )
            ],
        )

    @staticmethod
    def role(rows: list[dict]) -> Any:
        """构造 sys_role 种子声明（自然键 code）。

        参数:
        - rows (list[dict]): 种子行。

        返回:
        - SeedSpec: 种子声明。
        """
        from app.core.plugin.context import SeedSpec

        return SeedSpec(table="sys_role", rows=rows, natural_key="code")

    @staticmethod
    def user(rows: list[dict]) -> Any:
        """构造 sys_user 种子声明（自然键 username）。

        参数:
        - rows (list[dict]): 种子行。

        返回:
        - SeedSpec: 种子声明。
        """
        from app.core.plugin.context import SeedSpec

        return SeedSpec(table="sys_user", rows=rows, natural_key="username")

    @staticmethod
    def user_roles(rows: list[dict]) -> Any:
        """构造 sys_user_roles 种子声明（复合主键关联表）。

        ``user_name`` / ``role_code`` 是引用来源键（非表列），由 relations 解析成
        ``user_id`` / ``role_id``。

        参数:
        - rows (list[dict]): 种子行。

        返回:
        - SeedSpec: 种子声明。
        """
        from app.core.plugin.context import SeedSpec

        return SeedSpec(
            table="sys_user_roles",
            rows=rows,
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
