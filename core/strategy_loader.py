"""Load / compile CTA strategy source from MySQL for live + backtest runs.

MySQL ``strategy_classes.source_code`` (and optional per-instance override on
``strategy_instances.source_code``) is authoritative. Disk ``strategies/*.py`` is
a materialization cache so vnpy folder loaders stay compatible.
"""

from __future__ import annotations

import importlib
import logging
import re
import sys
import types
from pathlib import Path
from typing import Any

from mystabx.paths import PROJECT_ROOT

from core import strategy_store

logger = logging.getLogger("stabx.strategy_loader")

_STRATEGIES_DIR = (PROJECT_ROOT / "strategies").resolve()
_PARENT_CLASS = "EliteCtaTemplate"
_PARENT_IMPORT = "from core.strategy_shim import EliteCtaTemplate, HistoryManager, sma, cross_over, cross_below"


def parent_class_info(parent_class: str | None = None) -> dict[str, str]:
    try:
        from core import base_class_store

        row = (
            base_class_store.get_base_class(parent_class)
            if parent_class
            else base_class_store.get_default_base_class()
        )
    except Exception:
        row = None
    if row:
        return {
            "parent_class": str(row.get("class_name") or _PARENT_CLASS),
            "parent_module": str(row.get("module") or "core.strategy_shim"),
            "base_chain": str(row.get("base_chain") or "CtaTemplate → TargetPosTemplate → EliteCtaTemplate"),
            "import_stmt": str(row.get("import_stmt") or _PARENT_IMPORT),
            "note": str(row.get("description") or ""),
        }
    return {
        "parent_class": _PARENT_CLASS,
        "parent_module": "core.strategy_shim",
        "base_chain": "CtaTemplate → TargetPosTemplate → EliteCtaTemplate",
        "import_stmt": _PARENT_IMPORT,
        "note": "默认模板继承本仓库 EliteCtaTemplate（对标 VeighNa Elite；开源 shim）",
    }


def apply_parent_to_source(content: str, parent_class: str, import_stmt: str = "") -> str:
    """Rewrite class inheritance + ensure import for selected base class."""
    text = content or ""
    parent = _safe_ident(parent_class) or _PARENT_CLASS
    stmt = (import_stmt or "").strip() or parent_class_info(parent).get("import_stmt") or _PARENT_IMPORT

    # Replace `class Name(OldParent):` — keep class name, swap parent
    text = re.sub(
        r"(class\s+[A-Za-z_][A-Za-z0-9_]*\s*\()\s*[A-Za-z_][A-Za-z0-9_]*\s*(\))",
        rf"\1{parent}\2",
        text,
        count=1,
    )

    # Drop known parent imports then insert selected import after __future__ / at top
    lines = text.splitlines()
    filtered: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("from core.strategy_shim import"):
            continue
        if stripped.startswith("from vnpy_ctastrategy import") and any(
            x in stripped for x in ("CtaTemplate", "TargetPosTemplate", "EliteCtaTemplate")
        ):
            continue
        filtered.append(line)

    insert_at = 0
    for i, line in enumerate(filtered):
        if line.startswith("from __future__"):
            insert_at = i + 1
            while insert_at < len(filtered) and filtered[insert_at].strip() == "":
                insert_at += 1
            break
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i
            break
        if line.startswith("class "):
            insert_at = i
            break

    filtered.insert(insert_at, stmt)
    if insert_at + 1 < len(filtered) and filtered[insert_at + 1].strip() != "":
        filtered.insert(insert_at + 1, "")
    return "\n".join(filtered) + ("\n" if text.endswith("\n") else "")


def default_strategy_source(class_name: str = "UserStrategy", parent_class: str | None = None) -> str:
    """Default editable strategy body for the Web IDE."""
    safe = _safe_ident(class_name) or "UserStrategy"
    info = parent_class_info(parent_class)
    parent = info["parent_class"]
    import_stmt = info.get("import_stmt") or _PARENT_IMPORT
    note = info.get("note") or f"父类：{info.get('parent_module')}.{parent}"
    return f'''"""可编辑策略 — 源码以 MySQL 为准，运行前由后端动态编译。

{note}
父类：{info.get("parent_module")}.{parent}
"""

from __future__ import annotations

{import_stmt}


class {safe}({parent}):
    """双均线目标仓位示例：金叉做多、死叉做空。"""

    author = "Stabx"

    bar_window: int = 1
    bar_interval: str = "1m"
    bar_buffer: int = 100
    fast_window: int = 10
    slow_window: int = 20
    fixed_size: int = 1

    parameters = [
        "bar_window",
        "bar_interval",
        "bar_buffer",
        "fast_window",
        "slow_window",
        "fixed_size",
    ]
    variables: list[str] = []

    def on_history(self, hm: HistoryManager) -> None:
        fast = sma(hm.close, int(self.fast_window))
        slow = sma(hm.close, int(self.slow_window))
        diff = fast - slow
        if cross_over(diff, 0.0):
            self.set_target(int(self.fixed_size))
        elif cross_below(diff, 0.0):
            self.set_target(-int(self.fixed_size))
        self.execute_trading(0)
'''


def _safe_ident(name: str) -> str:
    text = re.sub(r"[^0-9A-Za-z_]", "_", (name or "").strip())
    if text and text[0].isdigit():
        text = f"S_{text}"
    return text


def compile_strategy_source(source: str, *, prefer_name: str = "") -> type:
    """Compile source string and return the CTA strategy class."""
    from vnpy_ctastrategy import CtaTemplate, TargetPosTemplate

    from core.strategy_shim import EliteCtaTemplate

    skip = {CtaTemplate, TargetPosTemplate, EliteCtaTemplate}
    module_name = f"strategies._db_{_safe_ident(prefer_name) or 'anon'}"
    module = types.ModuleType(module_name)
    module.__file__ = f"<mysql:{prefer_name or 'strategy'}>"
    sys.modules[module_name] = module
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    found: list[type] = []
    for value in module.__dict__.values():
        if not isinstance(value, type):
            continue
        if value in skip:
            continue
        try:
            if not issubclass(value, CtaTemplate):
                continue
        except TypeError:
            continue
        found.append(value)

    if not found:
        raise ValueError("源码中未找到继承 CtaTemplate / TargetPosTemplate / EliteCtaTemplate 的策略类")

    if prefer_name:
        for cls in found:
            if cls.__name__ == prefer_name:
                return cls
        cls = found[0]
        cls.__name__ = prefer_name
        cls.__qualname__ = prefer_name
        return cls
    return found[0]


def resolve_source_for_class(class_name: str) -> dict[str, Any]:
    """Prefer MySQL class source; fall back to strategies/*.py; else default template."""
    name = class_name.strip()
    stored = strategy_store.get_strategy_source(name)
    if stored and (stored.get("content") or "").strip():
        return {
            "class_name": name,
            "content": stored["content"],
            "file_path": stored.get("file_path") or "",
            "editable": bool(stored.get("editable", True)),
            "updated_at": stored.get("updated_at"),
            "store": "mysql",
            "is_default": False,
            **parent_class_info(),
        }

    path = _guess_file_path(name)
    if path.is_file():
        content = path.read_text(encoding="utf-8")
        try:
            rel = str(path.resolve().relative_to(PROJECT_ROOT.resolve()))
        except ValueError:
            rel = str(path)
        strategy_store.sync_class_from_file(
            class_name=name,
            path=path,
            module=f"strategies.{path.stem}",
            editable=str(path.resolve()).startswith(str(_STRATEGIES_DIR)),
            project_root=PROJECT_ROOT,
        )
        return {
            "class_name": name,
            "content": content,
            "file_path": rel,
            "editable": str(path.resolve()).startswith(str(_STRATEGIES_DIR)),
            "updated_at": None,
            "store": "file",
            "is_default": False,
            **parent_class_info(),
        }

    content = default_strategy_source(name)
    return {
        "class_name": name,
        "content": content,
        "file_path": f"strategies/{_camel_to_snake(name)}.py",
        "editable": True,
        "updated_at": None,
        "store": "default",
        "is_default": True,
        **parent_class_info(),
    }


def resolve_source_for_instance(strategy_name: str, class_name: str) -> dict[str, Any]:
    """Instance override → class MySQL/file → default template."""
    inst = strategy_store.get_instance_source(strategy_name)
    if inst and (inst.get("content") or "").strip():
        return {
            "class_name": class_name,
            "strategy_name": strategy_name,
            "content": inst["content"],
            "file_path": inst.get("file_path") or "",
            "editable": True,
            "updated_at": inst.get("updated_at"),
            "store": "mysql_instance",
            "is_default": False,
            **parent_class_info(),
        }
    payload = resolve_source_for_class(class_name)
    payload["strategy_name"] = strategy_name
    return payload


def save_class_source(class_name: str, content: str) -> dict[str, Any]:
    """Persist to MySQL + materialize strategies/*.py."""
    name = class_name.strip()
    if not name:
        raise ValueError("class_name 不能为空")
    if not content.strip():
        raise ValueError("源码不能为空")
    # Validate compile before save
    compile_strategy_source(content, prefer_name=name)

    snake = _camel_to_snake(name)
    rel = f"strategies/{snake}.py"
    path = (_STRATEGIES_DIR / f"{snake}.py").resolve()
    _STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    meta = strategy_store.save_strategy_source(
        class_name=name,
        content=content,
        file_name=path.name,
        file_path=rel,
        module=f"strategies.{snake}",
        editable=True,
    )
    return {**meta, "file_path": rel, "store": "mysql"}


def save_instance_source(strategy_name: str, class_name: str, content: str) -> dict[str, Any]:
    """Save per-instance override + keep class table in sync for backtester class_name."""
    if not content.strip():
        raise ValueError("源码不能为空")
    compile_strategy_source(content, prefer_name=class_name.strip())
    class_meta = save_class_source(class_name, content)
    strategy_store.save_instance_source(strategy_name, content)
    return {
        **class_meta,
        "strategy_name": strategy_name,
        "store": "mysql_instance",
    }


def register_class_on_engines(cls: type, class_name: str) -> None:
    """Put compiled class onto CTA + backtester engines when available."""
    from core.runtime import runtime

    name = class_name or cls.__name__
    cta = getattr(runtime, "cta", None)
    if cta is not None and hasattr(cta, "classes"):
        cta.classes[name] = cls
    bt = getattr(runtime, "backtester", None)
    if bt is not None and hasattr(bt, "classes"):
        bt.classes[name] = cls


def ensure_class_loaded_from_db(class_name: str, *, strategy_name: str | None = None) -> type:
    """Read effective source from MySQL (instance override optional), compile, register."""
    name = class_name.strip()
    if strategy_name:
        payload = resolve_source_for_instance(strategy_name, name)
    else:
        payload = resolve_source_for_class(name)
    content = str(payload.get("content") or "")
    if not content.strip():
        raise ValueError(f"策略 {name} 无可用源码")

    # Keep disk cache aligned for folder reloaders
    if payload.get("store") in {"mysql", "mysql_instance", "default", "mysql_model"}:
        snake = _camel_to_snake(name)
        path = _STRATEGIES_DIR / f"{snake}.py"
        try:
            _STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError:
            logger.exception("materialize failed for %s", name)

    cls = compile_strategy_source(content, prefer_name=name)
    register_class_on_engines(cls, name)

    # Prefer importlib reload path when file exists (vnpy-compatible)
    _try_reload_module(name)
    register_class_on_engines(cls, name)
    return cls


def ensure_model_loaded_from_db(
    *,
    model_id: int,
    model_version_id: int | None = None,
    runtime_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load model 合约/参数/基础配置/源码 from MySQL, compile, register. Returns run context."""
    from core import model_store

    ctx = model_store.resolve_model_run_context(
        model_id,
        model_version_id=model_version_id,
        runtime_override=runtime_override,
        prefer_draft=not model_version_id,
    )
    class_name = str(ctx["class_name"])
    source = str(ctx["template_source"])

    # Persist into strategy_classes + strategies/*.py so engines stay consistent
    save_class_source(class_name, source)
    cls = compile_strategy_source(source, prefer_name=class_name)
    register_class_on_engines(cls, class_name)
    _try_reload_module(class_name)
    register_class_on_engines(cls, class_name)
    ctx["loaded_class"] = class_name
    return ctx


def rebind_live_instance(strategy_name: str, class_name: str) -> None:
    """If CTA instance exists and is stopped, recreate it with freshly loaded class."""
    from core.runtime import runtime

    engine = getattr(runtime, "cta", None)
    if engine is None:
        return
    strategy = getattr(engine, "strategies", {}).get(strategy_name)
    if strategy is None:
        return
    if getattr(strategy, "trading", False):
        logger.warning("skip rebind %s — still trading", strategy_name)
        return
    cls = engine.classes.get(class_name)
    if cls is None:
        return
    if strategy.__class__ is cls:
        return
    vt_symbol = getattr(strategy, "vt_symbol", "")
    setting = dict(strategy.get_parameters()) if hasattr(strategy, "get_parameters") else {}
    inited = bool(getattr(strategy, "inited", False))
    ok = engine.remove_strategy(strategy_name)
    if not ok:
        logger.warning("rebind remove failed %s", strategy_name)
        return
    engine.add_strategy(class_name, strategy_name, vt_symbol, setting)
    if inited and strategy_name in engine.strategies:
        try:
            engine.init_strategy(strategy_name)
        except Exception:
            logger.exception("rebind re-init failed %s", strategy_name)


def _try_reload_module(class_name: str) -> None:
    snake = _camel_to_snake(class_name)
    module_name = f"strategies.{snake}"
    try:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)
    except Exception:
        logger.debug("module reload skipped for %s", module_name, exc_info=True)


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _guess_file_path(class_name: str) -> Path:
    return (_STRATEGIES_DIR / f"{_camel_to_snake(class_name)}.py").resolve()
