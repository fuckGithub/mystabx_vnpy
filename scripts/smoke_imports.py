"""Import engines and seed SimNow template. Does not open the trader window."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from mystabx.paths import ensure_project_trader_dir

ensure_project_trader_dir()

from mystabx.config.simnow import CONNECT_FILENAME, SECRET_FIELDS
from mystabx.trader import build_engines
from mystabx.ui.connect import ensure_simnow_connect_template
from mystabx.ui.theme import apply_mac_settings


def main() -> int:
    apply_mac_settings()
    path = ensure_simnow_connect_template()
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in SECRET_FIELDS:
        if data.get(field):
            print(f"local file has {field} set (not from repo)", file=sys.stderr)

    main_engine, _event_engine = build_engines()
    gateways = main_engine.get_all_gateway_names()
    apps = [app.app_name for app in main_engine.get_all_apps()]
    main_engine.close()

    print(f"gateways={gateways}")
    print(f"apps={apps}")
    print(f"connect_template={path}")
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
