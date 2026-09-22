"""HTTP 请求限流（按客户端 + 端点隔离）。

历史背景：
- fastapi-limiter 0.2.0 的 ``__call__`` 仍遍历 ``app.routes`` 并读取
  ``route.path``（FastAPI ≥ 0.141 的 ``_IncludedRouter`` 兼容问题未修复），
  因此仍需子类覆盖 ``__call__``。
- pyrate-limiter 4.5.0 的 ``SingleBucketFactory`` 对所有 key 共享一个桶，
  限流额度全站共享而非按客户端隔离（2026-09-18 线上实测确认）。

本模块用自建计数器替代 pyrate-limiter 桶，实现真正的 per-key 隔离：

- ``InMemoryLimiter`` — 内存计数器（Redis 不可用时降级）
- ``RedisLimiter`` — Redis INCR+EXPIRE 原子计数（分布式共享）
- ``RateLimiter`` — 覆盖上游 ``__call__`` 的子类（解决 ``_IncludedRouter`` 兼容）
- ``WsRateLimiter`` — WebSocket 限流依赖（复用同一后端，WS 同样按客户端隔离）
- ``build_limiter`` — 根据 Redis 可用性构造后端实例
- ``http_limit_callback`` / ``ws_limit_callback`` — 超限回调
"""

import asyncio
import time
from typing import Any, NoReturn, Protocol

from fastapi import Request, Response
from fastapi_limiter.callback import default_callback as _default_callback
from fastapi_limiter.depends import RateLimiter as _UpstreamRateLimiter
from fastapi_limiter.identifier import default_identifier as _default_identifier
from starlette.websockets import WebSocket

from app.core.exceptions import CustomException
from app.core.logger import log

# ── 限流后端协议 ────────────────────────────────────────────────────────────────


class _LimiterBackend(Protocol):
    """限流后端协议：``acquire(key)`` 返回 ``True`` 表示放行。"""

    async def acquire(self, key: str) -> bool: ...


# ── InMemoryLimiter ─────────────────────────────────────────────────────────────

class InMemoryLimiter:
    """内存限流器（Redis 不可用时降级）。

    使用近似滑动窗口算法：保留当前窗口和上一窗口的计数，
    根据时间权重计算有效请求数，消除固定窗口在边界处的翻倍问题。

    ``effective_count = prev_count * weight + curr_count``

    其中 ``weight = 1 - (now - window_start) / window`` 表示上一窗口
    在当前滑动窗口中的重叠比例。

    参数:
        max_requests: 窗口内最大请求数。
        window_seconds: 滑动窗口时长（秒）。
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        # key → (curr_count, curr_start, prev_count)
        self._counters: dict[str, tuple[int, float, int]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        """检查并消耗一次配额。返回 ``True`` 表示放行，``False`` 表示拦截。"""
        async with self._lock:
            now = time.monotonic()
            state = self._counters.get(key)
            if state is None:
                self._counters[key] = (1, now, 0)
                self._maybe_evict(now)
                return 1 <= self._max

            curr_count, curr_start, prev_count = state
            elapsed = now - curr_start

            if elapsed >= self._window:
                # 窗口已过期：当前计数变为上一窗口，重置当前
                prev_count = curr_count
                curr_count = 0
                curr_start = now
                # elapsed = window → weight = 0，前一窗口的残留立即归零
                elapsed = self._window

            # 近似滑动窗口：上一窗口按重叠比例衰减
            weight = max(0.0, 1.0 - elapsed / self._window)
            effective = prev_count * weight + curr_count
            # 先检查再 increment：effective 不含本次请求
            if effective + 1 > self._max:
                return False  # 拦截：不 increment，不污染 curr_count
            curr_count += 1
            self._counters[key] = (curr_count, curr_start, prev_count)

            self._maybe_evict(now)
            return True

    def _maybe_evict(self, now: float) -> None:
        """惰性清理：超阈值时淘汰已过期的 key；仍超则删最早的那批。"""
        if len(self._counters) <= 500:
            return
        expired = [k for k, (_, start, _) in self._counters.items()
                   if now - start >= self._window]
        for k in expired:
            del self._counters[k]
        if len(self._counters) > 500:
            for k in sorted(self._counters, key=lambda k: self._counters[k][1]
                            )[:len(self._counters) - 500]:
                del self._counters[k]


# ── RedisLimiter ────────────────────────────────────────────────────────────────

class RedisLimiter:
    """Redis 限流器（分布式共享）。

    用 ``INCR + EXPIRE NX`` 原子计数：首次 ``INCR`` 自动初始化为 1，
    ``EXPIRE ... NX`` 只在 key 不存在时设置窗口。Redis TTL 自动清理。

    参数:
        redis: redis.asyncio.Redis 实例。
        max_requests: 窗口内最大请求数。
        window_seconds: 滑动窗口时长（秒）。
    """

    def __init__(self, redis: Any, max_requests: int, window_seconds: int) -> None:
        self._redis = redis
        self._max = max_requests
        self._window = window_seconds

    async def acquire(self, key: str) -> bool:
        """检查并消耗一次配额。返回 ``True`` 表示放行，``False`` 表示拦截。"""
        redis_key = f"rl:{key}"
        pipe = self._redis.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, self._window, nx=True)
        result = await pipe.execute()
        count: int = result[0]
        return count <= self._max


# ── RateLimiter ─────────────────────────────────────────────────────────────────

class RateLimiter(_UpstreamRateLimiter):
    """HTTP 限流依赖（兼容 FastAPI ≥ 0.141，按客户端隔离）。

    上游 0.2.0 的 ``__call__`` 仍遍历 ``request.app.routes`` 并读取
    ``route.path``，在 FastAPI ≥ 0.141 下必然抛
    ``AttributeError: '_IncludedRouter' object has no attribute 'path'``。

    覆盖策略：不再遍历路由表，改用 ``request.scope["endpoint"]`` 定位端点。
    计数键 = ``客户端标识:端点全限定名``，穿过任意层 ``include_router`` 嵌套依然准确。

    参数:
        backend: 限流后端（``InMemoryLimiter`` 或 ``RedisLimiter``）。
        limiter: pyrate-limiter.Limiter 实例（保留以维持上游继承合法性，
            ``__call__`` 不再使用它）。
        identifier: 客户端标识提取函数（默认从 X-Forwarded-For 取 IP）。
        callback: 超限回调。
        blocking: 是否阻塞等待（默认 ``False``）。
    """

    _backend: _LimiterBackend

    def __init__(
        self,
        backend: _LimiterBackend,
        identifier: Any = None,
        callback: Any = None,
        blocking: bool = False,
    ) -> None:
        # 跳过父类 __init__（它要求 limiter: Limiter 参数，但我们不再使用它）
        # __call__ 已完全覆盖，只需设置 __call__ 实际读取的三个属性
        object.__init__(self)
        self.identifier = identifier or _default_identifier
        self.callback = callback or _default_callback
        self.blocking = blocking
        self._backend = backend

    async def __call__(self, request: Request, response: Response) -> None:
        """检查并消耗一次配额，超限时调用回调。"""
        endpoint = request.scope.get("endpoint")
        endpoint_key = (
            f"{getattr(endpoint, '__module__', '')}."
            f"{getattr(endpoint, '__qualname__', '')}"
            if endpoint is not None
            else request.scope.get("path", "")
        )

        identifier = self.identifier
        callback = self.callback
        rate_key = await identifier(request)
        key = f"{rate_key}:{endpoint_key}"
        acquired = await self._backend.acquire(key)
        if not acquired:
            return await callback(request, response)


# ── WsRateLimiter ───────────────────────────────────────────────────────────────

class WsRateLimiter:
    """WebSocket 限流依赖（复用同一后端，按客户端隔离）。

    上游 ``WebSocketRateLimiter`` 要求 pyrate-limiter ``Limiter`` 实例；本类改用
    ``_LimiterBackend``，既不在 WS 路径上保留全站共享计数的桶，也让 WS 与 HTTP
    共用同一套降级策略（Redis → 内存）。

    参数:
        backend: 限流后端（``InMemoryLimiter`` 或 ``RedisLimiter``）。
        identifier: 客户端标识提取函数（默认从 X-Forwarded-For 取 IP；
            ``WebSocket`` 同样具备 ``headers`` / ``client``）。
        callback: 超限回调（默认 ``ws_limit_callback``，关闭连接）。
    """

    def __init__(
        self,
        backend: _LimiterBackend,
        identifier: Any = None,
        callback: Any = None,
    ) -> None:
        self.identifier = identifier or _default_identifier
        self.callback = callback or ws_limit_callback
        self._backend = backend

    async def __call__(self, ws: WebSocket) -> None:
        """检查并消耗一次配额，超限时调用回调关闭连接。"""
        rate_key = await self.identifier(ws)
        acquired = await self._backend.acquire(f"ws:{rate_key}")
        if not acquired:
            return await self.callback(ws)


# ── 工厂 ────────────────────────────────────────────────────────────────────────

async def build_limiter(
    redis_client: Any | None = None,
    max_requests: int = 5,
    window_seconds: int = 10,
) -> _LimiterBackend:
    """根据 Redis 可用性构造限流后端。

    - Redis 可用 → ``RedisLimiter``（分布式限流，多实例共享计数）
    - Redis 不可用 → ``InMemoryLimiter``（单进程内存桶，重启丢失）

    参数:
        redis_client: redis.asyncio.Redis 实例，``None`` 表示 Redis 不可用。
        max_requests: 窗口内最大请求数（默认 5）。
        window_seconds: 滑动窗口时长（默认 10 秒）。

    返回:
        _LimiterBackend: ``InMemoryLimiter`` 或 ``RedisLimiter`` 实例。
    """
    if redis_client is not None:
        try:
            return RedisLimiter(redis_client, max_requests, window_seconds)
        except Exception:
            log.warning("Redis 限流后端初始化失败，降级为 InMemoryLimiter", exc_info=True)

    return InMemoryLimiter(max_requests, window_seconds)


def http_limit_callback(request: Request, response: Response, **_: Any) -> NoReturn:
    """HTTP 触发限流时的默认回调：抛出 429。

    参数:
        request (Request): 当前请求。
        response (Response): 当前响应（未直接使用，保留与限流器签名一致）。

    返回:
        无（始终抛出 CustomException）。
    """
    raise CustomException(
        status_code=429,
        msg="请求过于频繁，请稍后重试！",
        data={"Retry-After": "10"},
    )


async def ws_limit_callback(ws: WebSocket, **_: Any) -> None:
    """WebSocket 触发限流时的默认回调：关闭连接。

    参数:
        ws (WebSocket): 当前 WebSocket。

    返回:
        None
    """
    await ws.close(code=1008, reason="请求过于频繁，请稍后重试！10 秒后重试")
