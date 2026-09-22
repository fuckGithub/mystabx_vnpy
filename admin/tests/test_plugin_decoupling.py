"""内核解耦静态不变量测试（验收 A2）。

内核（``app/{core,common,utils,config,scripts}``）不得引用任何插件（``app.plugin``）。
白名单仅两个加载器文件，且它们只允许通过 ``importlib.import_module(...)`` **动态**导入插件根
包，不得静态 ``import`` / ``from ... import`` 插件及其子模块。

扫描判据是字面量子串 ``app.plugin``，**注释与 docstring 同样计入**（文档措辞会让解耦结论
变得不可验证）；若只是想说明插件根包名，请引用 ``loader.DEFAULT_PACKAGE`` 或改写措辞。

本文件不进入应用 lifespan，不依赖数据库/Redis，故不使用 conftest 的 ``test_client``。
"""

from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"

SCANNED_DIRS = ("core", "common", "utils", "config", "scripts")
"""被扫描的内核目录（相对 ``app``）。"""

ALLOWED = {
    "core/plugin/loader.py",
    "core/discover.py",
}
"""白名单加载器（内核中仅这两个文件允许出现插件根包字样）。"""

NEEDLE = "app.plugin"
"""插件根包名字面量（点号写法；``app/plugin`` 路径写法不算命中）。"""

SCAN_REMEDY = (
    "内核禁止出现该字面量（含注释与 docstring）；若只是想说明插件根包名，"
    "请引用 loader.DEFAULT_PACKAGE 或改写措辞。"
)


def _scan() -> list[tuple[str, int, str]]:
    """扫描内核目录中命中 ``NEEDLE`` 的位置（已排除白名单文件）。

    返回:
    - list[tuple[str, int, str]]: ``(相对 app 的路径, 行号, 去首尾空白的行内容)``。
    """
    hits: list[tuple[str, int, str]] = []
    for dir_name in SCANNED_DIRS:
        for path in sorted((APP_DIR / dir_name).rglob("*.py")):
            rel = path.relative_to(APP_DIR).as_posix()
            if rel in ALLOWED:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if NEEDLE in line:
                    hits.append((rel, lineno, line.strip()))
    return hits


def _format(hits: list[tuple[str, int, str]]) -> str:
    """把命中列表渲染成 ``相对路径:行号: 行内容`` 多行文本。

    参数:
    - hits (list[tuple[str, int, str]]): :func:`_scan` 的返回值（或其中一部分）。

    返回:
    - str: 每行一条命中，末尾附上修复提示。
    """
    lines = [f"  {rel}:{lineno}: {text}" for rel, lineno, text in hits]
    return "\n".join([*lines, SCAN_REMEDY])


def _static_plugin_imports(path: Path) -> list[tuple[int, str]]:
    """找出文件中静态导入 ``app.plugin`` 的语句节点。

    参数:
    - path (Path): 待解析的 Python 文件。

    返回:
    - list[tuple[int, str]]: ``(行号, 源码语句)``；空列表表示无静态插件导入。
    """
    source = path.read_text(encoding="utf-8")
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            # ``from app import plugin`` 与 ``from app.plugin.x import y`` 同为静态硬依赖。
            names = [node.module or ""]
            if node.module == "app":
                names += [f"app.{alias.name}" for alias in node.names]
        else:
            continue
        if any(name == NEEDLE or name.startswith(f"{NEEDLE}.") for name in names):
            statement = ast.get_source_segment(source, node) or ""
            found.append((node.lineno, " ".join(statement.split())))
    return found


# T22 完成：initialize.py / create_tables.py 已删除，lifespan 的两个 service 已迁入
# module_system 插件，base_model.py 的 TYPE_CHECKING 插件导入已换成内核 UserLike。
def test_kernel_does_not_reference_plugins() -> None:
    """内核目录（白名单外）零 ``app.plugin`` 引用。"""
    hits = _scan()
    assert not hits, "内核出现插件引用：\n" + _format(hits)


def test_whitelisted_loaders_use_import_module() -> None:
    """白名单加载器不得静态导入插件（只允许 ``importlib.import_module``）。"""
    missing = [rel for rel in sorted(ALLOWED) if not (APP_DIR / rel).is_file()]
    assert not missing, f"白名单文件不存在，白名单已过期：{missing}"

    offenders = [
        (rel, lineno, source)
        for rel in sorted(ALLOWED)
        for lineno, source in _static_plugin_imports(APP_DIR / rel)
    ]
    assert not offenders, "白名单加载器出现静态插件导入（应改为 importlib.import_module）：\n" + (
        "\n".join(f"  {rel}:{lineno}: {source}" for rel, lineno, source in offenders)
    )


# T22 完成：app/scripts 只剩 __init__.py 与 init_app.py，均无插件引用。
def test_scripts_do_not_reference_plugins() -> None:
    """``app/scripts`` 零插件引用（防止再次出现硬编码 router 或模型清单）。"""
    hits = [hit for hit in _scan() if hit[0].startswith("scripts/")]
    assert not hits, "app/scripts 出现插件引用：\n" + _format(hits)
