"""路由遍历共享模块：采集侧与校验侧的唯一语义来源。

用法：
    from route_walker import collect_routes, find_missing

说明：
    历史上同一套「递归展开路由树」逻辑在生成脚本（``scripts/dump_routes.py``）与
    校验测试（``tests/test_route_snapshot.py``）中各存一份，任一侧单独演进
    （最现实的是 FastAPI 升版后修补私有属性访问）都会让快照含义与断言含义静默分叉。
    故抽出本模块，两侧一律 import，不再各持一份。

覆盖的节点类型：
    - ``fastapi.routing.APIRoute``（含业务自定义子类，如 ``OperationLogRoute``）
    - ``starlette.routing.Route``（如 ``/openapi.json``，既非 APIRoute 又无子路由）
    - ``starlette.routing.WebSocketRoute``（如 ``/ai/chat/ws``，方法记为 ``WEBSOCKET``）
    - FastAPI 0.141 的懒挂载包装节点（``include_context`` + ``original_router``）
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from fastapi import FastAPI
from starlette.routing import Route, WebSocketRoute

EXCLUDED_METHODS: frozenset[str] = frozenset({"HEAD", "OPTIONS"})
"""不计入快照的 HTTP 方法（框架自动注册，不属于对外契约）。"""

WEBSOCKET_METHOD: str = "WEBSOCKET"
"""WebSocket 路由在快照中使用的伪方法名。"""

MIN_ROUTE_COUNT: int = 200
"""基线绝对下限：低于该条数说明注册管线整体退化，拒绝写出无效基线。"""

REQUIRED_MODULE_PREFIXES: tuple[str, ...] = (
    "/system/",
    "/common/",
    "/ai/",
    "/task/",
    "/monitor/",
    "/application/",
    "/generator/",
    "/example/",
)
"""基线必须各自覆盖至少一条路由的模块前缀。"""


def _own_endpoints(route: Any) -> list[tuple[str, str]] | None:
    """读取单个路由节点自身承载的「方法 + 路径」。

    参数:
    - route (Any): 单个路由节点。

    返回:
    - list[tuple[str, str]] | None: 节点自身（含懒挂载包装节点展开后）的端点列表；
      返回 ``None`` 表示该节点是纯容器，需由调用方递归其 ``routes``。
    """
    if isinstance(route, WebSocketRoute):
        return [(WEBSOCKET_METHOD, route.path)]
    if isinstance(route, Route):
        # APIRoute 是 starlette Route 的子类，一并在此处理。
        return [(method, route.path) for method in sorted(route.methods or ())]
    include_context = getattr(route, "include_context", None)
    original_router = getattr(route, "original_router", None)
    if include_context is not None and original_router is not None:
        inner_prefix = getattr(include_context, "prefix", "") or ""
        routes = getattr(original_router, "routes", None) or ()
        return [(method, inner_prefix + path) for method, path in _walk(routes)]
    return None


def _walk(routes: Iterable[Any], prefix: str = "") -> Iterator[tuple[str, str]]:
    """递归展开路由树，产出「方法 + 完整路径」。

    参数:
    - routes (Iterable[Any]): 待遍历的路由节点集合。
    - prefix (str): 上层累积的路径前缀。

    返回:
    - Iterator[tuple[str, str]]: 形如 ``("GET", "/common/health/")`` 的元素。
    """
    for route in routes:
        own = _own_endpoints(route)
        if own is not None:
            for method, path in own:
                yield method, prefix + path
            continue
        child_routes = getattr(route, "routes", None) or ()
        yield from _walk(child_routes, prefix + (getattr(route, "path", "") or ""))


def iter_endpoints(app: FastAPI) -> list[tuple[str, str]]:
    """递归展开应用路由树，返回全部「方法 + 路径」。

    与 ``collect_routes`` 的区别：本函数**不去重、不排序、不排除** ``HEAD``/``OPTIONS``，
    因此可用于重复路由检测（同一「方法 + 路径」出现多次即重复注册）。

    参数:
    - app (FastAPI): 应用实例。

    返回:
    - list[tuple[str, str]]: 形如 ``[("GET", "/common/health/"), ...]`` 的原始列表。
    """
    return list(_walk(app.routes))


def collect_routes(app: FastAPI) -> list[str]:
    """收集应用全部对外路由，返回排序去重后的 ``"METHOD /path"`` 列表。

    参数:
    - app (FastAPI): 应用实例。

    返回:
    - list[str]: 形如 ``"GET /common/health/"`` 的条目（不含 ``HEAD``/``OPTIONS``）。
    """
    items = {
        f"{method} {path}" for method, path in iter_endpoints(app) if method not in EXCLUDED_METHODS
    }
    return sorted(items)


def find_missing(baseline: list[str], current: list[str]) -> list[str]:
    """返回基线中存在、而当前缺失的条目（纯函数，供直接断言）。

    参数:
    - baseline (list[str]): 基线路由条目。
    - current (list[str]): 当前路由条目。

    返回:
    - list[str]: 排序后的缺失条目；无缺失时为空列表。
    """
    return sorted(set(baseline) - set(current))


def assert_snapshot_sane(routes: list[str]) -> None:
    """绝对下限守卫：拒绝写出整体退化的无效基线。

    交叉校验 ``openapi ⊆ collected`` 是单向差集：若注册管线整体退化（例如插件加载器
    一个容器都没挂上），两侧会同时收缩、差集为空，脚本反而会愉快地写出 count=4 的
    弱基线。本函数提供不依赖 ``app.openapi()`` 的绝对下限。

    参数:
    - routes (list[str]): 待写盘的路由条目列表。

    抛出:
    - AssertionError: 条目数低于 ``MIN_ROUTE_COUNT``，或某个必需模块前缀一条路由都没有。
    """
    if len(routes) < MIN_ROUTE_COUNT:
        raise AssertionError(
            f"路由基线异常：仅采集到 {len(routes)} 条，低于绝对下限 {MIN_ROUTE_COUNT}，"
            "疑似路由注册管线整体退化，拒绝写出无效基线"
        )
    paths = [entry.split(" ", 1)[-1] for entry in routes]
    absent = [
        prefix
        for prefix in REQUIRED_MODULE_PREFIXES
        if not any(path.startswith(prefix) for path in paths)
    ]
    if absent:
        raise AssertionError(f"路由基线缺少以下模块前缀的任何路由：{absent}")
