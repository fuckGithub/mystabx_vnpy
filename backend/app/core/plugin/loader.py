"""插件发现、依赖排序与模块导入。

本文件是内核中**唯一**被允许出现 ``app.plugin`` 字样的模块之一
（另一个是 ``app/core/discover.py``），因为它必须能动态导入插件包。
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from app.core.logger import log
from app.core.plugin.manifest import (
    CORE_PLUGIN_NAME,
    PLUGIN_DIR_PREFIX,
    PluginManifest,
    load_manifest,
    plugin_name_from_dir,
)

ENTRY_FILE = "plugin.py"
"""插件入口文件名（可选）。"""

MANIFEST_FILE = "plugin.toml"
"""插件元数据文件名（可选，畸形时降级为无元数据插件）。"""

README_FILE = "README.md"
"""模块文档文件名（必需，缺失记 WARNING）。"""

MODELS_DIR = "migrations"
"""插件迁移目录名。"""

DEFAULT_PACKAGE = "app.plugin"
"""插件根包名（测试可传假包名以隔离）。"""


@dataclass(frozen=True, slots=True)
class PluginDir:
    """一个已发现的插件目录（尚未导入其代码）。"""

    name: str
    """插件名，如 ``ai``。"""

    dir_name: str
    """目录名，如 ``module_ai``。"""

    path: Path
    """目录绝对路径。"""

    manifest: PluginManifest | None
    """``plugin.toml`` 解析结果；无该文件时为 ``None``。"""

    has_entry: bool
    """是否存在 ``plugin.py``。"""

    has_readme: bool
    """是否存在 ``README.md``。"""


def plugin_root_dir() -> Path:
    """返回 ``app.plugin`` 包所在目录。

    返回:
    - Path: 形如 ``.../app/plugin`` 的目录路径。
    """
    pkg = importlib.import_module("app.plugin")
    return Path(next(iter(pkg.__path__)))


def _has_module_content(path: Path) -> bool:
    """判断目录是否具备插件的最小内容（顶层有 ``*.py`` 源码或 ``plugin.toml``）。

    ``__pycache__`` 之类的构建产物单独存在时不算插件：删除插件源码后残留的缓存
    目录、尚未动笔的占位目录都属于这一类，它们不可能贡献路由/模型/种子。

    参数:
    - path (Path): 候选插件目录。

    返回:
    - bool: 具备最小内容时为 ``True``。
    """
    if (path / MANIFEST_FILE).is_file():
        return True
    return any(child.is_file() and child.suffix == ".py" for child in path.iterdir())


def discover_plugins(root: Path | None = None) -> list[PluginDir]:
    """扫描插件根目录下的 ``module_*`` 子目录。

    本函数保证**不抛异常**：畸形 ``plugin.toml``（非法 TOML、缺必填字段、非 UTF-8
    字节等）只会让该插件降级为「无元数据插件」（``manifest=None``），仍参与目录扫描
    与挂载，从而不阻塞应用启动。

    ``module_*`` 目录若既无 ``*.py`` 源码也无 ``plugin.toml``，按**空目录跳过**：
    若仍按插件计入，会污染插件清单、每次启动刷出「缺少 README.md」假警告，并让
    ``tests/test_module_readme.py`` 因这些空目录变红。

    参数:
    - root (Path | None): 插件根目录；``None`` 表示 ``app/plugin``（默认）。

    返回:
    - list[PluginDir]: 按目录名排序的插件列表。
    """
    base = root if root is not None else plugin_root_dir()
    if not base.is_dir():
        log.warning(f"⚠️ 插件根目录不存在，跳过发现: {base}")
        return []

    found: list[PluginDir] = []
    for path in sorted(base.iterdir(), key=lambda p: p.name):
        if not path.is_dir() or not path.name.startswith(PLUGIN_DIR_PREFIX):
            continue
        dir_name = path.name
        if dir_name == PLUGIN_DIR_PREFIX:  # 裸 module_ 目录
            continue
        if not _has_module_content(path):
            log.info(
                f"  ↳ 跳过空插件目录 {dir_name}：既无 *.py 源码也无 {MANIFEST_FILE}"
                "（通常是删除插件后残留的 __pycache__，或尚未动笔的占位目录）"
            )
            continue
        try:
            name = plugin_name_from_dir(dir_name)
        except ValueError as exc:
            log.error(f"❌ 跳过非法插件目录: {exc}")
            continue

        try:
            manifest = load_manifest(path)
        except Exception as exc:  # 畸形 plugin.toml 不得阻塞启动
            log.exception(
                f"❌ 插件 {dir_name} 的 {MANIFEST_FILE} 解析失败（{exc!s}），已降级为无元数据插件，"
                f"不影响加载；请修正该文件后重启: {path / MANIFEST_FILE}"
            )
            manifest = None

        if manifest is not None and manifest.name != name:
            log.warning(
                f"⚠️ 插件 {dir_name} 的 plugin.toml name={manifest.name!r} 与目录推导名 "
                f"{name!r} 不一致，以目录名 {name!r} 为准"
            )

        has_readme = (path / README_FILE).is_file()
        if not has_readme:
            log.warning(
                f"⚠️ 插件 {dir_name} 缺少 {README_FILE}（模块文档），"
                f"请补充「模块定位/入口/依赖/删除影响」四个小节：{path}"
            )

        found.append(
            PluginDir(
                name=name,
                dir_name=dir_name,
                path=path,
                manifest=manifest,
                has_entry=(path / ENTRY_FILE).is_file(),
                has_readme=has_readme,
            )
        )

    log.info(f"🔍 插件发现完成: {len(found)} 个 → {[p.name for p in found]}")
    return found


def sort_by_dependency(plugins: list[PluginDir]) -> list[PluginDir]:
    """按 ``depends`` 做拓扑排序，依赖方排在被依赖方之后。

    循环依赖或被依赖插件缺失的成员会被跳过（记 ERROR/WARNING），
    以保证任何插件集合都不会阻塞应用启动。

    指向自身的依赖（如 ``module_system`` 声明 ``depends = ["system"]``）属无效声明，
    仅记 WARNING 并忽略，不会触发环检测而剔除该插件。

    ``system`` 是保留名：若它确实已被发现（``module_system`` 已安装）则参与排序，
    保证系统模块先于依赖它的插件加载；未被发现时才视为内核隐式提供而忽略。

    参数:
    - plugins (list[PluginDir]): 已发现的插件列表。

    返回:
    - list[PluginDir]: 可安全加载的插件，按依赖顺序排列。
    """
    by_name = {p.name: p for p in plugins}
    order: list[PluginDir] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(plugin: PluginDir) -> bool:
        """深度优先访问，返回是否可加入加载序列。

        参数:
        - plugin (PluginDir): 当前插件。

        返回:
        - bool: ``True`` 表示可加载。
        """
        if plugin.name in visited:
            return True
        if plugin.name in visiting:
            log.error(f"❌ 插件 {plugin.name} 存在循环依赖，已跳过该插件")
            return False
        visiting.add(plugin.name)
        for dep in plugin.manifest.depends if plugin.manifest else []:
            if dep == plugin.name:
                # 自依赖是无效声明：若进入环检测会命中自身，导致该插件及其下游被整批剔除
                log.warning(
                    f"⚠️ 插件 {plugin.name} 的 depends 声明了自身（{dep!r}），"
                    f"自依赖无效，已忽略该依赖"
                )
                continue
            if dep == CORE_PLUGIN_NAME and dep not in by_name:
                continue  # 保留名：module_system 未安装时视为内核隐式提供
            target = by_name.get(dep)
            if target is None:
                log.warning(f"⚠️ 插件 {plugin.name} 依赖的插件 {dep!r} 不存在，忽略该依赖")
                continue
            if not visit(target):
                visiting.discard(plugin.name)
                return False
        visiting.discard(plugin.name)
        visited.add(plugin.name)
        order.append(plugin)
        return True

    for item in plugins:
        visit(item)

    skipped = [p.name for p in plugins if p.name not in visited]
    if skipped:
        log.error(f"❌ 以下插件因依赖问题被跳过: {skipped}")
    return order


def iter_migration_dirs(plugins: list[PluginDir]) -> list[Path]:
    """列出所有插件中真实存在的 ``migrations`` 目录。

    参数:
    - plugins (list[PluginDir]): 已发现的插件列表。

    返回:
    - list[Path]: 存在的迁移目录路径列表。
    """
    return [p.path / MODELS_DIR for p in plugins if (p.path / MODELS_DIR).is_dir()]


def import_plugin_models(
    plugin_name: str, dotted_paths: list[str], package: str = DEFAULT_PACKAGE
) -> None:
    """导入插件声明的 ORM 模型模块，使其注册到 ``MappedBase.metadata``。

    参数:
    - plugin_name (str): 插件名，如 ``ai``。
    - dotted_paths (list[str]): 相对插件目录的点分路径，如 ``["model.model", "chat.model"]``。
    - package (str): 插件根包名，默认 ``app.plugin``（测试可传假包名）。

    返回:
    - None
    """
    for dotted in dotted_paths:
        module_path = f"{package}.module_{plugin_name}.{dotted}"
        try:
            importlib.import_module(module_path)
        except Exception as exc:  # 单个插件模型导入失败不应阻塞启动
            log.exception(f"❌ 导入插件 {plugin_name} 的模型模块失败: {module_path} — {exc!s}")
