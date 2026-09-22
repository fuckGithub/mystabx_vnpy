"""最小可运行集测试（验收 A9；设计 D1 与 §6 风险表）。

不变量：只安装 ``module_system`` + ``module_common``（设计 §8 定义的「基础插件」）时，
应用必须仍能成功构建、只对外提供最小集的路由，且内核（认证、健康检查等）不受影响。

**「只安装最小集」需要模拟两处缝，缺一不可：**

1. ``loader.discover_plugins`` —— 内核唯一的插件发现入口，决定注册表、模型导入、种子与
   槽位。此处按任务简报过滤**真实发现结果**（保留真实 ``PluginDir``），不伪造路径，因此
   清单解析、模型导入路径与种子目录都还是磁盘上那一份。
2. ``app.plugin.__path__`` —— **路由并不走上面的发现器**：``app/core/discover.py`` 的
   目录扫描（``module_*/**/controller.py``）自行解析 ``app.plugin`` 包位置。把包路径临时
   指向「只含最小集软链的根」，才是对「其它插件目录不存在」的忠实模拟；只改发现器时扫描
   仍会把全部插件路由挂上（实测仍是基线 223 条，见任务报告 §4 的反证）。

两处补丁由 ``monkeypatch`` 在每个用例结束后还原，套件其余部分不受影响。

全部为同步测试：不进入 lifespan、不使用 ``test_client``（该 fixture 在本仓库必然报错）。
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI

import app.plugin as plugin_package
from app.core.ap_scheduler import SchedulerUtil
from app.core.plugin import loader
from app.core.plugin.events import event_bus
from app.core.plugin.runtime import PluginRuntime, get_runtime
from app.core.plugin.slots import (
    SLOT_AUTH_DATA_SCOPE_MODELS,
    SLOT_AUTH_USER_RESOLVER,
    SLOT_CONFIG_PARAMS_PROVIDER,
    SLOT_LOG_OPERATION_SINK,
    SLOT_SCHEDULER_JOB_LOG_SINK,
    clear_slots,
    get,
)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from route_walker import collect_routes, iter_endpoints  # noqa: E402

BASELINE = Path(__file__).parent / "fixtures" / "routes_baseline.json"
"""改造前的全量路由基线（全插件安装时的对外契约，共 223 条）。"""

MIN_SET: frozenset[str] = frozenset({"system", "common"})
"""最小可运行集（设计 §8：``module_system`` + ``module_common``）。"""

MIN_SET_ORDER: tuple[str, ...] = ("system", "common")
"""最小集的加载顺序：``common`` 的 ``plugin.toml`` 声明 ``depends = ["system"]``，故排序后 ``system`` 在前。"""

OTHER_PLUGIN_PREFIXES: tuple[str, ...] = (
    "/ai",
    "/task",
    "/example",
    "/generator",
    "/monitor",
    "/application",
)
"""非最小集插件贡献的路由前缀；最小集下这些前缀必须贡献 0 条路由。"""

KERNEL_ROUTE_ROOTS: frozenset[str] = frozenset({"docs", "ljdoc", "redoc", "openapi.json"})
"""内核自带（非插件）的路由根：文档页与 OpenAPI 描述文件。"""

MIN_SET_ENDPOINTS: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/system/auth/login"),
    ("POST", "/system/auth/token/refresh"),
    ("GET", "/common/health/"),
    ("GET", "/common/health/ready/"),
    ("POST", "/common/file/upload"),
    ("POST", "/common/file/download"),
})
"""最小集必须提供的代表端点：认证入口（system）+ 健康检查与文件（common）。

取具体的「方法 + 路径」而非模糊前缀匹配，避免 ``/system`` 只剩一条任意路由也能通过。
"""


@dataclass(frozen=True)
class MinimalPluginRoot:
    """最小集插件根（软链）与真实插件根。"""

    real_root: Path
    """真实插件根（``admin/app/plugin``），注册表里的 ``PluginDir.path`` 应指向这里。"""

    minimal_root: Path
    """临时根：只含最小集插件的符号链接，模拟「其它插件目录不存在」。"""


@pytest.fixture
def min_set_plugin_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MinimalPluginRoot:
    """把插件可见范围收缩为最小集（等价于其它插件未安装）。

    参数:
    - tmp_path (Path): pytest 临时目录。
    - monkeypatch (pytest.MonkeyPatch): pytest 补丁工具（用例结束自动还原）。

    返回:
    - MinimalPluginRoot: 真实插件根与临时最小集根。
    """
    real_root = loader.plugin_root_dir()
    discovered = loader.discover_plugins(real_root)
    names = {p.name for p in discovered}
    # 自检：过滤必须真的过滤掉东西，否则本文件的「排除」断言会静默形同虚设
    assert MIN_SET < names, (
        f"仓库里没有超出最小集的插件（发现到 {sorted(names)}），"
        "本文件的排除断言无法证伪，请检查插件目录布局"
    )

    minimal_root = tmp_path / "plugin"
    minimal_root.mkdir()
    for name in sorted(MIN_SET):
        (minimal_root / f"module_{name}").symlink_to(
            real_root / f"module_{name}", target_is_directory=True
        )

    real_discover = loader.discover_plugins
    monkeypatch.setattr(
        loader,
        "discover_plugins",
        lambda root=None: [p for p in real_discover(real_root) if p.name in MIN_SET],
    )
    # 目录扫描自行解析 app.plugin 包位置，故必须同时收缩包路径（见模块 docstring）
    monkeypatch.setattr(plugin_package, "__path__", [str(minimal_root)])
    return MinimalPluginRoot(real_root=real_root, minimal_root=minimal_root)


@pytest.fixture
def min_set_app(min_set_plugin_root: MinimalPluginRoot) -> FastAPI:
    """在最小集下构建应用。

    ``create_app()`` 抛异常即 fixture 报错，因此「应用可成功构建」不需要额外断言填充。

    参数:
    - min_set_plugin_root (MinimalPluginRoot): 已收缩的插件根。

    返回:
    - FastAPI: 应用实例（未进入 lifespan）。
    """
    from main import create_app

    return create_app()


def test_min_set_app_serves_minimal_routes(min_set_app: FastAPI) -> None:
    """最小集的两个插件都必须真的把自己的路由挂上来。"""
    endpoints = set(iter_endpoints(min_set_app))
    missing = sorted(MIN_SET_ENDPOINTS - endpoints)
    assert not missing, f"最小集端点缺失（插件路由未挂载）: {missing}"


def test_min_set_app_excludes_other_plugin_routes(
    min_set_app: FastAPI, min_set_plugin_root: MinimalPluginRoot
) -> None:
    """非最小集插件必须贡献 0 条路由。"""
    # 前提校验：路由来源（``app/core/discover.py`` 的目录扫描）此刻真的只看得见两个插件目录，
    # 否则下面的「零路由」断言可能只是因为扫描压根没跑起来
    assert {p.name for p in min_set_plugin_root.minimal_root.iterdir()} == {
        f"module_{name}" for name in MIN_SET
    }

    endpoints = iter_endpoints(min_set_app)

    leaked = sorted({
        (method, path)
        for method, path in endpoints
        if any(path == prefix or path.startswith(f"{prefix}/") for prefix in OTHER_PLUGIN_PREFIXES)
    })
    assert not leaked, f"最小集下不应出现其它插件的路由: {leaked}"

    # 路由根集合必须恰好是「最小集 + 内核文档」，任何多余根都是漏挂/硬编码路径
    roots = {path.split("/")[1] for _, path in endpoints}
    assert roots == MIN_SET | KERNEL_ROUTE_ROOTS, (
        f"最小集下的路由根异常: 多出 {sorted(roots - (MIN_SET | KERNEL_ROUTE_ROOTS))}，"
        f"缺少 {sorted((MIN_SET | KERNEL_ROUTE_ROOTS) - roots)}"
    )

    # 粗粒度规模护栏（真正的区分度在上面的前缀/路由根断言）：
    # 路由面必须比全插件基线小，防止"路由没被过滤但恰好没有越界前缀"的退化
    baseline_count = json.loads(BASELINE.read_text(encoding="utf-8"))["count"]
    assert len(collect_routes(min_set_app)) < baseline_count, (
        f"最小集路由数未少于全插件基线（{baseline_count}），过滤未生效"
    )


def test_min_set_registry_contains_only_min_set(
    min_set_app: FastAPI, min_set_plugin_root: MinimalPluginRoot
) -> None:
    """运行时注册表只含最小集，且用的是真实插件目录。"""
    runtime = get_runtime(min_set_app)
    assert runtime is not None, (
        "create_app() 未把插件运行时挂到 app.state（register_routers 装配缺失）"
    )

    entries = runtime.registry.entries
    assert {entry.plugin_dir.name for entry in entries} == MIN_SET
    assert [entry.plugin_dir.name for entry in entries] == list(MIN_SET_ORDER), (
        "最小集也必须按依赖顺序加载（system 先于依赖它的 common）"
    )
    assert {entry.plugin_dir.path for entry in entries} == {
        min_set_plugin_root.real_root / f"module_{name}" for name in MIN_SET
    }, "注册表应持有真实 PluginDir（模型路径/清单/种子目录不得来自伪造路径）"
    assert all(entry.instance is not None for entry in entries), (
        "最小集插件应全部具备可用入口实例（plugin.py 必须绑定 PLUGIN）"
    )


def test_min_set_start_provides_system_slots_and_degrades_scheduler_slot(
    min_set_app: FastAPI,
) -> None:
    """最小集驱动的 ``start()`` 不抛异常：system 提供槽位，scheduler 槽位按预期缺失。

    依赖 ``min_set_app``：应用装配阶段已把插件模型导入 ``MappedBase.metadata``，
    故 ``create_tables()`` 能真实建表（与 lifespan 中「内核先建表、再启动插件」同序）；
    最小集没有 ``module_task``（不提供 scheduler 槽位），但种子写入仍需表结构，
    先建表才是真实启动路径。

    参数:
    - min_set_app (FastAPI): 最小集应用（也是模型已注册的保证）。

    返回:
    - None
    """
    from app.core.database import create_tables

    clear_slots()
    try:
        runtime = PluginRuntime()
        runtime.discover_and_setup()
        assert [entry.plugin_dir.name for entry in runtime.registry.entries] == list(MIN_SET_ORDER)

        async def drive() -> None:
            """按 lifespan 的顺序建表并启动插件运行时。"""
            await create_tables()
            await runtime.start()

        # 槽位 scheduler.job_log_sink 的提供者（module_task）不在最小集内：
        # 该降级链路必须只记 WARNING，不得把异常抛穿启动流程（设计 D1）。
        asyncio.run(drive())

        assert [entry.plugin_dir.name for entry in runtime.started_entries] == list(MIN_SET_ORDER)

        for slot in (
            SLOT_LOG_OPERATION_SINK,
            SLOT_CONFIG_PARAMS_PROVIDER,
            SLOT_AUTH_USER_RESOLVER,
            SLOT_AUTH_DATA_SCOPE_MODELS,
        ):
            assert get(slot) is not None, f"system 插件 start() 未提供槽位 {slot}"
        assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is None, (
            "scheduler.job_log_sink 应由 module_task 提供，最小集下必须保持缺失"
        )
    finally:
        # 进程全局态清理：槽位、事件总线、调度器任务
        SchedulerUtil.clear_jobs()
        event_bus.clear()
        clear_slots()
