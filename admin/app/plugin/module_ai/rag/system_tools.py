"""系统查询工具 - 让 Agent 能查询实时系统数据。"""
import json

from agno.tools import tool
from sqlalchemy import text

from app.core.database import async_db_session
from app.core.logger import log


@tool
async def query_system_users(limit: int = 10) -> str:
    """
    查询系统用户列表。

    参数:
    - limit (int): 返回记录数，默认10条

    返回:
    - str: JSON 格式的用户列表
    """
    try:
        async with async_db_session() as db:
            result = await db.execute(
                text("""
                    SELECT id, username, name, mobile, email, gender,
                           is_superuser, status, dept_id
                    FROM sys_user
                    WHERE is_deleted = false
                    ORDER BY id
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            rows = result.fetchall()
            users = [
                {
                    "id": r[0], "username": r[1], "name": r[2],
                    "mobile": r[3], "email": r[4], "gender": r[5],
                    "is_superuser": bool(r[6]), "status": r[7], "dept_id": r[8],
                }
                for r in rows
            ]
            return json.dumps(users, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"查询用户失败: {e}")
        return f"查询失败: {e}"


@tool
async def query_system_roles(limit: int = 10) -> str:
    """
    查询系统角色列表。

    参数:
    - limit (int): 返回记录数，默认10条

    返回:
    - str: JSON 格式的角色列表
    """
    try:
        async with async_db_session() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, code, data_scope, status
                    FROM sys_role
                    WHERE is_deleted = false
                    ORDER BY id
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            rows = result.fetchall()
            roles = [
                {"id": r[0], "name": r[1], "code": r[2], "data_scope": r[3], "status": r[4]}
                for r in rows
            ]
            return json.dumps(roles, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"查询角色失败: {e}")
        return f"查询失败: {e}"


@tool
async def query_system_menus(limit: int = 20) -> str:
    """
    查询系统菜单/权限列表。

    参数:
    - limit (int): 返回记录数，默认20条

    返回:
    - str: JSON 格式的菜单列表
    """
    try:
        async with async_db_session() as db:
            result = await db.execute(
                text("""
                    SELECT id, name, type, permission, icon, route_path, parent_id, status
                    FROM sys_menu
                    WHERE is_deleted = false
                    ORDER BY "order"
                    LIMIT :limit
                """),
                {"limit": limit},
            )
            rows = result.fetchall()
            menus = [
                {
                    "id": r[0], "name": r[1], "type": r[2], "permission": r[3],
                    "icon": r[4], "route_path": r[5], "parent_id": r[6], "status": r[7],
                }
                for r in rows
            ]
            return json.dumps(menus, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"查询菜单失败: {e}")
        return f"查询失败: {e}"


@tool
async def query_system_stats() -> str:
    """
    查询系统统计概览：用户数、角色数、菜单数、AI模型数等。

    返回:
    - str: JSON 格式的系统统计信息
    """
    try:
        async with async_db_session() as db:
            stats: dict[str, int] = {}
            for table, key in [
                ("sys_user", "用户数"), ("sys_role", "角色数"),
                ("sys_menu", "菜单数"), ("sys_dept", "部门数"),
                ("sys_dict_type", "字典类型数"), ("sys_param", "参数数"),
                ("sys_log", "日志数"),
                ("ai_provider", "AI供应商数"), ("ai_model", "AI模型数"),
            ]:
                result = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE is_deleted = false")
                )
                stats[key] = result.scalar() or 0

            return json.dumps(stats, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"查询统计失败: {e}")
        return f"查询失败: {e}"


def get_system_tools() -> list:
    """返回系统查询工具列表。"""
    return [
        query_system_users,
        query_system_roles,
        query_system_menus,
        query_system_stats,
    ]
