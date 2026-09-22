import json
from collections.abc import AsyncGenerator

from fastapi import Depends, Query, Request
from redis.asyncio.client import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import RedisInitKeyConfig
from app.config.setting import settings
from app.core.auth.schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.core.logger import log
from app.core.plugin.slots import SLOT_AUTH_USER_RESOLVER, get
from app.core.redis_crud import RedisCURD
from app.core.security import OAuth2Schema, decode_access_token


async def db_getter() -> AsyncGenerator[AsyncSession]:
    """获取数据库会话连接

    返回:
    - AsyncSession: 数据库会话连接
    """
    async with async_db_session() as session:
        async with session.begin():
            yield session


async def redis_getter(request: Request) -> Redis:
    """获取Redis连接

    参数:
    - request (Request): 请求对象

    返回:
    - Redis: Redis连接
    """
    return request.app.state.redis


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(db_getter),
    redis: Redis = Depends(redis_getter),
    token: str = Depends(OAuth2Schema),
) -> AuthSchema:
    """获取当前用户

    参数:
    - request (Request): 请求对象
    - db (AsyncSession): 数据库会话
    - redis (Redis): Redis连接
    - token (str): 访问令牌

    返回:
    - AuthSchema: 认证信息模型
    """
    if not token:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 处理Bearer token
    if token.startswith("Bearer"):
        token = token.split(" ")[1]

    payload = decode_access_token(token)
    if not payload or not hasattr(payload, "is_refresh") or payload.is_refresh:
        raise CustomException(msg="非法凭证", code=10401, status_code=401)

    online_user_info = payload.sub
    # 从Redis中获取用户信息
    user_info = json.loads(online_user_info)  # 确保是字典类型

    session_id = user_info.get("session_id")
    if not session_id:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 检查用户是否在线
    online_ok = await RedisCURD(redis).exists(
        key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}"
    )
    if not online_ok:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 如果启用了滑动过期，自动续期token
    if settings.TOKEN_SLIDING_EXPIRE:
        await RedisCURD(redis).expire(
            key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}",
            expire=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        )
        await RedisCURD(redis).expire(
            key=f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{session_id}",
            expire=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        )

    # 关闭数据权限过滤，避免当前用户查询被拦截
    auth = AuthSchema(db=db, check_data_scope=False)
    username = user_info.get("user_name")
    if not username:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    resolver = get(SLOT_AUTH_USER_RESOLVER)
    if resolver is None:
        log.warning(
            "⚠️ 用户解析槽位 auth.user_resolver 未提供，无法认证"
        )
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    user = await resolver.resolve(db, username)
    if not user:
        raise CustomException(msg="用户不存在", code=10401, status_code=401)
    if user.status == "1":
        raise CustomException(msg="用户已被停用", code=10401, status_code=401)

    # 设置请求上下文
    request.scope["user_id"] = user.id
    request.scope["user_username"] = user.username
    request.scope["user_mobile"] = user.mobile
    request.scope["login_type"] = user_info.get("login_type")

    # 过滤可用的角色和职位
    if hasattr(user, "roles"):
        user.roles = [role for role in user.roles if role and role.status]
    if hasattr(user, "positions"):
        user.positions = [pos for pos in user.positions if pos and pos.status]

    auth.user = user
    return auth


async def get_current_user_ws(
    token: str = Query(..., description="认证token"),
    db: AsyncSession = Depends(db_getter),
    redis: Redis = Depends(redis_getter),
) -> AuthSchema:
    """获取当前用户（WebSocket专用，从查询参数获取token）

    参数:
    - token (str): 认证token
    - db (AsyncSession): 数据库会话
    - redis (Redis): Redis连接

    返回:
    - AuthSchema: 认证信息模型
    """
    return await _verify_token(token, db, redis)


async def _verify_token(
    token: str,
    db: AsyncSession,
    redis: Redis,
) -> AuthSchema:
    """验证token并返回用户信息

    参数:
    - token (str): 认证token
    - db (AsyncSession): 数据库会话
    - redis (Redis): Redis连接

    返回:
    - AuthSchema: 认证信息模型
    """
    if not token:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 处理Bearer token（如果通过查询参数传递时包含Bearer前缀）
    if token.startswith("Bearer"):
        token = token.split(" ")[1]

    payload = decode_access_token(token)
    if not payload or not hasattr(payload, "is_refresh") or payload.is_refresh:
        raise CustomException(msg="非法凭证", code=10401, status_code=401)

    online_user_info = payload.sub
    # 从Redis中获取用户信息
    user_info = json.loads(online_user_info)  # 确保是字典类型

    session_id = user_info.get("session_id")
    if not session_id:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 检查用户是否在线
    online_ok = await RedisCURD(redis).exists(
        key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}"
    )
    if not online_ok:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    # 如果启用了滑动过期，自动续期token
    if settings.TOKEN_SLIDING_EXPIRE:
        await RedisCURD(redis).expire(
            key=f"{RedisInitKeyConfig.ACCESS_TOKEN.key}:{session_id}",
            expire=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        )
        await RedisCURD(redis).expire(
            key=f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{session_id}",
            expire=settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        )

    # 关闭数据权限过滤，避免当前用户查询被拦截
    auth = AuthSchema(db=db, check_data_scope=False)
    username = user_info.get("user_name")
    if not username:
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    resolver = get(SLOT_AUTH_USER_RESOLVER)
    if resolver is None:
        log.warning(
            "⚠️ 用户解析槽位 auth.user_resolver 未提供，无法认证"
        )
        raise CustomException(msg="认证已失效", code=10401, status_code=401)

    user = await resolver.resolve(db, username)
    if not user:
        raise CustomException(msg="用户不存在", code=10401, status_code=401)
    if user.status == "1":
        raise CustomException(msg="用户已被停用", code=10401, status_code=401)

    # 设置请求上下文
    # request.scope["user_id"] = user.id
    # request.scope["user_username"] = user.username
    # request.scope["login_type"] = user_info.get("login_type")

    # 过滤可用的角色和职位
    if hasattr(user, "roles"):
        user.roles = [role for role in user.roles if role and role.status]
    if hasattr(user, "positions"):
        user.positions = [pos for pos in user.positions if pos and pos.status]

    auth.user = user
    return auth
