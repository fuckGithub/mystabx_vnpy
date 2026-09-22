"""插件目录与可选 ``plugin.toml`` 的展示信息（供 ``/application/portal/plugins``）。

目录发现与 ``plugin.toml`` 解析**统一委托**给内核 ``app.core.plugin.loader``（唯一实现），
本模块只把内核的 ``PluginDir`` 映射为管理端接口所用的扁平字典，不再自行扫描
``app/plugin`` 或解析 TOML。
"""

from __future__ import annotations

from typing import Any

from app.core.plugin.loader import discover_plugins


def list_plugin_infos() -> list[dict[str, Any]]:
    """
    列出所有 ``module_*`` 插件的汇总信息（含可选 manifest）。

    返回:
    - list[dict[str, Any]]: 按内核发现顺序（目录名排序）排列的列表，每项含
      ``module_dir``/``route_prefix``/``has_manifest``/``name``/``title``/``version``/
      ``description``/``optional``/``tags``/``manifest_name_mismatch``。
    """
    infos: list[dict[str, Any]] = []
    for plugin_dir in discover_plugins():
        manifest = plugin_dir.manifest
        # 展示 manifest 中**声明**的 name（而非目录推导名），与迁移前行为一致
        declared_name = manifest.name if manifest is not None else None
        infos.append({
            "module_dir": plugin_dir.dir_name,
            "route_prefix": f"/{plugin_dir.name}",
            "has_manifest": manifest is not None,
            "name": declared_name,
            "title": manifest.title if manifest is not None else None,
            "version": manifest.version if manifest is not None else None,
            "description": manifest.description if manifest is not None else None,
            "optional": manifest.optional if manifest is not None else None,
            "tags": manifest.tags if manifest is not None else None,
            "manifest_name_mismatch": bool(declared_name) and declared_name != plugin_dir.name,
        })
    return infos
