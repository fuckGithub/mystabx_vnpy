"""导出当前应用的路由清单（方法 + 路径）为 JSON 快照。

用法：
    cd backend && .venv/bin/python scripts/dump_routes.py

说明：
    采集逻辑统一由 ``scripts/route_walker.py`` 提供（与 ``tests/test_route_snapshot.py``
    共用同一份语义，避免生成侧与校验侧静默分叉）。FastAPI 0.141 起 ``include_router``
    在 ``app.routes`` 中留下的是 ``_IncludedRouter`` 包装节点而非 ``APIRoute``，直接按
    类型过滤会漏掉全部业务路由；遍历器递归展开路由树，覆盖 ``APIRoute``、starlette
    ``Route``（如 ``/openapi.json``）、``WebSocketRoute``（如 ``/ai/chat/ws``）与包装节点。

    写盘前有两道防线：

    1. ``assert_snapshot_sane`` 绝对下限守卫（条目数 + 8 个模块前缀）——第一防线；
    2. ``app.openapi()["paths"]`` 交叉校验——第二防线（注意它只遍历 ``APIRoute``，
       对 ``Route``/``WebSocketRoute`` 天然不可见，故不能单独依赖）。

    任一道不通过即抛错，拒绝写出无效基线。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from route_walker import assert_snapshot_sane, collect_routes

from main import create_app

OUTPUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "routes_baseline.json"

HTTP_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "DELETE", "PATCH"})
"""用于交叉校验的 HTTP 方法白名单。"""


def _openapi_operations(app: FastAPI) -> set[str]:
    """从 OpenAPI 文档提取「方法 + 路径」集合，用于交叉校验枚举完整性。

    参数:
    - app (FastAPI): 应用实例。

    返回:
    - set[str]: 形如 ``"GET /common/health/"`` 的集合（不含隐藏路由）。
    """
    return {
        f"{method.upper()} {path}"
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.upper() in HTTP_METHODS
    }


def main() -> None:
    """生成快照文件。"""
    app = create_app()
    routes = collect_routes(app)
    assert_snapshot_sane(routes)
    missing = sorted(_openapi_operations(app) - set(routes))
    if missing:
        raise RuntimeError(
            f"路由枚举不完整：OpenAPI 中 {len(missing)} 条未被采集，例如 {missing[:5]}"
        )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({"count": len(routes), "routes": routes}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✅ 已写入 {OUTPUT}（{len(routes)} 条路由）")


if __name__ == "__main__":
    main()
