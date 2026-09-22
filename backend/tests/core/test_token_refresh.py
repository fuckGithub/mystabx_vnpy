"""刷新令牌的鉴权契约。

守三件在真实使用中会直接让用户撞墙、或被悄悄削弱的性质：

1. 刷新路由**不得**要求前置的 access token。access token 过期正是刷新要解决的
   场景，挂上 ``Depends(get_current_user)`` 会让本接口对过期令牌必然 401 ——
   用户每 30 分钟被强制重新登录，刷新令牌形同虚设。
2. 提交上来的刷新令牌必须与 Redis 中留存的那一份逐字一致。否则登出
   （``logout_service`` 删除该 key）形同虚设，且旧令牌可被无限续期。
3. access token 不能冒充刷新令牌。

测试在**同一个事件循环**内构造 fakeredis 并调用服务，避免把异步假实例跨循环使用。
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import patch

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.common.enums import RedisInitKeyConfig
from app.core.auth.schema import JWTPayloadSchema
from app.core.auth.session import SessionInfo
from app.core.exceptions import CustomException
from app.core.redis_crud import RedisCURD
from app.core.security import create_access_token, decode_access_token
from app.plugin.module_system.auth.schema import JWTOutSchema, RefreshTokenPayloadSchema
from app.plugin.module_system.auth.service import LoginService
from app.plugin.module_system.user.crud import UserCRUD

SESSION_ID = "sess-refresh-1"
USER_ID = 7


def _sub() -> str:
    """与登录时写进令牌完全一致的会话载荷。"""
    return SessionInfo(
        name="管理员",
        session_id=SESSION_ID,
        user_id=USER_ID,
        user_name="super",
    ).model_dump_json()


def _token(*, is_refresh: bool, seconds: int = 1800) -> str:
    """造一个令牌。

    ``JWTPayloadSchema`` 只有 ``sub``/``is_refresh``/``exp``，没有 jti —— 同一秒内
    相同 ``seconds`` 生成的两个令牌会**逐字相同**，那样「存留的不一致」这类断言会
    假绿。故凡需要两个不同令牌处，都用不同 ``seconds`` 保证必然不同。
    """
    return create_access_token(
        payload=JWTPayloadSchema(
            sub=_sub(),
            is_refresh=is_refresh,
            exp=datetime.now() + timedelta(seconds=seconds),
        )
    )


class _User:
    """打桩用户（只需要刷新流程用到的两个属性）。"""

    id = USER_ID
    username = "super"


async def _user_lookup(*_args: object, **_kwargs: object) -> _User:
    """替掉 ``UserCRUD.get_by_id_crud``（避免依赖真实库与用户行）。"""
    return _User()


def _dummy_request() -> Request:
    """刷新型服务接收 ``request`` 但从不使用它；给一个最小可用的 Request 以满足类型。"""
    return Request(scope={"type": "http", "method": "POST", "path": "/", "headers": []})


def _refresh(
    *, stored: str | None, submitted: str
) -> tuple[JWTOutSchema | CustomException, str | None]:
    """种下 Redis 留存值 → 调刷新服务 → 返回 (结果或异常, 刷新后的留存值)。

    数据库会话用内存 SQLite 真实构造 —— ``AuthSchema`` 会校验 ``db`` 的类型，
    传 ``None`` 会被 pydantic 直接拒绝；用户查询本身被打桩，故无需任何表。
    """

    async def _run() -> tuple[JWTOutSchema | CustomException, str | None]:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        key = f"{RedisInitKeyConfig.REFRESH_TOKEN.key}:{SESSION_ID}"
        if stored is not None:
            await redis.set(key, stored)

        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                with patch.object(UserCRUD, "get_by_id_crud", _user_lookup):
                    try:
                        result = await LoginService.refresh_token_service(
                            db=db,
                            redis=redis,
                            request=_dummy_request(),
                            refresh_token=RefreshTokenPayloadSchema(refresh_token=submitted),
                        )
                    except CustomException as exc:
                        return exc, None
        finally:
            await engine.dispose()

        kept = await redis.get(key)
        return result, kept.decode() if isinstance(kept, bytes) else kept

    return asyncio.run(_run())


def test_refresh_succeeds_without_access_token(
    test_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """**不带任何 Authorization 头**也能刷新成功 —— 本缺陷的回归守卫。

    access token 过期正是刷新要解决的场景。若刷新路由又挂上
    ``Depends(get_current_user)``，这里会直接 401（"认证已失效"），用户每 30
    分钟被强制重新登录。

    注：不能用「遍历 app.routes 找路由」的结构断言 —— FastAPI ≥ 0.141 的
    ``include_router`` 是惰性的（``_IncludedRouter``），路由不会出现在
    ``app.routes`` 里，只能从行为上验证。
    """
    refresh_token = _token(is_refresh=True)

    async def _stored(*_args: object, **_kwargs: object) -> str:
        return refresh_token

    async def _noop(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(RedisCURD, "get", _stored)
    monkeypatch.setattr(RedisCURD, "set", _noop)
    monkeypatch.setattr(UserCRUD, "get_by_id_crud", _user_lookup)

    response = test_client.post(
        "/system/auth/token/refresh",
        json={"refresh_token": refresh_token},
        # TestClient 的客户端地址是字面量 "testclient"，会被操作日志的 IP 校验拒掉
        # （与本用例无关）；带上 X-Forwarded-For 给出一个合法地址。
        headers={"X-Forwarded-For": "127.0.0.1"},
    )

    assert response.status_code == 200, (
        f"不带 access token 无法刷新（{response.status_code} {response.json().get('msg')}）："
        "刷新路由可能又要求了有效 access token"
    )
    data = response.json()["data"]
    assert data["refresh_token"] != refresh_token, "刷新令牌未轮换"
    assert decode_access_token(data["access_token"]).is_refresh is False


def test_refresh_succeeds_and_rotates_stored_token() -> None:
    """存留值一致 → 换发新令牌，并把 Redis 里的那份一并换成新的（轮换）。"""
    old = _token(is_refresh=True, seconds=1700)
    result, kept = _refresh(stored=old, submitted=old)

    assert not isinstance(result, CustomException), result
    assert result.access_token and result.refresh_token
    assert result.refresh_token != old, "刷新令牌未轮换：旧令牌可被重放"
    assert kept == result.refresh_token, "Redis 里存的仍是旧刷新令牌"
    assert decode_access_token(result.access_token).is_refresh is False


def test_logout_invalidates_refresh_token() -> None:
    """登出删掉 Redis 键后，旧刷新令牌必须失效（否则登出形同虚设）。"""
    result, _ = _refresh(stored=None, submitted=_token(is_refresh=True))

    assert isinstance(result, CustomException)
    assert result.status_code == 401


def test_stale_refresh_token_is_rejected() -> None:
    """与 Redis 中留存值不一致（轮换前/登出前的旧令牌）必须被拒。"""
    result, _ = _refresh(
        stored=_token(is_refresh=True, seconds=1700),
        submitted=_token(is_refresh=True, seconds=1600),
    )

    assert isinstance(result, CustomException)
    assert result.status_code == 401


def test_access_token_cannot_be_used_as_refresh_token() -> None:
    """拿 access token 冒充刷新令牌必须被拒。"""
    access = _token(is_refresh=False, seconds=1700)
    result, _ = _refresh(stored=access, submitted=access)

    assert isinstance(result, CustomException)
    assert result.status_code == 401
    assert "刷新令牌" in result.msg


def test_refresh_payload_must_carry_session_and_user() -> None:
    """载荷缺会话/用户时给 401，而不是 500。"""
    token = create_access_token(
        payload=JWTPayloadSchema(
            sub=json.dumps({"user_name": "super"}),
            is_refresh=True,
            exp=datetime.now() + timedelta(seconds=600),
        )
    )
    result, _ = _refresh(stored=token, submitted=token)

    assert isinstance(result, CustomException)
    assert result.status_code == 401


@pytest.mark.parametrize("leader", ["Bearer ", ""])
def test_bad_signature_is_rejected(leader: str) -> None:
    """签名被篡改的令牌一律 401（无论是否带 Bearer 前缀）。"""
    result, _ = _refresh(stored=None, submitted=f"{leader}not-a-jwt")

    assert isinstance(result, CustomException)
    assert result.status_code == 401
