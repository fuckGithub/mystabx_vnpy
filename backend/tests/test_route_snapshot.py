"""路由表零回归测试（验收 A1）。

比对当前应用的全部 HTTP 路由与改造前基线快照，确保插件化改造不改变任何对外路径。

说明：采集与比较逻辑统一来自 ``scripts/route_walker.py``（生成侧 ``scripts/dump_routes.py``
import 同一份），本文件不再自行持有 ``_iter_endpoints``/``_current_routes``，避免两侧语义
静默分叉导致快照含义漂移。

应用实例直接由 ``create_app()`` 构建，不进入 lifespan，因此不依赖数据库/Redis
（conftest 的 ``test_client`` 会进入 lifespan，在无 Redis 的环境下会直接报错）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from route_walker import (  # noqa: E402
    EXCLUDED_METHODS,
    assert_snapshot_sane,
    collect_routes,
    find_missing,
    iter_endpoints,
)

BASELINE = Path(__file__).parent / "fixtures" / "routes_baseline.json"


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """构建应用实例（不进入 lifespan，故无需数据库/Redis）。

    返回:
    - FastAPI: 应用实例。
    """
    from main import create_app

    return create_app()


@pytest.fixture(scope="module")
def baseline() -> dict:
    """加载基线快照并自证其有效性。

    这里必须做「下限守卫 + 自洽校验」，否则守卫形同虚设：若有人手工把 ``routes`` 改小
    （或只改 ``count`` 造成与 ``len(routes)`` 漂移），``baseline ⊆ current`` 会平凡成立，
    门禁全绿却毫无约束力。

    返回:
    - dict: 含 ``count`` 与 ``routes`` 的字典。
    """
    assert BASELINE.is_file(), f"缺少基线快照，请先运行 scripts/dump_routes.py：{BASELINE}"
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert data["count"] == len(data["routes"]), (
        f"基线快照自相矛盾：count={data['count']} 与 routes 实际长度 "
        f"{len(data['routes'])} 不一致，快照已被手工篡改或写入中断"
    )
    assert_snapshot_sane(data["routes"])
    return data


def test_no_route_regression(app: FastAPI, baseline: dict) -> None:
    """基线中的每条路由在改造后依然存在。"""
    missing = find_missing(baseline["routes"], collect_routes(app))
    assert not missing, f"以下路由在改造后消失：{missing}"


def test_no_duplicate_routes(app: FastAPI) -> None:
    """同一「方法 + 路径」不得重复注册（防止目录扫描与显式聚合双挂载）。"""
    seen: dict[str, int] = {}
    for method, path in iter_endpoints(app):
        if method in EXCLUDED_METHODS:
            continue
        key = f"{method} {path}"
        seen[key] = seen.get(key, 0) + 1
    duplicated = {k: v for k, v in seen.items() if v > 1}
    assert not duplicated, f"发现重复路由：{duplicated}"


def test_find_missing_detects_removed_route() -> None:
    """meta-test：路由消失时 ``find_missing`` 必须报出来（守卫自证，非空断言）。"""
    baseline = ["GET /common/health/", "GET /system/x"]
    current = ["GET /common/health/"]
    assert find_missing(baseline, current) == ["GET /system/x"]


def test_find_missing_returns_empty_when_equal() -> None:
    """meta-test：基线等于当前时不得报缺失（防止守卫恒真导致假绿）。"""
    routes = ["GET /common/health/", "WEBSOCKET /ai/chat/ws"]
    assert find_missing(routes, routes) == []


def test_real_gate_red_path(app: FastAPI, baseline: dict) -> None:
    """常驻反证：向真实基线注入幽灵路由，门禁必须精确报出它。

    前面的 meta-test 用的是自造的极小列表，无法证明「真实快照 + 真实应用」这条路径是
    通的。本用例把一次性注入实验固化为 CI 断言：真出问题时门禁必然变红，且只红在注入项上。
    """
    buried = [*baseline["routes"], "GET /__phantom__"]
    assert find_missing(buried, collect_routes(app)) == ["GET /__phantom__"]
