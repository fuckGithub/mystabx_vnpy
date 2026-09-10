"""Product entry: exec ./start.sh (Vue web trader). Same as `uv run start`.

`python main.py` and IDE Run on this file start the Web trader (not Qt).
Args pass through to start.sh: --dev, --skip-build, --help.
Legacy Qt desktop only with explicit --qt.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)


def _run_legacy_qt() -> None:
    from mystabx.paths import ensure_project_trader_dir

    ensure_project_trader_dir()

    from vnpy.trader.ui import create_qapp

    from mystabx.trader import build_engines
    from mystabx.ui.connect import ensure_simnow_connect_template
    from mystabx.ui.main_window import build_main_window
    from mystabx.ui.theme import apply_mac_settings

    apply_mac_settings()
    ensure_simnow_connect_template()

    qapp = create_qapp("Stabx Trader")
    main_engine, event_engine = build_engines()
    main_window = build_main_window(main_engine, event_engine)
    main_window.showMaximized()
    qapp.exec()


def main() -> None:
    if "--qt" in sys.argv[1:]:
        sys.argv = [sys.argv[0], *[a for a in sys.argv[1:] if a != "--qt"]]
        _run_legacy_qt()
        return

    from core.start import main as start_main

    start_main()


if __name__ == "__main__":
    main()
