"""插件框架：发现、注册、装配、槽位与事件。

本包与 ``loader.py`` 是内核中唯一允许动态导入插件包的位置。
"""

from app.core.plugin.base import PluginBase
from app.core.plugin.context import JobSpec, PluginContext, RouterSpec, SeedRelation, SeedSpec
from app.core.plugin.events import EventBus, event_bus
from app.core.plugin.loader import PluginDir, discover_plugins, sort_by_dependency
from app.core.plugin.manifest import PluginManifest
from app.core.plugin.registry import PluginEntry, PluginRegistry
from app.core.plugin.runtime import PluginRuntime, get_runtime, migration_locations
from app.core.plugin.slots import clear_slots, get, provide

__all__ = [
    "EventBus",
    "JobSpec",
    "PluginBase",
    "PluginContext",
    "PluginDir",
    "PluginEntry",
    "PluginManifest",
    "PluginRegistry",
    "PluginRuntime",
    "RouterSpec",
    "SeedRelation",
    "SeedSpec",
    "clear_slots",
    "discover_plugins",
    "event_bus",
    "get",
    "get_runtime",
    "migration_locations",
    "provide",
    "sort_by_dependency",
]
