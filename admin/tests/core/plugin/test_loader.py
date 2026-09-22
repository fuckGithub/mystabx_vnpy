"""插件目录发现与依赖排序测试。"""

from __future__ import annotations

from pathlib import Path

from app.core.plugin.loader import (
    PluginDir,
    discover_plugins,
    iter_migration_dirs,
    sort_by_dependency,
)


def _make_plugin(root: Path, dir_name: str, toml: str | None, *, entry: bool = True) -> Path:
    """构造一个假插件目录。

    参数:
    - root (Path): 插件根目录。
    - dir_name (str): 目录名，如 ``module_ai``。
    - toml (str | None): ``plugin.toml`` 内容，``None`` 表示不写。
    - entry (bool): 是否写 ``plugin.py``。

    返回:
    - Path: 插件目录路径。
    """
    d = root / dir_name
    d.mkdir(parents=True)
    (d / "__init__.py").write_text("", encoding="utf-8")
    if toml is not None:
        (d / "plugin.toml").write_text(toml, encoding="utf-8")
    if entry:
        (d / "plugin.py").write_text("", encoding="utf-8")
    return d


def test_discover_ignores_non_module_dirs(tmp_path: Path) -> None:
    """只认 module_ 前缀目录，忽略 __pycache__ 等。"""
    _make_plugin(tmp_path, "module_ai", 'name = "ai"\ntitle = "AI"\nversion = "1.0.0"\n')
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "helpers").mkdir()
    plugins = discover_plugins(tmp_path)
    assert [p.name for p in plugins] == ["ai"]
    assert plugins[0].has_entry is True
    assert plugins[0].has_readme is False


def test_discover_without_toml_or_entry(tmp_path: Path) -> None:
    """无 plugin.toml / plugin.py 的存量插件也能被发现（回退目录扫描）。"""
    _make_plugin(tmp_path, "module_legacy", None, entry=False)
    plugins = discover_plugins(tmp_path)
    assert len(plugins) == 1
    assert plugins[0].manifest is None
    assert plugins[0].has_entry is False


def test_discover_skips_dir_with_only_pycache(tmp_path: Path) -> None:
    """只剩 ``__pycache__`` 的残留目录不算插件。

    删除插件源码（如从全量分支切到 lite）会留下缓存目录。若按 ``module_`` 前缀一律
    当插件，插件清单会被幽灵条目污染、每次启动刷「缺少 README.md」假警告，README
    守卫测试也会因这些空目录变红。
    """
    ghost = tmp_path / "module_ghost" / "__pycache__"
    ghost.mkdir(parents=True)
    (ghost / "x.cpython-314.pyc").write_bytes(b"")
    (tmp_path / "module_real").mkdir()
    (tmp_path / "module_real" / "__init__.py").write_text("", encoding="utf-8")

    assert [p.name for p in discover_plugins(tmp_path)] == ["real"]


def test_discover_keeps_dir_with_only_toml(tmp_path: Path) -> None:
    """只有 ``plugin.toml``、还没写入口的目录仍算插件（编写中/仅元数据）。"""
    d = tmp_path / "module_half"
    d.mkdir()
    (d / "plugin.toml").write_text(
        'name = "half"\ntitle = "Half"\nversion = "1.0.0"\n', encoding="utf-8"
    )

    plugins = discover_plugins(tmp_path)
    assert [p.name for p in plugins] == ["half"]
    assert plugins[0].manifest is not None
    assert plugins[0].has_entry is False


def test_discover_sorted_by_dir_name(tmp_path: Path) -> None:
    """发现结果按目录名排序，保证注册顺序稳定。"""
    _make_plugin(tmp_path, "module_zeta", 'name = "zeta"\ntitle = "Z"\nversion = "1.0.0"\n')
    _make_plugin(tmp_path, "module_alpha", 'name = "alpha"\ntitle = "A"\nversion = "1.0.0"\n')
    assert [p.name for p in discover_plugins(tmp_path)] == ["alpha", "zeta"]


def test_sort_by_dependency_puts_dependency_first(tmp_path: Path) -> None:
    """依赖方排在被依赖方之后。"""
    _make_plugin(
        tmp_path,
        "module_ai",
        'name = "ai"\ntitle = "AI"\nversion = "1.0.0"\ndepends = ["system"]\n',
    )
    _make_plugin(
        tmp_path,
        "module_system",
        'name = "system"\ntitle = "S"\nversion = "1.0.0"\n',
    )
    ordered = sort_by_dependency(discover_plugins(tmp_path))
    assert [p.name for p in ordered] == ["system", "ai"]


def test_sort_by_dependency_skips_cycle(tmp_path: Path) -> None:
    """循环依赖时跳过成环插件，不抛异常、不阻塞启动。"""
    _make_plugin(
        tmp_path, "module_a", 'name = "a"\ntitle = "A"\nversion = "1.0.0"\ndepends = ["b"]\n'
    )
    _make_plugin(
        tmp_path, "module_b", 'name = "b"\ntitle = "B"\nversion = "1.0.0"\ndepends = ["a"]\n'
    )
    _make_plugin(tmp_path, "module_c", 'name = "c"\ntitle = "C"\nversion = "1.0.0"\n')
    ordered = sort_by_dependency(discover_plugins(tmp_path))
    assert [p.name for p in ordered] == ["c"]


def test_sort_by_dependency_ignores_missing_dependency(tmp_path: Path) -> None:
    """依赖不存在的插件名时照常注册（只记 WARNING）。"""
    _make_plugin(
        tmp_path, "module_x", 'name = "x"\ntitle = "X"\nversion = "1.0.0"\ndepends = ["nope"]\n'
    )
    assert [p.name for p in sort_by_dependency(discover_plugins(tmp_path))] == ["x"]


def test_discover_tolerates_invalid_toml(tmp_path: Path) -> None:
    """畸形 plugin.toml（非法 TOML）不得抛异常，降级为无元数据插件。"""
    _make_plugin(tmp_path, "module_bad", 'name = "bad" this is not toml\n')
    plugins = discover_plugins(tmp_path)  # 不抛异常即通过
    assert [p.name for p in plugins] == ["bad"]
    assert plugins[0].manifest is None
    assert [p.name for p in sort_by_dependency(plugins)] == ["bad"]


def test_discover_tolerates_missing_required_fields(tmp_path: Path) -> None:
    """plugin.toml 缺必填字段（无 title/version）不得抛异常，降级为无元数据插件。"""
    _make_plugin(tmp_path, "module_partial", 'name = "partial"\n')
    plugins = discover_plugins(tmp_path)
    assert [p.name for p in plugins] == ["partial"]
    assert plugins[0].manifest is None
    assert [p.name for p in sort_by_dependency(plugins)] == ["partial"]


def test_sort_by_dependency_ignores_self_dependency(tmp_path: Path) -> None:
    """自依赖视为无效声明被忽略：自身与下游插件都不得被剔除。"""
    _make_plugin(
        tmp_path,
        "module_self",
        'name = "self"\ntitle = "S"\nversion = "1.0.0"\ndepends = ["self"]\n',
    )
    _make_plugin(
        tmp_path,
        "module_other",
        'name = "other"\ntitle = "O"\nversion = "1.0.0"\ndepends = ["self"]\n',
    )
    assert [p.name for p in sort_by_dependency(discover_plugins(tmp_path))] == ["self", "other"]


def test_iter_migration_dirs_only_existing(tmp_path: Path) -> None:
    """只返回真实存在的 migrations 目录。"""
    d = _make_plugin(tmp_path, "module_ai", 'name = "ai"\ntitle = "AI"\nversion = "1.0.0"\n')
    (d / "migrations").mkdir()
    assert iter_migration_dirs(discover_plugins(tmp_path)) == [d / "migrations"]


def test_plugin_dir_is_frozen_dataclass() -> None:
    """PluginDir 不可变（防止加载过程中被篡改）。"""
    p = PluginDir(
        name="a",
        dir_name="module_a",
        path=Path("/tmp/a"),
        manifest=None,
        has_entry=False,
        has_readme=False,
    )
    try:
        p.name = "b"  # type: ignore[misc]
    except Exception as exc:
        assert "frozen" in str(exc).lower() or "cannot assign" in str(exc).lower()
    else:
        raise AssertionError("PluginDir 应为不可变 dataclass")
