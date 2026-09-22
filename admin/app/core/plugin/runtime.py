"""插件运行时：发现 → setup → mount → start → stop 五阶段编排。"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.core.logger import log
from app.core.plugin import loader
from app.core.plugin.base import PluginBase
from app.core.plugin.context import PluginContext
from app.core.plugin.events import event_bus
from app.core.plugin.loader import DEFAULT_PACKAGE, PluginDir
from app.core.plugin.registry import PluginEntry, PluginRegistry
from app.core.plugin.slots import SLOT_SCHEDULER_JOB_LOG_SINK, get
from app.core.seed import SeedApplier

RUNTIME_STATE_KEY = "plugin_runtime"
"""``app.state`` 中运行时实例的键名。"""

ENTRY_MODULE = "plugin"
"""插件入口模块名（``plugin.py``）。"""

ENTRY_VAR = "PLUGIN"
"""插件入口模块中暴露的实例变量名。"""


class PluginRuntime:
    """按五个阶段装配全部插件。"""

    def __init__(self, root: Path | None = None, package: str = DEFAULT_PACKAGE) -> None:
        """初始化。

        参数:
        - root (Path | None): 插件根目录；``None`` 表示 ``app/plugin``。
        - package (str): 插件根包名，默认 ``loader.DEFAULT_PACKAGE``（测试可传假包名）。
        """
        self.root = root
        self.package = package
        self.registry = PluginRegistry()
        self._plugins: list[PluginDir] = []
        self._started: list[PluginEntry] = []

    @property
    def started_entries(self) -> list[PluginEntry]:
        """已成功启动的插件项（``stop()`` 的收尾范围与启动日志汇总依据）。

        返回:
        - list[PluginEntry]: 已成功启动的插件项，按启动顺序；返回副本。
        """
        return list(self._started)

    def discover_and_setup(self, names: set[str] | None = None) -> PluginRuntime:
        """阶段 1+2：发现插件目录并调用各插件 ``setup(ctx)``。

        无 ``plugin.py`` 或 ``setup()`` 抛异常的插件降级为 ``instance=None``：该插件本轮
        不贡献**任何**注册项（路由/模型/种子/事件/钩子均不生效），但依然登记在注册表中
        （"无 plugin.py 时回退目录扫描并挂载 controller.py" 的设计尚未实现）。单个插件失败
        不阻塞其余插件。

        参数:
        - names (set[str] | None): 只加载这些插件（``None`` 表示全部）。

        返回:
        - PluginRuntime: 自身，便于链式调用。
        """
        discovered = loader.discover_plugins(self.root)
        if names is not None:
            discovered = [p for p in discovered if p.name in names]
        self._plugins = loader.sort_by_dependency(discovered)

        for plugin_dir in self._plugins:
            instance = self._load_instance(plugin_dir)
            context = PluginContext(plugin_name=plugin_dir.name, base_dir=plugin_dir.path)
            if instance is None:
                if plugin_dir.has_entry:
                    log.info(
                        f"  ↳ 插件 {plugin_dir.name} 入口不可用（导入失败或未定义 {ENTRY_VAR}，"
                        "已在上方记录原因）：该插件本轮不贡献任何注册项"
                        "（无路由/模型/种子/事件/钩子）"
                    )
                else:
                    log.info(
                        f"  ↳ 插件 {plugin_dir.name} 无 {ENTRY_MODULE}.py：该插件本轮不贡献任何"
                        f"注册项（无路由/模型/种子/事件/钩子）；缺少 {ENTRY_MODULE}.py 的目录"
                        "不会自动挂载 controller.py"
                    )
            else:
                try:
                    instance.setup(context)
                except Exception as exc:  # 单插件 setup 失败不阻塞启动
                    log.exception(
                        f"❌ 插件 {plugin_dir.name}（{plugin_dir.path}）setup() 失败，"
                        f"已降级为无实例（该插件本轮不贡献任何注册项）— {exc!s}"
                    )
                    instance = None
                    # 丢弃半途收集的注册项：降级语义与"无 plugin.py"完全一致，
                    # 避免只生效一半（路由挂上了但模型/种子/事件/钩子没生效）。
                    context = PluginContext(plugin_name=plugin_dir.name, base_dir=plugin_dir.path)
                else:
                    log.info(f"  ↳ 插件 {plugin_dir.name} 已执行 setup()")
            self.registry.add(
                PluginEntry(plugin_dir=plugin_dir, context=context, instance=instance)
            )

        log.info(f"✅ 插件 setup 完成: {[e.plugin_dir.name for e in self.registry.entries]}")
        return self

    def _load_instance(self, plugin_dir: PluginDir) -> PluginBase | None:
        """导入 ``plugin.py`` 并取出 ``PLUGIN`` 实例。

        参数:
        - plugin_dir (PluginDir): 插件目录。

        返回:
        - PluginBase | None: 插件实例；无入口文件或导入失败时为 ``None``。
        """
        if not plugin_dir.has_entry:
            return None
        module_path = f"{self.package}.{plugin_dir.dir_name}.{ENTRY_MODULE}"
        try:
            module = importlib.import_module(module_path)
        except Exception as exc:  # 单插件导入失败不阻塞启动
            log.exception(f"❌ 导入插件入口失败: {module_path} — {exc!s}")
            return None
        instance = getattr(module, ENTRY_VAR, None)
        if not isinstance(instance, PluginBase):
            log.error(
                f"❌ 插件 {plugin_dir.name} 的 {ENTRY_MODULE}.py 未定义 {ENTRY_VAR}"
                f"（或类型不是 PluginBase），跳过 setup"
            )
            return None
        return instance

    def mount(self, app: FastAPI, dependencies: list[Any] | None = None) -> None:
        """阶段 3：导入插件模型并挂载插件声明的路由。

        依赖按**逐路由**粒度解析：插件在 ``ctx.add_router(router, dependencies=[...])``
        里声明的专属依赖优先；未声明（``spec.dependencies is None``）的路由沿用本方法的
        ``dependencies`` 运行时默认值。HTTP 路由与 WebSocket 路由需要不同限流器
        （``RateLimiter`` / ``WebSocketRateLimiter``），统一依赖无法覆盖。

        参数:
        - app (FastAPI): FastAPI 应用。
        - dependencies (list[Any] | None): 运行时统一附加的 FastAPI 依赖（如 HTTP 限流器），
          作为未声明专属依赖的路由的默认值。

        返回:
        - None
        """
        for plugin_name, dotted_paths in self.registry.model_paths():
            loader.import_plugin_models(plugin_name, dotted_paths, self.package)

        routers = self.registry.load_main()
        for spec in routers:
            effective = spec.dependencies if spec.dependencies is not None else dependencies
            app.include_router(spec.router, dependencies=list(effective or []))

        app.state.__setattr__(RUNTIME_STATE_KEY, self)
        log.info(f"✅ 插件路由挂载完成: 显式路由 {len(routers)} 个")

    async def start(self, redis: object | None = None) -> None:
        """阶段 4：写种子、注册事件、注入 Redis、执行钩子与 ``Plugin.start()``，再注册定时任务。

        步骤顺序为 **种子 → 事件订阅 → redis/钩子/``Plugin.start()`` → 定时任务**：定时任务
        注册依赖槽位 ``scheduler.job_log_sink``，而该槽位的提供者正是插件自己的 ``start()``
        （真实实现见 ``module_task/plugin.py``）。注册若排在启动循环之前，全新进程里槽位必然
        还是 ``None``，插件声明的任务会被整批跳过 —— 故注册必须后置到全部插件启动步骤之后。

        按**插件粒度**隔离异常，任何单个插件的初始化问题都不中断应用启动：

        - **种子**：每个声明了种子的插件单独开会话与事务，失败只丢自己的种子（日志含
          插件名与目录路径），其余插件的种子照常写入；写入顺序不变，仍为
          「插件加载顺序 → 插件内声明顺序」。
        - **事件订阅**：按插件包裹，订阅失败的插件同样跳过其后续启动步骤。
        - **启动钩子 / ``Plugin.start()``**：失败的插件同样降级（并入 ``degraded_ids``），
          不记入已启动集合，也不参与 ``stop()`` 收尾。
        - **定时任务**：降级插件（含 ``Plugin.start()`` 抛异常者）声明的任务一律不注册；
          槽位实现（插件提供的外部代码）单条 ``register`` 抛异常只跳过该条；全部插件启动
          结束后槽位仍缺失时仅记 WARNING（无任何插件提供该槽位）。

        任一步骤失败的插件（种子写入／事件订阅／``Plugin.start()``）本轮都不进入运行态，
        与 ``setup()`` 失败降级同一语义：声明无法落地的插件不进入运行态，避免「半启动」
        （钩子跑了但数据缺失）把问题推迟到运行时。该规则贯穿本方法的每一步（含定时任务与
        启动汇总分母），不存在「降级却仍生效」的旁路。

        参数:
        - redis (object | None): Redis 客户端，注入给需要缓存的插件。

        返回:
        - None
        """
        degraded_ids = await self._apply_seeds()

        for entry in self.registry.entries:
            if id(entry) in degraded_ids:
                continue
            try:
                for event, handler in entry.context.event_handlers:
                    event_bus.subscribe(event, handler)
            except Exception as exc:  # 单插件事件订阅失败不阻塞其它插件
                degraded_ids.add(id(entry))
                log.exception(
                    f"❌ 插件 {entry.plugin_dir.name}（{entry.plugin_dir.path}）事件订阅失败，"
                    f"其后续启动步骤已跳过 — {exc!s}"
                )

        # 分母只数"本轮真的可能启动"的插件：降级插件永远进不了启动阶段，
        # 计入分母会把这行日志误读成"启动失败"。必须在启动循环**之前**取值：循环内会把
        # start() 失败的插件也并入 degraded_ids（它们已计入分母），届时该集合不再是"未计入
        # 分母的插件"，故另存下面的 skipped_before_start 供汇总行使用。
        total = sum(
            1
            for entry in self.registry.entries
            if entry.instance is not None and id(entry) not in degraded_ids
        )
        skipped_before_start = len(degraded_ids)

        for entry in self.registry.entries:
            instance = entry.instance
            if instance is None or id(entry) in degraded_ids:
                continue
            try:
                instance.set_redis(redis)
                for hook in entry.context.startup_hooks:
                    await hook()
                await instance.start()
            except Exception as exc:  # 单插件启动失败不阻塞其它插件
                # 并入降级集合：未进入运行态的插件其声明的定时任务同样不得注册
                degraded_ids.add(id(entry))
                log.exception(
                    f"❌ 插件 {entry.plugin_dir.name}（{entry.plugin_dir.path}）启动失败，"
                    f"其后续启动步骤已跳过 — {exc!s}"
                )
                continue
            self._started.append(entry)

        # 定时任务注册后置到启动循环之后：槽位 scheduler.job_log_sink 由插件在自己的
        # start() 里提供，提前注册会让全新进程的首启恒取到 None 槽位（任务被整批跳过）。
        await self._apply_scheduler_jobs(degraded_ids)

        summary = f"✅ 插件启动阶段完成: 已启动 {len(self._started)}/{total} 个插件"
        if skipped_before_start:
            summary += f"（另有 {skipped_before_start} 个插件因初始化失败被降级跳过，未计入分母）"
        log.info(summary)

    async def _apply_seeds(self) -> set[int]:
        """按插件粒度写入全部种子（每个插件独立会话与事务）。

        排序语义与单事务版本一致：外层按插件加载顺序、内层按插件内声明顺序；差别只在
        事务边界 —— 单个插件的种子失败整体回滚且不影响其它插件。

        返回:
        - set[int]: 种子写入失败的插件项 ``id`` 集合（调用方据此跳过其启动步骤）。
        """
        from app.core.database import async_db_session

        failed_ids: set[int] = set()
        ok = 0
        failed = 0
        for entry in self.registry.entries:
            seeds = entry.context.seeds
            if not seeds:
                continue
            try:
                async with async_db_session() as session:
                    async with session.begin():
                        await SeedApplier(session).apply_all(seeds)
            except Exception as exc:  # 单插件种子失败只丢自己的种子
                failed += 1
                failed_ids.add(id(entry))
                log.exception(
                    f"❌ 插件 {entry.plugin_dir.name}（{entry.plugin_dir.path}）种子写入失败，"
                    f"该插件的种子已整体回滚，并跳过本轮启动步骤 — {exc!s}"
                )
            else:
                ok += 1

        if ok or failed:
            log.info(f"✅ 插件种子阶段完成: 成功 {ok} 个插件 / 失败 {failed} 个插件")
        return failed_ids

    async def _apply_scheduler_jobs(self, degraded_ids: set[int]) -> None:
        """把插件声明的定时任务交给槽位实现（缺失时仅记日志）。

        由 ``start()`` 在**全部插件的启动步骤之后**调用：槽位 ``scheduler.job_log_sink``
        的提供者是插件自己的 ``start()``，早于启动循环调用只会取到 ``None``。

        与其余启动步骤同一语义：

        - **降级插件不参与**：``setup()`` 失败、种子写入、事件订阅或 ``Plugin.start()``
          失败的插件本轮不进入运行态，其声明的定时任务同样不注册，避免绕过
          「降级＝本轮完全不参与」。
        - **逐条隔离**：``sink`` 是插件经槽位提供的**外部代码**，``job`` 是插件声明数据；
          单条 ``register`` 抛异常只跳过该条（日志含插件名、目录路径、任务标识与槽位名），
          不阻塞应用启动。
        - **槽位缺失**：跑完所有插件启动步骤仍无人提供槽位，只记 WARNING（这是「插件未安装」
          的正常降级路径，不是错误）。

        参数:
        - degraded_ids (set[int]): 已降级插件项 ``id`` 集合。

        返回:
        - None
        """
        jobs = [
            (entry, job)
            for entry in self.registry.entries
            if id(entry) not in degraded_ids
            for job in entry.context.scheduler_jobs
        ]
        if not jobs:
            return
        sink = get(SLOT_SCHEDULER_JOB_LOG_SINK)
        if sink is None:
            log.warning(
                f"⚠️ 有 {len(jobs)} 个插件定时任务待注册，但全部插件启动完成后仍没有任何插件"
                f"提供槽位 {SLOT_SCHEDULER_JOB_LOG_SINK}（未安装提供该槽位的插件），已跳过；"
                "这些任务不会执行"
            )
            return
        for entry, job in jobs:
            job_label = job.get("job_id") or job.get("job_name") or job.get("code") or "<未命名>"
            try:
                await sink.register(job)
            except Exception as exc:  # 单条任务注册失败不阻塞应用启动
                log.exception(
                    f"❌ 插件 {entry.plugin_dir.name}（{entry.plugin_dir.path}）的定时任务 "
                    f"{job_label} 注册失败（槽位 {SLOT_SCHEDULER_JOB_LOG_SINK}），已跳过 — {exc!s}"
                )
                continue

    async def stop(self) -> None:
        """阶段 5：反序收尾**已成功启动**的插件（关闭钩子与 ``Plugin.stop()``）。

        ``setup()`` 失败降级、种子写入／事件订阅失败被跳过、或 ``start()`` 抛异常的插件
        都不在收尾范围内：对从未启动的插件调 ``stop()`` 可能抛出第二个异常并掩盖原始错误。

        返回:
        - None
        """
        for entry in reversed(self._started):
            try:
                if entry.instance is not None:
                    await entry.instance.stop()
                for hook in reversed(entry.context.shutdown_hooks):
                    await hook()
            except Exception as exc:  # 单插件关闭失败不影响其它插件收尾
                log.exception(
                    f"❌ 插件 {entry.plugin_dir.name}（{entry.plugin_dir.path}）关闭失败 — {exc!s}"
                )
        event_bus.clear()
        log.info("✅ 插件关闭阶段完成")


def get_runtime(app: FastAPI) -> PluginRuntime | None:
    """取应用上挂载的插件运行时。

    参数:
    - app (FastAPI): FastAPI 应用。

    返回:
    - PluginRuntime | None: 运行时实例。
    """
    return getattr(app.state, RUNTIME_STATE_KEY, None)


def migration_locations(root: Path | None = None) -> list[str]:
    """返回核心 + 全部插件的 Alembic 迁移目录（供 env.py 使用）。

    参数:
    - root (Path | None): 插件根目录。

    返回:
    - list[str]: 目录字符串列表。
    """
    from app.config.path_conf import ALEMBIC_VERSION_DIR

    dirs = [str(ALEMBIC_VERSION_DIR)]
    dirs.extend(str(p) for p in loader.iter_migration_dirs(loader.discover_plugins(root)))
    return dirs
