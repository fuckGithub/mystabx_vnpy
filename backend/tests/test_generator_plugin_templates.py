"""代码生成器插件骨架测试（验收 A10；设计 D10、§4.13）。

不变量：

1. **模板清单**：``Jinja2TemplateUtil.get_template_list()`` 必须含 3 个插件骨架模板，
   且模板文件在磁盘上真实存在（生成/预览/下载/写入四条路径共用该清单）；
2. **输出位置**：这 3 个模板经 ``get_file_name`` 落到**插件根** ``module_xxx/``，
   而不是子模块目录内；
3. **子表不重复渲染**：``get_sub_template_list()`` 必须排除这 3 个模板（否则子表渲染会
   用子表上下文覆盖插件根文件）；
4. **渲染产物真的是插件**：用生成器同一套上下文渲染 ``plugin.py``/``plugin.toml``/
   ``README.md``，产物必须含模块级 ``PLUGIN = Plugin()`` 绑定、合法 ``plugin.toml``
   清单（可被内核 ``PluginManifest`` 校验）与 4 个固定 README 小节。

全部为同步测试：不进入事件循环，也不使用 ``test_client``。
"""

from __future__ import annotations

from app.config.path_conf import TEMPLATE_DIR
from app.core.plugin.manifest import PluginManifest, loads_toml
from app.plugin.module_generator.gencode.schema import GenTableOutSchema
from app.plugin.module_generator.gencode.tools.jinja2_template_util import (
    Jinja2TemplateUtil,
)

REQUIRED_TEMPLATES = frozenset({
    "python/plugin.toml.j2",
    "python/plugin.py.j2",
    "python/README.md.j2",
})
"""A10 要求的 3 个插件骨架模板（相对 ``TEMPLATE_DIR``）。"""

PLUGIN_ROOT_FILES = {
    "python/plugin.toml.j2": "plugin.toml",
    "python/plugin.py.j2": "plugin.py",
    "python/README.md.j2": "README.md",
}
"""模板 → 插件根下的产物文件名。"""

REQUIRED_README_SECTIONS: tuple[str, ...] = (
    "## 模块定位",
    "## 入口",
    "## 依赖",
    "## 删除影响",
)
"""README 产物必须含的 4 个固定小节（与 `tests/test_module_readme.py` 同一约定）。"""

PLUGIN_ROOT = "backend/app/plugin/module_demo"
"""示例生成的目标插件根（相对仓库根，与 ``Jinja2TemplateUtil`` 的映射一致）。"""


def _sample_table() -> GenTableOutSchema:
    """构造一份最小可用的生成表配置（不触库）。

    返回:
    - GenTableOutSchema: 示例表配置，包名 ``module_demo``、模块名 ``demo``。
    """
    return GenTableOutSchema(
        table_name="gen_demo",
        table_comment="示例表",
        class_name="Demo",
        package_name="module_demo",
        module_name="demo",
        business_name="demo",
        function_name="示例功能",
    )


def test_template_list_contains_plugin_scaffold() -> None:
    """模板清单必须包含 3 个插件骨架模板。

    异常:
    - AssertionError: 清单缺任一模板时抛出。
    """
    names = set(Jinja2TemplateUtil.get_template_list())
    assert REQUIRED_TEMPLATES <= names, f"模板清单缺少：{sorted(REQUIRED_TEMPLATES - names)}"


def test_template_files_exist_on_disk() -> None:
    """3 个插件骨架模板必须真实存在于磁盘。

    异常:
    - AssertionError: 任一模板文件缺失时抛出。
    """
    missing = [
        str(TEMPLATE_DIR / name)
        for name in sorted(REQUIRED_TEMPLATES)
        if not (TEMPLATE_DIR / name).is_file()
    ]
    assert not missing, f"模板文件缺失：{missing}"


def test_plugin_scaffold_outputs_to_plugin_root() -> None:
    """3 个模板必须输出到插件根 ``module_xxx/``，业务文件仍在子模块目录内。

    异常:
    - AssertionError: 输出路径落错层级时抛出。
    """
    table = _sample_table()
    got = {name: Jinja2TemplateUtil.get_file_name(name, table) for name in REQUIRED_TEMPLATES}
    expected = {name: f"{PLUGIN_ROOT}/{out}" for name, out in PLUGIN_ROOT_FILES.items()}
    assert got == expected, f"插件骨架输出路径不符：{got}"

    assert (
        Jinja2TemplateUtil.get_file_name("python/controller.py.j2", table)
        == f"{PLUGIN_ROOT}/demo/controller.py"
    ), "业务模板仍应写到子模块目录内"


def test_sub_render_list_excludes_plugin_scaffold() -> None:
    """子表渲染清单必须排除插件骨架模板（否则会覆盖插件根文件）。

    异常:
    - AssertionError: 子表清单仍含骨架模板，或与主表清单非包含关系时抛出。
    """
    main = set(Jinja2TemplateUtil.get_template_list())
    sub = set(Jinja2TemplateUtil.get_sub_template_list())
    assert not (sub & REQUIRED_TEMPLATES), (
        f"子表清单仍含骨架模板：{sorted(sub & REQUIRED_TEMPLATES)}"
    )
    assert sub < main, "子表清单应是主表清单的真子集"


def test_rendered_plugin_py_binds_plugin() -> None:
    """渲染产物 ``plugin.py`` 必须绑定 ``PLUGIN = Plugin()`` 并声明模型。

    缺少该模块级绑定会让整个插件静默失效（内核报 ERROR 并降级为无实例），
    故这里连绑定、``MODEL_PATHS`` 与 ``ctx.add_models`` 一起断言。

    异常:
    - AssertionError: 产物缺少绑定/模型声明时抛出。
    """
    ctx = Jinja2TemplateUtil.prepare_context(_sample_table())
    rendered = Jinja2TemplateUtil.get_env().get_template("python/plugin.py.j2").render(**ctx)

    assert "PLUGIN = Plugin()" in rendered, f"缺少 PLUGIN 绑定：\n{rendered}"
    assert "MODEL_PATHS" in rendered and "ctx.add_models(*MODEL_PATHS)" in rendered, rendered
    assert 'MODEL_PATHS: tuple[str, ...] = ("demo.model",)' in rendered, (
        f"单元素模型点位应为 ruff format 规范的紧凑形态：\n{rendered}"
    )


def test_rendered_plugin_toml_is_valid_manifest() -> None:
    """渲染产物 ``plugin.toml`` 必须能被内核 ``PluginManifest`` 校验通过。

    异常:
    - AssertionError: 缺少 A10 要求的字段或字段值不符时抛出。
    """
    ctx = Jinja2TemplateUtil.prepare_context(_sample_table())
    rendered = Jinja2TemplateUtil.get_env().get_template("python/plugin.toml.j2").render(**ctx)

    # 复用内核的 loads_toml，而不是在测试里另起一份 TOML 解析。
    data = loads_toml(rendered.encode("utf-8"))
    manifest = PluginManifest.model_validate(data)
    assert manifest.name == "demo", f"name 应为目录名去掉 module_ 前缀：{manifest.name}"
    assert manifest.title == "示例功能"
    assert manifest.version == "1.0.0"
    assert manifest.optional is True
    assert manifest.depends == ["system"]
    assert manifest.tags, "tags 不应为空"
    assert len(manifest.tags) == len(set(manifest.tags)), f"tags 不应重复：{manifest.tags}"


def test_rendered_readme_has_required_sections() -> None:
    """渲染产物 ``README.md`` 必须含 4 个固定小节与真实路由前缀/表名。

    异常:
    - AssertionError: 缺小节或内容与实际生成规则不符时抛出。
    """
    ctx = Jinja2TemplateUtil.prepare_context(_sample_table())
    rendered = Jinja2TemplateUtil.get_env().get_template("python/README.md.j2").render(**ctx)

    missing = [s for s in REQUIRED_README_SECTIONS if s not in rendered]
    assert not missing, f"README 产物缺少小节：{missing}\n{rendered}"
    assert "/demo/demo" in rendered, "README 的路由前缀应与 discover 容器前缀一致"
    assert "`gen_demo`" in rendered, "README 应填入真实表名"


def test_plugin_model_paths_covers_sub_table_module() -> None:
    """子表使用独立模块目录时，``MODEL_PATHS`` 必须同时声明两个模型模块。

    异常:
    - AssertionError: 子表模型点位缺失时抛出。
    """
    table = _sample_table()
    table.sub = True
    table.sub_table = GenTableOutSchema(
        table_name="gen_demo_item",
        class_name="DemoItem",
        package_name="module_demo",
        module_name="demo_item",
    )
    assert Jinja2TemplateUtil.get_plugin_model_paths(table) == ["demo.model", "demo_item.model"]
    # 多元素用展开形态（尾随逗号使 ruff format 保持展开）
    assert (
        Jinja2TemplateUtil.format_python_tuple_literal(["demo.model", "demo_item.model"])
        == '(\n    "demo.model",\n    "demo_item.model",\n)'
    )

    # 子表与主表同模块目录时不重复声明
    table.sub_table.module_name = "demo"
    assert Jinja2TemplateUtil.get_plugin_model_paths(table) == ["demo.model"]


def test_loads_toml_parses_plugin_manifest_bytes() -> None:
    """内核 ``loads_toml`` 必须能直接解析 ``plugin.toml`` 的字节内容。

    该函数在 Python 3.14 下限下应只走标准库 ``tomllib``；本用例锁定的
    是它的对外行为（输入 bytes、输出顶层表），以免将来的优化改坏契约。
    """
    raw = b'name = "demo"\nversion = "1.0.0"\n\n[extra]\nkey = "value"\n'
    data = loads_toml(raw)
    assert data["name"] == "demo"
    assert data["version"] == "1.0.0"
    assert data["extra"] == {"key": "value"}
