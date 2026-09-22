"""插件注册表与运行时编排测试。

假插件包建在 tmp_path 下并通过 ``syspath_prepend`` 变为可导入包，
避免污染 app/plugin。

每个用例的假插件包名唯一（``fakeplugins_<uuid8>``）：``syspath_prepend`` 只改搜索
路径，同名包会命中 ``sys.modules`` 中首次导入的模块，使后续用例实际执行的是首个
tmp_path 的 ``plugin.py``。唯一包名让每个用例的假插件真正独立。

路由断言经 ``scripts/route_walker.py``（本仓唯一的路由遍历语义来源）：
FastAPI 0.141 起 ``include_router`` 不再把子路由摊平进 ``app.routes``，
而是放入懒挂载包装节点，故不能用 ``route.path`` 直接断言。
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI

from app.core.plugin.registry import PluginRegistry
from app.core.plugin.runtime import PluginRuntime
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, clear_slots, get
from app.core.seed import resolve_model

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from route_walker import iter_endpoints  # noqa: E402


@dataclass(frozen=True)
class FakePlugins:
    """单个用例专属的假插件包（包名唯一，避免 ``sys.modules`` 复用）。"""

    root: Path
    """假插件根目录（即包目录，其下放 ``module_xxx``）。"""

    package: str
    """假插件包名，如 ``fakeplugins_1a2b3c4d``。"""


def _make_runtime(fake: FakePlugins) -> PluginRuntime:
    """构造指向该用例专属假插件包的运行时。

    参数:
    - fake (FakePlugins): 用例专属假插件包。

    返回:
    - PluginRuntime: 尚未执行发现阶段的运行时实例。
    """
    return PluginRuntime(root=fake.root, package=fake.package)


PLUGIN_PY = '''
from fastapi import APIRouter

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide

DEMO_ROUTER = APIRouter(prefix="/demo")


@DEMO_ROUTER.get("")
async def demo_ping() -> dict:
    """测试端点（使路由可被挂载观测）。"""
    return {}


class Plugin(PluginBase):
    """测试插件：注册路由、事件与钩子。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_router(DEMO_ROUTER)
        ctx.on("demo.event", self.on_event)
        ctx.add_startup_hook(self.on_start)
        ctx.add_shutdown_hook(self.on_stop)

    async def on_event(self, payload: dict) -> None:
        provide("demo.event.seen", payload)

    async def on_start(self) -> None:
        provide("demo.started", True)

    async def on_stop(self) -> None:
        provide("demo.started", False)


PLUGIN = Plugin()
'''

EMPTY_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext


class Plugin(PluginBase):
    """空插件。"""

    def setup(self, ctx: PluginContext) -> None:
        pass


PLUGIN = Plugin()
'''

PER_ROUTER_DEPS_PLUGIN_PY = '''
from fastapi import APIRouter, Depends

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext

DEFAULT_ROUTER = APIRouter(prefix="/default-deps")


@DEFAULT_ROUTER.get("")
async def default_ping() -> dict:
    """未声明专属依赖的路由（应拿到运行时默认依赖）。"""
    return {}


CUSTOM_ROUTER = APIRouter(prefix="/custom-deps")


@CUSTOM_ROUTER.get("")
async def custom_ping() -> dict:
    """声明了专属依赖的路由（应拿到专属依赖，而非运行时默认）。"""
    return {}


def custom_dep() -> None:
    """本插件为 CUSTOM_ROUTER 声明的专属依赖。"""


class Plugin(PluginBase):
    """同时声明「有专属依赖」与「无专属依赖」两条路由的插件。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_router(DEFAULT_ROUTER)
        ctx.add_router(CUSTOM_ROUTER, dependencies=[Depends(custom_dep)])


PLUGIN = Plugin()
'''

SETUP_RAISES_PLUGIN_PY = '''
from fastapi import APIRouter

from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext

GHOST_ROUTER = APIRouter(prefix="/ghost")


@GHOST_ROUTER.get("")
async def ghost_ping() -> dict:
    """setup 抛异常前已声明的端点（不应被挂载）。"""
    return {}


class Plugin(PluginBase):
    """setup 抛异常的插件：先注册一半再抛。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_router(GHOST_ROUTER)
        ctx.add_startup_hook(self.on_start)
        raise RuntimeError("setup-boom")

    async def on_start(self) -> None:
        """降级插件不应执行启动钩子。"""
        raise AssertionError("降级插件不应执行启动钩子")


PLUGIN = Plugin()
'''

START_RAISES_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide


class Plugin(PluginBase):
    """start() 抛异常的插件：启动钩子、stop 与关闭钩子都留可观测标记。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_startup_hook(self.on_start)
        ctx.add_shutdown_hook(self.on_shutdown)

    async def on_start(self) -> None:
        provide("broken.startup_hook", True)

    async def start(self) -> None:
        raise RuntimeError("start-boom")

    async def on_shutdown(self) -> None:
        provide("broken.shutdown_hook", True)

    async def stop(self) -> None:
        provide("broken.stop_called", True)


PLUGIN = Plugin()
'''

README_TEXT = "## 模块定位\n\n测试。\n\n## 入口\n\n无。\n\n## 依赖\n\n无。\n\n## 删除影响\n\n无。\n"

BROKEN_SEED_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide


class Plugin(PluginBase):
    """声明了必失败种子的插件：自然键字段不是模型真实列。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_models("model")
        # 自然键必须出现在行里才会走到 getattr(model, key)；该键不是模型列
        # → SeedApplier._find_existing_id 抛 AttributeError（种子阶段的必然失败输入）。
        ctx.add_seed(
            "runtime_seed_probe",
            [{"probe_code": "P1", "no_such_column": "x"}],
            natural_key="no_such_column",
        )

    async def start(self) -> None:
        provide("broken_seed.started", True)

    async def stop(self) -> None:
        provide("broken_seed.stop_called", True)


PLUGIN = Plugin()
'''

PROBE_MODEL_PY = '''
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class RuntimeSeedProbeModel(MappedBase):
    """测试探针表：模拟插件自带模型，让种子声明能解析到真实模型。"""

    __tablename__ = "runtime_seed_probe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    probe_code: Mapped[str] = mapped_column(String(32))
'''

HOOK_ONLY_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide


class Plugin(PluginBase):
    """只声明启动钩子的插件（其启动不应受其它插件的种子失败影响）。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_startup_hook(self.on_start)

    async def on_start(self) -> None:
        provide("hook_only.started", True)


PLUGIN = Plugin()
'''


SCHEDULER_BOOM_SINK_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, provide


class _BoomSink:
    """register 必抛异常的槽位实现（槽位是插件提供的代码，故必须被逐条隔离）。"""

    async def register(self, job: dict) -> None:
        raise RuntimeError("sink-boom")


class Plugin(PluginBase):
    """声明一条任务、并在 ``start()`` 里提供"抛异常"任务接收器的插件。

    槽位与 ``module_task`` 一样由 ``start()`` 注入（注册任务排在全部插件启动之后），
    因此本用例同时覆盖「注册后置」与「单条 register 失败逐条隔离」。
    """

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_startup_hook(self.on_start)
        ctx.add_scheduler_job({"job_id": "boom-job", "job_name": "boom", "code": "boom"})

    async def on_start(self) -> None:
        provide("boom_sink.started", True)

    async def start(self) -> None:
        provide(SLOT_SCHEDULER_JOB_LOG_SINK, _BoomSink())


PLUGIN = Plugin()
'''

JOB_ONLY_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide


class Plugin(PluginBase):
    """只声明定时任务的正常插件（对照组：证明 sink 确实收到任务）。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_scheduler_job({"job_id": "keep-job", "job_name": "keep", "code": "keep"})
        ctx.add_startup_hook(self.on_start)

    async def on_start(self) -> None:
        provide("job_only.started", True)


PLUGIN = Plugin()
'''

BROKEN_SEED_JOB_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import provide


class Plugin(PluginBase):
    """种子必失败且声明了定时任务的插件：其任务不得被注册。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_models("model")
        ctx.add_seed(
            "runtime_seed_probe_job",
            [{"probe_code": "J1", "no_such_column": "x"}],
            natural_key="no_such_column",
        )
        ctx.add_scheduler_job({"job_id": "drop-job", "job_name": "drop", "code": "drop"})

    async def start(self) -> None:
        provide("drop_job.started", True)


PLUGIN = Plugin()
'''

PROBE_MODEL_JOB_PY = '''
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import MappedBase


class RuntimeSeedProbeJobModel(MappedBase):
    """测试探针表（表名与上一个探针不同，避免同进程重复定义表）。"""

    __tablename__ = "runtime_seed_probe_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    probe_code: Mapped[str] = mapped_column(String(32))
'''

RECORDING_SINK_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, provide


class _RecordingJobSink:
    """记录收到的任务 id 的槽位实现（用于断言"哪些任务被注册"）。"""

    def __init__(self) -> None:
        """初始化空记录。"""
        self.job_ids: list[str] = []

    async def register(self, job: dict) -> None:
        """记录任务 id。

        参数:
        - job (dict): 任务定义。

        返回:
        - None
        """
        self.job_ids.append(str(job.get("job_id")))


SINK = _RecordingJobSink()


class Plugin(PluginBase):
    """只提供记录型槽位的插件（与 module_task 一致：在 start() 里注入）。"""

    def setup(self, ctx: PluginContext) -> None:
        """无注册项。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """

    async def start(self) -> None:
        """注入记录型槽位。

        返回:
        - None
        """
        provide(SLOT_SCHEDULER_JOB_LOG_SINK, SINK)


PLUGIN = Plugin()
'''

ORDERING_GUARD_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, provide


class _RecordingJobSink:
    """记录收到的任务 id（槽位按真实机制由 start() 提供）。"""

    def __init__(self) -> None:
        """初始化空记录。"""
        self.job_ids: list[str] = []

    async def register(self, job: dict) -> None:
        """记录任务 id。

        参数:
        - job (dict): 任务定义。

        返回:
        - None
        """
        self.job_ids.append(str(job.get("job_id")))


SINK = _RecordingJobSink()


class Plugin(PluginBase):
    """setup() 声明定时任务、start() 才提供接收槽位的插件（真实生产形态）。"""

    def setup(self, ctx: PluginContext) -> None:
        """声明一条定时任务（此刻槽位尚不存在）。

        参数:
        - ctx (PluginContext): 插件上下文。

        返回:
        - None
        """
        ctx.add_scheduler_job({
            "job_id": "ordered-job",
            "job_name": "ordered",
            "code": "ordered",
            "cron": "0 0 3 * * ?",
        })

    async def start(self) -> None:
        """注入记录型槽位。

        返回:
        - None
        """
        provide(SLOT_SCHEDULER_JOB_LOG_SINK, SINK)


PLUGIN = Plugin()
'''

START_RAISES_JOB_PLUGIN_PY = '''
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext


class Plugin(PluginBase):
    """声明了定时任务但 ``start()`` 必失败的插件（未进入运行态，任务不得注册）。"""

    def setup(self, ctx: PluginContext) -> None:
        ctx.add_scheduler_job({
            "job_id": "start-boom-job",
            "job_name": "start-boom",
            "code": "start-boom",
        })

    async def start(self) -> None:
        raise RuntimeError("start-boom")


PLUGIN = Plugin()
'''


def _noop_dep() -> None:
    """测试用空依赖。"""


def _include_deps(app: FastAPI, router: object) -> list[Any]:
    """取出某个 router 被 include 时实际生效的依赖列表。

    FastAPI 0.141 把 ``include_router`` 变成懒挂载包装节点：依赖挂在
    ``include_context.dependencies``，被包含的 router 在 ``original_router``
    （该节点没有 ``.router``/``.path`` 属性，故不能按普通路由遍历）。

    参数:
    - app (FastAPI): 应用实例。
    - router (object): 被包含的 router 实例（按身份匹配）。

    返回:
    - list[Any]: include 时生效的依赖列表。
    """
    context = next(
        getattr(r, "include_context")
        for r in app.routes
        if getattr(r, "include_context", None) is not None
        and getattr(r, "original_router", None) is router
    )
    return list(context.dependencies)


def _make_plugin_dir(root: Path, name: str, body: str) -> Path:
    """在假插件包内创建一个插件目录。

    参数:
    - root (Path): 假插件包目录（即 ``fakeplugins``）。
    - name (str): 插件名，如 ``demo``。
    - body (str): ``plugin.py`` 内容。

    返回:
    - Path: 插件目录。
    """
    d = root / f"module_{name}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").write_text("", encoding="utf-8")
    (d / "plugin.toml").write_text(
        f'name = "{name}"\ntitle = "{name}"\nversion = "1.0.0"\n', encoding="utf-8"
    )
    (d / "README.md").write_text(README_TEXT, encoding="utf-8")
    (d / "plugin.py").write_text(body, encoding="utf-8")
    return d


@pytest.fixture
def fake_plugins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakePlugins:
    """构造可导入的、本用例专属的假插件包。

    参数:
    - tmp_path (Path): pytest 临时目录。
    - monkeypatch (pytest.MonkeyPatch): 补丁工具。

    返回:
    - FakePlugins: 假插件包目录与唯一包名。
    """
    package = f"fakeplugins_{uuid4().hex[:8]}"
    root = tmp_path / package
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return FakePlugins(root=root, package=package)


def test_empty_registry_is_safe() -> None:
    """没有插件时注册表各项为空，不抛异常。"""
    registry = PluginRegistry()
    assert registry.routers() == []
    assert registry.seeds() == []
    assert registry.manifests() == []


def test_discover_and_setup_collects_router(fake_plugins: FakePlugins) -> None:
    """setup 声明的路由被收集。"""
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    assert [e.plugin_dir.name for e in runtime.registry.entries] == ["demo"]
    assert len(runtime.registry.load_main()) == 1


def test_mount_registers_plugin_router(fake_plugins: FakePlugins) -> None:
    """mount 把插件声明的路由挂到应用上。"""
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    app = FastAPI()
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    runtime.mount(app)
    assert ("GET", "/demo") in iter_endpoints(app)


def test_mount_applies_uniform_dependencies(fake_plugins: FakePlugins) -> None:
    """mount 把内核统一依赖挂到插件路由上（限流不能丢）。"""
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    app = FastAPI()
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    runtime.mount(app, dependencies=[Depends(_noop_dep)])
    included = next(r for r in app.routes if getattr(r, "include_context", None) is not None)
    assert getattr(included, "include_context").dependencies, "插件路由必须带上内核统一依赖"


def test_mount_uses_per_router_dependencies(fake_plugins: FakePlugins) -> None:
    """逐路由依赖：声明了 dependencies 的路由用专属依赖，未声明的用运行时默认。

    两条路由同时挂载，断言互不污染 —— 这正是 ``module_ai`` 的 WS 路由（需要
    ``WebSocketRateLimiter``）与其它路由（用运行时 HTTP ``RateLimiter``）的共存形态。
    """
    _make_plugin_dir(fake_plugins.root, "demo", PER_ROUTER_DEPS_PLUGIN_PY)
    app = FastAPI()
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    module = importlib.import_module(f"{fake_plugins.package}.module_demo.plugin")

    runtime.mount(app, dependencies=[Depends(_noop_dep)])

    default_deps = [d.dependency for d in _include_deps(app, module.DEFAULT_ROUTER)]
    custom_deps = [d.dependency for d in _include_deps(app, module.CUSTOM_ROUTER)]
    assert default_deps == [_noop_dep], "未声明专属依赖的路由必须用运行时默认依赖"
    assert custom_deps == [module.custom_dep], "声明了专属依赖的路由不得被统一依赖覆盖"

    mounted = set(iter_endpoints(app))
    assert {("GET", "/default-deps"), ("GET", "/custom-deps")} <= mounted, (
        "两条路由都必须真的挂上（否则依赖断言是空转）"
    )


def test_load_main_is_repeatable(fake_plugins: FakePlugins) -> None:
    """load_main 幂等：连续两次调用返回相同且非空的路由列表。

    去重语义若跨调用累积（实例级集合），第二次调用会返回 ``[]``；
    本用例断言两次结果一致且非空。
    """
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    runtime = _make_runtime(fake_plugins).discover_and_setup()

    first = runtime.registry.load_main()
    second = runtime.registry.load_main()

    assert first, "首次调用不应为空"
    assert len(first) == len(second), "第二次调用不应比第一次少"
    assert first == second


def test_probe_before_mount_keeps_routes(fake_plugins: FakePlugins) -> None:
    """先探一次 load_main() 再 mount，插件路由仍完整挂载（mount 不受预探影响）。"""
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    app = FastAPI()
    runtime = _make_runtime(fake_plugins).discover_and_setup()

    assert len(runtime.registry.load_main()) == 1, "预探应看到插件路由"

    runtime.mount(app)

    assert ("GET", "/demo") in iter_endpoints(app), "预探后 mount 仍须挂上插件路由"


def test_start_runs_hooks_and_subscribes_events(fake_plugins: FakePlugins) -> None:
    """start 执行启动钩子并订阅事件；stop 执行关闭钩子。"""
    _make_plugin_dir(fake_plugins.root, "demo", PLUGIN_PY)
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    clear_slots()
    asyncio.run(runtime.start())
    assert get("demo.started") is True

    from app.core.plugin.events import event_bus

    asyncio.run(event_bus.publish("demo.event", {"id": 9}))
    assert get("demo.event.seen") == {"id": 9}

    asyncio.run(runtime.stop())
    assert get("demo.started") is False
    clear_slots()


def test_plugin_without_entry_falls_back(fake_plugins: FakePlugins) -> None:
    """无 plugin.py 的插件仍被登记（回退目录扫描），上下文为空。"""
    d = fake_plugins.root / "module_legacy"
    d.mkdir()
    (d / "__init__.py").write_text("", encoding="utf-8")
    (d / "README.md").write_text(README_TEXT, encoding="utf-8")
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    entry = runtime.registry.entries[0]
    assert entry.instance is None
    assert entry.context.routers == []


def test_discover_and_setup_names_filter(fake_plugins: FakePlugins) -> None:
    """names 参数只加载指定插件（最小集验证用），且执行的是本用例自己的包。"""
    alpha_dir = _make_plugin_dir(fake_plugins.root, "alpha", EMPTY_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "beta", EMPTY_PLUGIN_PY)
    runtime = _make_runtime(fake_plugins).discover_and_setup(names={"alpha"})
    assert [e.plugin_dir.name for e in runtime.registry.entries] == ["alpha"]

    loaded = sys.modules[f"{fake_plugins.package}.module_alpha.plugin"]
    assert Path(str(loaded.__file__)).resolve().parent == alpha_dir.resolve(), (
        "必须执行本用例 tmp_path 下的 plugin.py，而非 sys.modules 缓存的旧模块"
    )


def test_setup_failure_does_not_block_other_plugins(fake_plugins: FakePlugins) -> None:
    """一个插件 setup 抛异常不阻塞其余插件，该插件降级为无实例（回退目录扫描）。"""
    _make_plugin_dir(fake_plugins.root, "broken", SETUP_RAISES_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "healthy", PLUGIN_PY)

    runtime = _make_runtime(fake_plugins).discover_and_setup()  # 不得抛穿

    entries = {e.plugin_dir.name: e for e in runtime.registry.entries}
    assert set(entries) == {"broken", "healthy"}, "异常插件不得把其它插件带下水"
    broken = entries["broken"]
    assert broken.instance is None, "setup 失败的插件应降级为无实例"
    assert broken.context.routers == [], "半途声明的路由不得保留"
    assert broken.context.startup_hooks == [], "半途声明的钩子不得保留"
    assert entries["healthy"].instance is not None, "正常插件仍应装载实例"
    assert len(runtime.registry.load_main()) == 1, "只应挂上健康插件的路由"


def test_start_failure_isolated_to_failing_plugin(fake_plugins: FakePlugins) -> None:
    """一个插件 start 抛异常不影响其它插件，且不被记入已启动集合。"""
    _make_plugin_dir(fake_plugins.root, "broken", START_RAISES_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "healthy", PLUGIN_PY)

    runtime = _make_runtime(fake_plugins).discover_and_setup()
    clear_slots()

    asyncio.run(runtime.start())  # 不得抛穿

    assert get("demo.started") is True, "健康插件的启动钩子必须执行"
    assert [e.plugin_dir.name for e in runtime.started_entries] == ["healthy"]
    clear_slots()


def test_stop_only_touches_started_plugins(fake_plugins: FakePlugins) -> None:
    """stop() 只收尾成功启动的插件，未成功启动者不调用 stop/关闭钩子。"""
    _make_plugin_dir(fake_plugins.root, "broken", START_RAISES_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "healthy", PLUGIN_PY)

    runtime = _make_runtime(fake_plugins).discover_and_setup()
    clear_slots()
    asyncio.run(runtime.start())
    assert get("demo.started") is True

    asyncio.run(runtime.stop())

    assert get("demo.started") is False, "已启动插件的关闭钩子必须执行"
    assert get("broken.stop_called") is None, "未成功启动的插件不得调用 stop()"
    assert get("broken.shutdown_hook") is None, "未成功启动的插件的关闭钩子不得执行"
    clear_slots()


def test_seed_failure_isolated_to_failing_plugin(fake_plugins: FakePlugins) -> None:
    """一个插件的种子写入失败不抛穿，其它插件照常启动，失败者本轮不进入已启动集合。

    坏种子走真实路径（不 mock）：自然键字段不是模型列，故
    ``SeedApplier._find_existing_id`` 的 ``getattr(model, key)`` 抛 ``AttributeError``。
    """
    broken_dir = _make_plugin_dir(fake_plugins.root, "broken", BROKEN_SEED_PLUGIN_PY)
    (broken_dir / "model.py").write_text(PROBE_MODEL_PY, encoding="utf-8")
    _make_plugin_dir(fake_plugins.root, "healthy", HOOK_ONLY_PLUGIN_PY)

    runtime = _make_runtime(fake_plugins).discover_and_setup()
    runtime.mount(FastAPI())  # 经注册表导入插件模型 → 探针表注册进 MappedBase
    clear_slots()

    assert resolve_model("runtime_seed_probe") is not None, (
        "探针模型必须已注册；否则失败原因会是「无模型」而非坏自然键，本用例就成了假绿"
    )

    asyncio.run(runtime.start())  # 坏种子不得抛穿 start()

    assert get("hook_only.started") is True, "另一个插件的启动钩子必须照常执行"
    assert get("broken_seed.started") is None, "种子失败的插件不得进入启动阶段"
    assert [e.plugin_dir.name for e in runtime.started_entries] == ["healthy"]

    asyncio.run(runtime.stop())

    assert get("broken_seed.stop_called") is None, "未成功启动的插件不得被 stop() 收尾"
    clear_slots()


def test_scheduler_sink_failure_does_not_block_start(fake_plugins: FakePlugins) -> None:
    """槽位实现的 ``register`` 抛异常时 ``start()`` 不得抛穿，其它插件照常启动。

    槽位实现由插件提供（任意插件都能 ``provide``），属于外部代码；它抛异常若逃出
    ``start()`` 会让 lifespan 启动失败，故必须与其余阶段同样逐条隔离。
    """
    _make_plugin_dir(fake_plugins.root, "sinkowner", SCHEDULER_BOOM_SINK_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "healthy", HOOK_ONLY_PLUGIN_PY)

    clear_slots()  # 槽位由插件在 start() 期注入，先清空以隔离上一个用例的残留
    runtime = _make_runtime(fake_plugins).discover_and_setup()

    asyncio.run(runtime.start())  # 会抛的 sink 不得抛穿

    assert get("hook_only.started") is True, "正常插件的启动钩子必须执行"
    assert get("boom_sink.started") is True, "提供槽位的插件自身也应照常启动"
    clear_slots()


def test_scheduler_job_reaches_sink_provided_by_start(fake_plugins: FakePlugins) -> None:
    """``C-NEW-1`` 守卫：任务注册必须排在全部 ``Plugin.start()`` 之后。

    槽位 ``scheduler.job_log_sink`` 的唯一提供者是插件的 ``start()``（真实实现见
    ``module_task/plugin.py``），因此「先注册任务、后启动插件」在全新进程里必然取到
    ``None`` 槽位 → 插件声明的任务会被整批跳过且无人察觉。本用例走真实路径
    （``discover_and_setup()`` + ``await runtime.start()``），断言 ``setup()`` 声明的任务
    真的被 ``start()`` 提供的槽位收到。
    """
    _make_plugin_dir(fake_plugins.root, "ordered", ORDERING_GUARD_PLUGIN_PY)

    clear_slots()
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    sink = importlib.import_module(f"{fake_plugins.package}.module_ordered.plugin").SINK

    assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is None, (
        "槽位只应在插件的 start() 里出现；此处非 None 说明用例没复现真实时序"
    )
    assert sink.job_ids == [], "注册发生前记录必须为空"

    asyncio.run(runtime.start())

    assert sink.job_ids == ["ordered-job"], (
        f"start() 提供的槽位必须收到 setup() 声明的任务，实际 {sink.job_ids}"
        "（为空 = 任务注册仍排在插件启动之前）"
    )
    clear_slots()


def test_scheduler_jobs_of_degraded_plugin_are_not_registered(
    fake_plugins: FakePlugins,
) -> None:
    """被判降级的插件（种子写入失败）其声明的定时任务不得注册，正常插件的不受影响。

    「降级＝本轮完全不参与」须在定时任务步骤同样成立，否则等于绕过该语义。
    坏种子走真实路径（自然键字段不是模型列），不 mock；接收槽位由插件在 ``start()`` 里
    提供（与 ``module_task`` 的真实机制一致），不再是测试体里的提前 ``provide``。
    ``start()`` 抛异常的插件同样没有进入运行态，其任务也不得注册（同一条降级规则）。
    """
    broken_dir = _make_plugin_dir(fake_plugins.root, "broken", BROKEN_SEED_JOB_PLUGIN_PY)
    (broken_dir / "model.py").write_text(PROBE_MODEL_JOB_PY, encoding="utf-8")
    _make_plugin_dir(fake_plugins.root, "healthy", JOB_ONLY_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "startboom", START_RAISES_JOB_PLUGIN_PY)
    _make_plugin_dir(fake_plugins.root, "sinkowner", RECORDING_SINK_PLUGIN_PY)

    clear_slots()
    runtime = _make_runtime(fake_plugins).discover_and_setup()
    runtime.mount(FastAPI())  # 经注册表导入插件模型 → 探针表注册进 MappedBase
    sink = importlib.import_module(f"{fake_plugins.package}.module_sinkowner.plugin").SINK

    assert resolve_model("runtime_seed_probe_job") is not None, (
        "探针模型必须已注册；否则失败原因会是「无模型」而非坏自然键，本用例就成了假绿"
    )
    assert get(SLOT_SCHEDULER_JOB_LOG_SINK) is None, "槽位只应由插件的 start() 在启动期注入"

    asyncio.run(runtime.start())

    assert sink.job_ids == ["keep-job"], f"只有正常插件的任务可注册，实际收到 {sink.job_ids}"
    assert get("job_only.started") is True, "正常插件仍应照常启动"
    assert get("drop_job.started") is None, "种子失败的插件不得进入启动阶段"
    assert {e.plugin_dir.name for e in runtime.started_entries} == {"healthy", "sinkowner"}, (
        f"只有启动成功的插件可进入收尾范围，实际 {[e.plugin_dir.name for e in runtime.started_entries]}"
    )
    clear_slots()
