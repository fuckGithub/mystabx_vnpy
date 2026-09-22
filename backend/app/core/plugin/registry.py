"""插件注册表：聚合所有插件的注册项，对外提供只读视图。"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import log
from app.core.plugin.base import PluginBase
from app.core.plugin.context import JobSpec, PluginContext, RouterSpec, SeedSpec
from app.core.plugin.loader import PluginDir


@dataclass(slots=True)
class PluginEntry:
    """单个插件的加载产物。"""

    plugin_dir: PluginDir
    """发现的插件目录信息。"""

    context: PluginContext
    """``setup()`` 期间收集到的注册项。"""

    instance: PluginBase | None = None
    """插件实例；无 ``plugin.py`` 时为 ``None``。"""


class PluginRegistry:
    """插件注册表。"""

    def __init__(self) -> None:
        """初始化空注册表。"""
        self.entries: list[PluginEntry] = []

    def add(self, entry: PluginEntry) -> None:
        """登记一个插件。

        参数:
        - entry (PluginEntry): 插件加载产物。

        返回:
        - None
        """
        self.entries.append(entry)

    def routers(self) -> list[RouterSpec]:
        """返回全部插件声明的路由声明（只读视图，按插件加载顺序，不去重）。

        挂载请改用 ``load_main()``（含重复声明去重）。

        返回:
        - list[RouterSpec]: 路由声明列表（含各自的专属依赖）。
        """
        return [spec for entry in self.entries for spec in entry.context.routers]

    def load_main(self) -> list[RouterSpec]:
        """返回插件显式声明的路由声明（按加载顺序，同一 router 实例只出现一次）。

        去重语义收敛在**单次调用内**（局部集合）：同一实例在同一次返回里只出现一次，
        不同调用之间互不影响 —— 故本方法是幂等的，可重复调用且结果一致。
        判据是 ``spec.router`` 的实例 id（不看 ``RouterSpec``）：同一 router 被重复声明时
        保留**首次**的声明（含其专属依赖），后续重复项整条丢弃。
        重复声明仅在同一插件/多插件共享同一 router 实例时发生。

        返回:
        - list[RouterSpec]: 路由声明列表（含各自的专属依赖）。
        """
        specs: list[RouterSpec] = []
        seen_ids: set[int] = set()
        for entry in self.entries:
            for spec in entry.context.routers:
                if id(spec.router) in seen_ids:
                    log.warning(f"⚠️ 路由被重复声明，已忽略: {entry.plugin_dir.name}")
                    continue
                seen_ids.add(id(spec.router))
                specs.append(spec)
        return specs

    def model_paths(self) -> list[tuple[str, list[str]]]:
        """返回 ``(插件名, 模型点分路径列表)``。

        返回:
        - list[tuple[str, list[str]]]: 待导入的模型路径。
        """
        return [
            (entry.plugin_dir.name, list(entry.context.model_paths))
            for entry in self.entries
            if entry.context.model_paths
        ]

    def seeds(self) -> list[SeedSpec]:
        """按插件加载顺序返回全部种子声明。

        返回:
        - list[SeedSpec]: 种子声明列表。
        """
        return [spec for entry in self.entries for spec in entry.context.seeds]

    def scheduler_jobs(self) -> list[JobSpec]:
        """返回全部插件声明的定时任务。

        返回:
        - list[JobSpec]: 任务定义列表。
        """
        return [job for entry in self.entries for job in entry.context.scheduler_jobs]

    def manifests(self) -> list[dict]:
        """返回全部插件元数据（供 ``/application/portal/plugins`` 使用）。

        返回:
        - list[dict]: 每项含 ``name``/``title``/``version``/``description``/
          ``optional``/``tags``/``dir_name``/``route_prefix``/``has_manifest``。
        """
        items: list[dict] = []
        for entry in self.entries:
            manifest = entry.plugin_dir.manifest
            items.append({
                "name": entry.plugin_dir.name,
                "dir_name": entry.plugin_dir.dir_name,
                "route_prefix": f"/{entry.plugin_dir.name}",
                "has_manifest": manifest is not None,
                "title": manifest.title if manifest else None,
                "version": manifest.version if manifest else None,
                "description": manifest.description if manifest else None,
                "optional": manifest.optional if manifest else None,
                "tags": manifest.tags if manifest else None,
            })
        return items
