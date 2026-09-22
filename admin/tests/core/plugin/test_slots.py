"""内核槽位测试。"""

from __future__ import annotations

from app.core.plugin.slots import SLOT_AUTH_USER_RESOLVER, clear_slots, get, provide


def test_provide_and_get() -> None:
    """注入后可按名取回实现。"""
    clear_slots()
    impl = object()
    provide(SLOT_AUTH_USER_RESOLVER, impl)
    assert get(SLOT_AUTH_USER_RESOLVER) is impl


def test_get_missing_returns_default() -> None:
    """未注入时返回默认值，不抛异常（保证降级可启动）。"""
    clear_slots()
    assert get(SLOT_AUTH_USER_RESOLVER) is None
    assert get(SLOT_AUTH_USER_RESOLVER, "fallback") == "fallback"


def test_clear_slots_removes_all() -> None:
    """clear_slots 用于测试隔离。"""
    provide("x", 1)
    clear_slots()
    assert get("x") is None
