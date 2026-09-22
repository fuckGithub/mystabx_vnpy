"""模块文档规范测试（验收 A8；设计 D9、§4.12）。

不变量：每个模块目录都必须有 ``README.md``，且逐字包含 4 个固定小节标题：

    ``## 模块定位`` / ``## 入口`` / ``## 依赖`` / ``## 删除影响``

覆盖范围由本测试自身枚举（即"enforce 的集合 = 检查的集合"），分两路：

1. **插件模块**：由内核 ``discover_plugins()`` 给出（与运行时同源）——插件根目录，
   外加其每个含 ``__init__.py`` 的**直接子模块**目录；
2. **内核子系统**：``app/core/plugin``、``app/core/auth``（不由插件发现器发现）。

全部为同步测试：不进入事件循环，也不使用 ``test_client``（该 fixture 在本仓库必然报错）。
"""

from __future__ import annotations

from pathlib import Path

from app.core.plugin.loader import discover_plugins

APP_DIR = Path(__file__).resolve().parent.parent / "app"
"""``backend/app`` 目录。"""

REQUIRED_SECTIONS: tuple[str, ...] = (
    "## 模块定位",
    "## 入口",
    "## 依赖",
    "## 删除影响",
)
"""README 必须逐字包含的 4 个小节标题。"""

CORE_MODULE_DIRS: tuple[Path, ...] = (
    APP_DIR / "core" / "plugin",
    APP_DIR / "core" / "auth",
)
"""内核子系统目录（D9 要求同样具备 README）。"""

MIN_PLUGIN_ROOTS = frozenset({"system", "common"})
"""最小可运行集：目录发现至少要能命中它们，否则说明发现器或目录布局已异常。"""


def iter_plugin_dirs() -> list[Path]:
    """列出全部插件模块目录（插件根 + 其直接子模块）。

    返回:
    - list[Path]: 目录路径列表；每个插件根之后紧跟它的子模块目录。
    """
    dirs: list[Path] = []
    for plugin in discover_plugins():
        dirs.append(plugin.path)
        dirs.extend(
            sub
            for sub in sorted(plugin.path.iterdir())
            if sub.is_dir() and (sub / "__init__.py").is_file()
        )
    return dirs


def iter_module_dirs() -> list[Path]:
    """列出全部必须有 ``README.md`` 的模块目录。

    返回:
    - list[Path]: 插件模块目录 + 内核子系统目录。
    """
    return [*iter_plugin_dirs(), *CORE_MODULE_DIRS]


def test_module_dir_scan_is_not_empty() -> None:
    """目录枚举不得静默归零（否则下面的断言会恒真）。

    异常:
    - AssertionError: 插件目录、子模块目录或内核目录任一路为空时抛出。
    """
    plugins = discover_plugins()
    root_names = {p.name for p in plugins}

    assert plugins, "未发现任何插件目录：README 守卫已静默失效，请检查目录布局"
    assert MIN_PLUGIN_ROOTS <= root_names, (
        f"最小可运行集插件未发现：期望包含 {sorted(MIN_PLUGIN_ROOTS)}，实际 {sorted(root_names)}"
    )

    submodule_dirs = [d for d in iter_plugin_dirs() if d.parent.parent == APP_DIR / "plugin"]
    assert submodule_dirs, "未发现任何插件子模块目录（含 __init__.py 的直接子目录）"

    for core_dir in CORE_MODULE_DIRS:
        assert core_dir.is_dir(), f"内核模块目录不存在：{core_dir}"

    dirs = iter_module_dirs()
    assert len(set(dirs)) == len(dirs), f"目录枚举出现重复：{dirs}"


def test_every_module_has_readme_with_required_sections() -> None:
    """每个模块目录都必须有 README.md 且含 4 个固定小节；一次性列出全部违规项。

    异常:
    - AssertionError: 存在缺文件或缺小节的模块时抛出，消息内列出全部违规路径。
    """
    dirs = iter_module_dirs()
    assert dirs, "模块目录集合为空：README 守卫会静默失效"

    problems: list[str] = []
    for module_dir in dirs:
        readme = module_dir / "README.md"
        if not readme.is_file():
            problems.append(f"{readme} —— 缺少 README.md")
            continue
        text = readme.read_text(encoding="utf-8")
        missing = [section for section in REQUIRED_SECTIONS if section not in text]
        if missing:
            problems.append(f"{readme} —— 缺少小节：{'、'.join(missing)}")

    assert not problems, (
        f"共 {len(problems)}/{len(dirs)} 个模块的 README.md 不合规：\n"
        + "\n".join(f"  - {item}" for item in problems)
    )
