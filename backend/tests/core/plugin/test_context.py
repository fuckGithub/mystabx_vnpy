"""插件上下文注册项收集测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import APIRouter, Depends

from app.core.plugin.context import PluginContext, RouterSpec, SeedRelation

ROUTER = APIRouter(prefix="/demo", tags=["demo"])


def _demo_dep() -> None:
    """测试用路由专属依赖。"""


def test_add_router_and_models(tmp_path: Path) -> None:
    """路由声明与模型路径被收集（未传 dependencies 即沿用运行时默认）。"""
    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    ctx.add_router(ROUTER)
    ctx.add_models("model.model", "chat.model")
    assert ctx.routers == [RouterSpec(router=ROUTER, dependencies=None)]
    assert ctx.model_paths == ["model.model", "chat.model"]


def test_add_router_with_explicit_dependencies(tmp_path: Path) -> None:
    """传了 dependencies 的路由把专属依赖存在声明里（不再只有 router 本体）。"""
    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    dep = Depends(_demo_dep)
    ctx.add_router(ROUTER, dependencies=[dep])
    spec = ctx.routers[0]
    assert spec.router is ROUTER
    deps = spec.dependencies
    assert deps is not None
    assert deps == [dep]
    assert deps[0].dependency is _demo_dep


def test_add_seed_inline(tmp_path: Path) -> None:
    """内联种子行与自然键被收集。"""
    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    ctx.add_seed("sys_menu", [{"name": "A"}], natural_key="route_path")
    assert len(ctx.seeds) == 1
    spec = ctx.seeds[0]
    assert spec.table == "sys_menu"
    assert spec.rows == [{"name": "A"}]
    assert spec.natural_key == "route_path"
    assert spec.children_field == "children"
    assert spec.parent_field == "parent_id"


def test_add_seed_file_reads_json(tmp_path: Path) -> None:
    """从 JSON 文件读取种子，含 relations。"""
    (tmp_path / "seeds").mkdir()
    (tmp_path / "seeds" / "sys_dict_data.json").write_text(
        json.dumps([{"dict_label": "男", "dict_value": "0", "dict_type": "sys_user_sex"}]),
        encoding="utf-8",
    )
    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    ctx.add_seed_file(
        "sys_dict_data",
        "seeds/sys_dict_data.json",
        natural_key=("dict_type", "dict_value"),
        relations=[
            SeedRelation(
                field="dict_type_id",
                ref_table="sys_dict_type",
                ref_key="dict_type",
                source_field="dict_type",
            )
        ],
    )
    assert ctx.seeds[0].natural_key == ("dict_type", "dict_value")
    assert ctx.seeds[0].relations[0].ref_table == "sys_dict_type"
    assert ctx.seeds[0].rows[0]["dict_label"] == "男"


def test_add_seed_file_missing_raises(tmp_path: Path) -> None:
    """种子文件不存在时报错，避免静默丢数据。"""
    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        ctx.add_seed_file("sys_menu", "seeds/nope.json")


def test_event_and_hooks_and_jobs(tmp_path: Path) -> None:
    """事件处理器、启动/关闭钩子与定时任务被收集。"""

    async def handler(payload: dict) -> None:
        """示例事件处理器。"""

    async def hook() -> None:
        """示例钩子。"""

    ctx = PluginContext(plugin_name="demo", base_dir=tmp_path)
    ctx.on("auth.login", handler)
    ctx.add_startup_hook(hook)
    ctx.add_shutdown_hook(hook)
    ctx.add_scheduler_job({
        "job_id": "cleanup",
        "trigger": "cron",
        "cron": "0 3 * * *",
        "code": "def handler(): pass",
    })
    assert ctx.event_handlers == [("auth.login", handler)]
    assert ctx.startup_hooks == [hook]
    assert ctx.shutdown_hooks == [hook]
    assert ctx.scheduler_jobs[0].get("job_id") == "cleanup"
