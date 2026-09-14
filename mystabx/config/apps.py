"""Optional vnpy BaseApp modules loaded into MainEngine (soft-fail per package)."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSpec:
    key: str
    package: str
    class_name: str
    # After add_app: call these no-arg methods on the engine (best-effort).
    post_init: tuple[str, ...] = ()


# Loadable apps (WebTrader omitted: app_name clashes with RpcService; product is already Web).
# ExcelRtd omitted from default load list — Windows COM; soft-import only if present.
APP_SPECS: dict[str, AppSpec] = {
    "cta": AppSpec("cta", "vnpy_ctastrategy", "CtaStrategyApp", ("init_engine",)),
    "backtester": AppSpec("backtester", "vnpy_ctabacktester", "CtaBacktesterApp", ("init_engine",)),
    "spread": AppSpec("spread", "vnpy_spreadtrading", "SpreadTradingApp"),
    "option": AppSpec("option", "vnpy_optionmaster", "OptionMasterApp"),
    "portfolio": AppSpec(
        "portfolio", "vnpy_portfoliostrategy", "PortfolioStrategyApp", ("init_engine",)
    ),
    "algo": AppSpec("algo", "vnpy_algotrading", "AlgoTradingApp", ("init_engine",)),
    "script": AppSpec("script", "vnpy_scripttrader", "ScriptTraderApp", ("init",)),
    "paper": AppSpec("paper", "vnpy_paperaccount", "PaperAccountApp"),
    "recorder": AppSpec("recorder", "vnpy_datarecorder", "DataRecorderApp", ("start",)),
    "datamanager": AppSpec("datamanager", "vnpy_datamanager", "DataManagerApp"),
    "risk": AppSpec("risk", "vnpy_riskmanager", "RiskManagerApp"),
    "rpc": AppSpec("rpc", "vnpy_rpcservice", "RpcServiceApp"),
    "chart": AppSpec("chart", "vnpy_chartwizard", "ChartWizardApp"),
    "portfolio_mgr": AppSpec("portfolio_mgr", "vnpy_portfoliomanager", "PortfolioManagerApp"),
    "excelrtd": AppSpec("excelrtd", "vnpy_excelrtd", "ExcelRtdApp"),
}

DEFAULT_APP_KEYS: tuple[str, ...] = tuple(
    key for key in APP_SPECS if key != "excelrtd"
)


def selected_app_keys() -> tuple[str, ...]:
    """env MYSTABX_APPS=cta,backtester,... or \"all\" / \"none\"."""
    raw = os.environ.get("MYSTABX_APPS", "all").strip().lower()
    if raw in {"", "none", "off", "0"}:
        return ()
    if raw in {"all", "*"}:
        return DEFAULT_APP_KEYS
    wanted = {part.strip() for part in raw.split(",") if part.strip()}
    return tuple(key for key in DEFAULT_APP_KEYS if key in wanted)


def iter_optional_apps(keys: Iterable[str] | None = None):
    """Yield (key, app_class, post_init) for apps that import successfully."""
    for key in keys if keys is not None else selected_app_keys():
        spec = APP_SPECS.get(key)
        if spec is None:
            continue
        try:
            module = __import__(spec.package, fromlist=[spec.class_name])
        except ImportError as exc:
            print(f"[mystabx] skip app {key}: {spec.package} not installed ({exc})")
            continue
        try:
            app_cls = getattr(module, spec.class_name)
        except AttributeError as exc:
            print(f"[mystabx] skip app {key}: {exc}")
            continue
        yield key, app_cls, spec.post_init


def probe_package(package: str) -> tuple[bool, str | None]:
    """Return (importable, error_message)."""
    try:
        __import__(package)
        return True, None
    except Exception as exc:  # noqa: BLE001 — soft probe for UI status
        return False, f"{type(exc).__name__}: {exc}"
