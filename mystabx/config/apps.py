"""Optional vnpy BaseApp modules loaded into the Function menu."""

from __future__ import annotations

import os
from collections.abc import Iterable

# env MYSTABX_APPS=cta,backtester,datamanager,chart  or "none"
DEFAULT_APP_KEYS = ("cta", "backtester", "datamanager", "chart")

APP_SPECS: dict[str, tuple[str, str]] = {
    "cta": ("vnpy_ctastrategy", "CtaStrategyApp"),
    "backtester": ("vnpy_ctabacktester", "CtaBacktesterApp"),
    "datamanager": ("vnpy_datamanager", "DataManagerApp"),
    "chart": ("vnpy_chartwizard", "ChartWizardApp"),
}


def selected_app_keys() -> tuple[str, ...]:
    raw = os.environ.get("MYSTABX_APPS", ",".join(DEFAULT_APP_KEYS)).strip().lower()
    if raw in {"", "none", "off", "0"}:
        return ()
    wanted = {part.strip() for part in raw.split(",") if part.strip()}
    return tuple(key for key in DEFAULT_APP_KEYS if key in wanted)


def iter_optional_apps(keys: Iterable[str] | None = None):
    """Yield (key, app_class) for apps that import successfully."""
    for key in keys if keys is not None else selected_app_keys():
        if key not in APP_SPECS:
            continue
        module_name, class_name = APP_SPECS[key]
        try:
            module = __import__(module_name, fromlist=[class_name])
        except ImportError:
            print(f"[mystabx] skip app {key}: {module_name} not installed")
            continue
        yield key, getattr(module, class_name)
