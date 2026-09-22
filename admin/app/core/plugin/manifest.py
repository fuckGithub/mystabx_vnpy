"""插件元数据（``plugin.toml``）解析与校验。"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

PLUGIN_DIR_PREFIX = "module_"
"""插件目录名前缀。"""

CONTAINER_NAME_LENGTH = len(PLUGIN_DIR_PREFIX)
"""容器前缀截断长度（``module_`` → 7 个字符）。"""

CORE_PLUGIN_NAME = "system"
"""内核保留的隐式依赖名。"""


class PluginManifest(BaseModel):
    """``plugin.toml`` 的结构化表示。"""

    name: str = Field(..., min_length=1, description="插件名，须等于目录名去掉 module_ 前缀")
    title: str = Field(..., min_length=1, description="中文标题")
    version: str = Field(..., min_length=1, description="语义化版本")
    description: str = Field(default="", description="功能描述")
    optional: bool = Field(default=False, description="可安全删除（信息性，不影响加载）")
    depends: list[str] = Field(default_factory=list, description="依赖的插件名列表")
    tags: list[str] = Field(default_factory=list, description="标签")


def plugin_name_from_dir(dir_name: str) -> str:
    """由插件目录名推导插件名。

    参数:
    - dir_name (str): 形如 ``module_ai`` 的目录名。

    返回:
    - str: 插件名，如 ``ai``。

    异常:
    - ValueError: 目录名不以 ``module_`` 开头，或前缀后无字符。
    """
    if not dir_name.startswith(PLUGIN_DIR_PREFIX):
        raise ValueError(f"插件目录名必须以 {PLUGIN_DIR_PREFIX!r} 开头，实际为 {dir_name!r}")
    name = dir_name[CONTAINER_NAME_LENGTH:]
    if not name:
        raise ValueError(f"插件目录名 {dir_name!r} 的 {PLUGIN_DIR_PREFIX!r} 前缀后缺少名称")
    return name


def loads_toml(raw: bytes) -> dict[str, Any]:
    """解析 TOML 字节内容。

    参数:
    - raw (bytes): TOML 文件内容。

    返回:
    - dict[str, Any]: 顶层表。
    """
    return tomllib.loads(raw.decode("utf-8"))


def load_manifest(plugin_dir: Path) -> PluginManifest | None:
    """读取并校验 ``plugin_dir/plugin.toml``。

    参数:
    - plugin_dir (Path): 插件目录。

    返回:
    - PluginManifest | None: 解析结果；文件不存在时返回 ``None``。
    """
    manifest_path = plugin_dir / "plugin.toml"
    if not manifest_path.is_file():
        return None
    return PluginManifest.model_validate(loads_toml(manifest_path.read_bytes()))
