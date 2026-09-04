"""Stabx Trader entry. Start this yourself in PyCharm; the agent will not launch it."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from mystabx.paths import ensure_project_trader_dir

ensure_project_trader_dir()


def main() -> None:
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


if __name__ == "__main__":
    main()
