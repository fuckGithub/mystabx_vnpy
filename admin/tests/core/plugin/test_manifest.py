"""``plugin.toml`` 元数据解析测试。"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.plugin.manifest import (
    PluginManifest,
    load_manifest,
    plugin_name_from_dir,
)


def test_plugin_name_from_dir_strips_prefix() -> None:
    """``module_ai`` → ``ai``。"""
    assert plugin_name_from_dir("module_ai") == "ai"
    assert plugin_name_from_dir("module_system") == "system"


def test_plugin_name_from_dir_rejects_bad_name() -> None:
    """不以 ``module_`` 开头应报错。"""
    with pytest.raises(ValueError, match="module_"):
        plugin_name_from_dir("plugins_ai")


def test_load_manifest_reads_toml(tmp_path: Path) -> None:
    """正常解析必填字段与可选项。"""
    (tmp_path / "plugin.toml").write_text(
        'name = "ai"\n'
        'title = "AI 子系统"\n'
        'version = "1.2.0"\n'
        'description = "desc"\n'
        "optional = true\n"
        'depends = ["system"]\n'
        'tags = ["ai", "chat"]\n',
        encoding="utf-8",
    )
    manifest = load_manifest(tmp_path)
    assert manifest is not None
    assert manifest.name == "ai"
    assert manifest.title == "AI 子系统"
    assert manifest.version == "1.2.0"
    assert manifest.optional is True
    assert manifest.depends == ["system"]
    assert manifest.tags == ["ai", "chat"]


def test_load_manifest_returns_none_when_absent(tmp_path: Path) -> None:
    """无 ``plugin.toml`` 时返回 None（兼容存量插件）。"""
    assert load_manifest(tmp_path) is None


def test_load_manifest_requires_name_title_version(tmp_path: Path) -> None:
    """缺必填字段时校验失败。"""
    (tmp_path / "plugin.toml").write_text('name = "ai"\n', encoding="utf-8")
    with pytest.raises(ValidationError):
        load_manifest(tmp_path)


def test_manifest_defaults() -> None:
    """可选字段有安全默认值。"""
    manifest = PluginManifest(name="x", title="X", version="1.0.0")
    assert manifest.description == ""
    assert manifest.optional is False
    assert manifest.depends == []
    assert manifest.tags == []
