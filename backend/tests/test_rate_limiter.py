"""限流器按客户端隔离测试。

验证线上已知缺陷的修复：pyrate-limiter 4.5.0 单桶模式下限流额度全站共享，
不同客户端的请求互相消耗配额。

本测试不依赖 Redis / 数据库 / FastAPI app，纯单元测试。
"""

from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from starlette.websockets import WebSocket

from app.core.http_limit import InMemoryLimiter, RedisLimiter, WsRateLimiter


class TestInMemoryLimiter:
    """InMemoryLimiter 纯内存限流器测试。"""

    @pytest.fixture()
    def limiter(self) -> InMemoryLimiter:
        return InMemoryLimiter(max_requests=3, window_seconds=10)

    @pytest.mark.anyio()
    async def test_under_limit_passes(self, limiter: InMemoryLimiter) -> None:
        """在限额内应全部通过。"""
        for _ in range(3):
            assert await limiter.acquire("client-A:endpoint") is True

    @pytest.mark.anyio()
    async def test_over_limit_blocks(self, limiter: InMemoryLimiter) -> None:
        """超过限额后应被拦截。"""
        for _ in range(3):
            await limiter.acquire("client-A:endpoint")
        assert await limiter.acquire("client-A:endpoint") is False

    @pytest.mark.anyio()
    async def test_different_keys_are_isolated(self, limiter: InMemoryLimiter) -> None:
        """不同 key 的额度互相独立（这是修复的核心验证）。"""
        # client-A 用完 3 次额度
        for _ in range(3):
            await limiter.acquire("client-A:endpoint")
        assert await limiter.acquire("client-A:endpoint") is False

        # client-B 仍应有完整额度
        assert await limiter.acquire("client-B:endpoint") is True
        assert await limiter.acquire("client-B:endpoint") is True
        assert await limiter.acquire("client-B:endpoint") is True
        # client-B 第 4 次才被拦截
        assert await limiter.acquire("client-B:endpoint") is False

    @pytest.mark.anyio()
    async def test_different_endpoints_are_isolated(
        self, limiter: InMemoryLimiter
    ) -> None:
        """同一客户端对不同端点的额度互相独立。"""
        for _ in range(3):
            await limiter.acquire("client-A:endpoint-1")
        assert await limiter.acquire("client-A:endpoint-1") is False

        # 同一客户端访问另一个端点，应有完整额度
        assert await limiter.acquire("client-A:endpoint-2") is True

    @pytest.mark.anyio()
    async def test_window_reset(self) -> None:
        """窗口过期后额度应重置。"""
        limiter = InMemoryLimiter(max_requests=2, window_seconds=1)  # 1 秒窗口
        await limiter.acquire("k")
        await limiter.acquire("k")
        assert await limiter.acquire("k") is False

        await asyncio.sleep(1.1)  # 等窗口过期
        assert await limiter.acquire("k") is True

    @pytest.mark.anyio()
    async def test_stale_cleanup_evicts_expired_keys(self) -> None:
        """惰性清理：超阈值时应淘汰已过期的 key。"""
        limiter = InMemoryLimiter(max_requests=1, window_seconds=1)
        # 制造 600 个过期 key（阈值 500）
        for i in range(600):
            await limiter.acquire(f"ephemeral-{i}")
        await asyncio.sleep(1.1)

        # 触发清理
        await limiter.acquire("trigger")

        # 过期 key 应已被清理（字典大小回落）
        assert len(limiter._counters) < 600

    @pytest.mark.anyio()
    async def test_window_boundary_no_double_counting(self) -> None:
        """滑动窗口：窗口过期后前一窗口计数按时间权重衰减。

        固定窗口在窗口交界处会翻倍放行（窗口1末尾满额 + 窗口2开头满额）。
        滑动窗口应确保前一窗口的计数按重叠比例衰减，而非全权重计入下一窗口。
        """
        limiter = InMemoryLimiter(max_requests=4, window_seconds=1)

        # 窗口1：放行4次（满额）
        for _ in range(4):
            assert await limiter.acquire("k") is True
        assert await limiter.acquire("k") is False

        # 等窗口过期 + 0.2秒（前一窗口权重 = 1 - 0.2 = 0.8）
        await asyncio.sleep(1.2)
        # 此时 prev_count=4 × 0.8权重 = 3.2，effective=3.2，应允许放行
        assert await limiter.acquire("k") is True

        # 继续发请求直到被拦截，验证滑动窗口限制
        allowed = 1
        for _ in range(10):
            if await limiter.acquire("k"):
                allowed += 1
            else:
                break
        # 前一窗口 4×0.8=3.2 + 当前窗口 allowed 次 ≤ 4
        assert allowed <= 4, f"窗口边界处放行了 {allowed} 次，超过限额"

    @pytest.mark.anyio()
    async def test_max_keys_evicts_oldest(self) -> None:
        """超上限时应淘汰 expire 最小的 key（LRU 降级）。"""
        limiter = InMemoryLimiter(max_requests=100, window_seconds=60)
        # 制造 501 个活跃 key
        for i in range(501):
            await limiter.acquire(f"key-{i}")

        # 触发淘汰
        await limiter.acquire("trigger-overflow")

        # 总 key 数应 ≤ 500 + 1（trigger）
        assert len(limiter._counters) <= 501


class TestRedisLimiter:
    """RedisLimiter 测试（需要 fakeredis 或真实 Redis）。

    REDIS_ENABLE=False 时跳过。
    """

    @pytest.fixture()
    def redis_limiter(self):
        """构造 RedisLimiter（优先 fakeredis，否则跳过）。"""
        try:
            import fakeredis.aioredis

            redis = fakeredis.aioredis.FakeRedis()
            return RedisLimiter(redis=redis, max_requests=3, window_seconds=10)
        except ImportError:
            pytest.skip("fakeredis 未安装，跳过 Redis 限流器测试")

    @pytest.mark.anyio()
    async def test_under_limit_passes(self, redis_limiter: RedisLimiter) -> None:
        for _ in range(3):
            assert await redis_limiter.acquire("client-A:endpoint") is True

    @pytest.mark.anyio()
    async def test_over_limit_blocks(self, redis_limiter: RedisLimiter) -> None:
        for _ in range(3):
            await redis_limiter.acquire("client-A:endpoint")
        assert await redis_limiter.acquire("client-A:endpoint") is False

    @pytest.mark.anyio()
    async def test_different_keys_are_isolated(
        self, redis_limiter: RedisLimiter
    ) -> None:
        """不同 key 的额度互相独立（Redis 模式下同样必须隔离）。"""
        for _ in range(3):
            await redis_limiter.acquire("client-A:endpoint")
        assert await redis_limiter.acquire("client-A:endpoint") is False
        assert await redis_limiter.acquire("client-B:endpoint") is True

    @pytest.mark.anyio()
    async def test_redis_key_prefix(self, redis_limiter: RedisLimiter) -> None:
        """Redis key 应带 rl: 前缀，防与其他业务 key 冲突。"""
        await redis_limiter.acquire("my-key")
        # 检查 Redis 里是否有 rl:my-key
        keys = await redis_limiter._redis.keys("rl:*")
        assert any(b"rl:my-key" in k for k in keys)


class _FakeWebSocket:
    """最小 WebSocket 替身：``WsRateLimiter`` 只用到 identifier 与 ``close``。"""

    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self.closed_with: tuple[int, str] | None = None

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """记录关闭参数（默认回调会传 1008）。"""
        self.closed_with = (code, reason)


async def _ws_identifier(ws: Any) -> str:
    """测试用客户端标识函数：直接取替身上的 client_id。"""
    return ws.client_id


async def _hit(limiter: WsRateLimiter, ws: _FakeWebSocket) -> None:
    """把替身当作 ``WebSocket`` 交给限流器（仅测试用的类型桥接）。"""
    await limiter(cast(WebSocket, ws))


class TestWsRateLimiter:
    """``WsRateLimiter`` 复用同一后端，WS 同样按客户端隔离。"""

    @pytest.mark.anyio()
    async def test_under_limit_keeps_connection(self) -> None:
        """额度内不关闭连接。"""
        ws = _FakeWebSocket("client-A")
        limiter = WsRateLimiter(
            backend=InMemoryLimiter(max_requests=2, window_seconds=10),
            identifier=_ws_identifier,
        )
        await _hit(limiter, ws)
        await _hit(limiter, ws)
        assert ws.closed_with is None

    @pytest.mark.anyio()
    async def test_over_limit_closes_connection(self) -> None:
        """超限时走默认回调 ``ws_limit_callback``，以 1008 关闭连接。"""
        ws = _FakeWebSocket("client-A")
        limiter = WsRateLimiter(
            backend=InMemoryLimiter(max_requests=1, window_seconds=10),
            identifier=_ws_identifier,
        )
        await _hit(limiter, ws)
        await _hit(limiter, ws)
        assert ws.closed_with is not None
        assert ws.closed_with[0] == 1008

    @pytest.mark.anyio()
    async def test_clients_are_isolated(self) -> None:
        """不同客户端的 WS 额度互相独立（与 HTTP 侧同一后端、同一保证）。"""
        backend = InMemoryLimiter(max_requests=1, window_seconds=10)
        limiter = WsRateLimiter(backend=backend, identifier=_ws_identifier)
        client_a = _FakeWebSocket("client-A")
        client_b = _FakeWebSocket("client-B")

        await _hit(limiter, client_a)
        await _hit(limiter, client_b)
        assert client_a.closed_with is None
        assert client_b.closed_with is None

        # client-A 第 2 次超限被关闭，client-B 不受影响
        await _hit(limiter, client_a)
        assert client_a.closed_with is not None
        assert client_b.closed_with is None
