"""Headless vnpy MainEngine — no Qt UI imports (docs/01, docs/06 B2). Powered by vn.py MainEngine."""

from __future__ import annotations

from typing import Any

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from mystabx.config.apps import APP_SPECS, iter_optional_apps, selected_app_keys


def build_headless_engines() -> tuple[MainEngine, EventEngine, dict[str, dict[str, Any]]]:
    """Create engines and soft-load selected BaseApp modules.

    Returns (main_engine, event_engine, app_registry) where registry maps
    app key -> {loaded, app_name, package, error, post_init_ok}.
    """
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    # Named instances are registered later by AccountGatewayManager.
    _ = CtpGateway

    registry: dict[str, dict[str, Any]] = {}
    selected = set(selected_app_keys())

    for key, spec in APP_SPECS.items():
        if key not in selected:
            registry[key] = {
                "loaded": False,
                "selected": False,
                "app_name": None,
                "package": spec.package,
                "error": "not selected (MYSTABX_APPS)",
                "post_init_ok": None,
            }

    for key, app_cls, post_init in iter_optional_apps():
        package = APP_SPECS[key].package
        try:
            engine = main_engine.add_app(app_cls)
        except Exception as exc:  # noqa: BLE001
            registry[key] = {
                "loaded": False,
                "selected": True,
                "app_name": getattr(app_cls, "app_name", None),
                "package": package,
                "error": f"add_app failed: {exc}",
                "post_init_ok": False,
            }
            continue

        post_ok = True
        post_errors: list[str] = []
        for method_name in post_init:
            method = getattr(engine, method_name, None)
            if not callable(method):
                post_errors.append(f"missing {method_name}")
                post_ok = False
                continue
            try:
                method()
            except Exception as exc:  # noqa: BLE001
                post_ok = False
                post_errors.append(f"{method_name}: {exc}")

        registry[key] = {
            "loaded": True,
            "selected": True,
            "app_name": app_cls.app_name,
            "package": package,
            "error": "; ".join(post_errors) if post_errors else None,
            "post_init_ok": post_ok,
        }

    return main_engine, event_engine, registry
