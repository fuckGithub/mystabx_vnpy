"""槽位命名与内核解耦的静态校验。"""

from __future__ import annotations

from pathlib import Path

from app.core.plugin.slots import (
    SLOT_AUTH_DATA_SCOPE_MODELS,
    SLOT_AUTH_USER_RESOLVER,
    SLOT_CONFIG_PARAMS_PROVIDER,
    SLOT_LOG_OPERATION_SINK,
    SLOT_SCHEDULER_JOB_LOG_SINK,
    clear_slots,
    get,
)

APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"

EXPECTED_SLOTS = {
    "auth.user_resolver": SLOT_AUTH_USER_RESOLVER,
    "auth.data_scope_models": SLOT_AUTH_DATA_SCOPE_MODELS,
    "log.operation_sink": SLOT_LOG_OPERATION_SINK,
    "config.params_provider": SLOT_CONFIG_PARAMS_PROVIDER,
    "scheduler.job_log_sink": SLOT_SCHEDULER_JOB_LOG_SINK,
}


def test_slot_names_are_stable() -> None:
    """槽位名是跨插件契约，不得随意更改。"""
    for expected, actual in EXPECTED_SLOTS.items():
        assert actual == expected, f"槽位名变更：{expected!r} → {actual!r}"


def test_missing_slots_return_none() -> None:
    """未注入时返回 None，调用方可安全降级。"""
    clear_slots()
    for name, value in EXPECTED_SLOTS.items():
        assert get(value) is None, f"槽位 {name} 未注入时应为 None"


def test_dependencies_has_no_business_import() -> None:
    """``dependencies.py`` 不得依赖任何具体业务模块。"""
    text = (APP_DIR / "core" / "dependencies.py").read_text(encoding="utf-8")
    assert "module_system" not in text
    assert "UserModel" not in text
    assert "UserCRUD" not in text


def test_dependencies_uses_resolver_slot() -> None:
    """``dependencies.py`` 通过槽位获取用户解析器。"""
    text = (APP_DIR / "core" / "dependencies.py").read_text(encoding="utf-8")
    assert SLOT_AUTH_USER_RESOLVER in text


def test_permission_has_no_business_import() -> None:
    """``permission.py`` 不得依赖任何具体业务模型。"""
    text = (APP_DIR / "core" / "permission.py").read_text(encoding="utf-8")
    assert "DeptModel" not in text
    assert "UserModel" not in text
    assert "module_system" not in text


def test_permission_uses_data_scope_slot() -> None:
    """``permission.py`` 通过槽位获取数据权限模型。"""
    text = (APP_DIR / "core" / "permission.py").read_text(encoding="utf-8")
    assert SLOT_AUTH_DATA_SCOPE_MODELS in text
