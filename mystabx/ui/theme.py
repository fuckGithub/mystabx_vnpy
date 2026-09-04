"""Mac UI theme: PingFang + larger size. qdarkstyle is applied by create_qapp."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MAC_FONT_FAMILY = "PingFang SC"
MAC_FONT_SIZE = 14


def apply_mac_settings() -> None:
    """Override vnpy SETTINGS before create_qapp so cocoa uses a real Mac font."""
    from vnpy.trader.setting import SETTINGS
    from vnpy.trader.utility import get_file_path

    if sys.platform == "darwin":
        current = SETTINGS.get("font.family", "")
        if current in ("", "微软雅黑", "Microsoft YaHei"):
            SETTINGS["font.family"] = MAC_FONT_FAMILY
        if int(SETTINGS.get("font.size", 12)) < MAC_FONT_SIZE:
            SETTINGS["font.size"] = MAC_FONT_SIZE

    _use_local_datafeed()
    _persist_local_settings(get_file_path("vt_setting.json"))


def _use_local_datafeed() -> None:
    """SimNow / P0: sqlite + empty datafeed. Do not require RQData."""
    from vnpy.trader import datafeed as datafeed_mod
    from vnpy.trader.setting import SETTINGS

    SETTINGS["datafeed.name"] = str(SETTINGS.get("datafeed.name", "") or "")
    SETTINGS.setdefault("datafeed.username", "")
    SETTINGS.setdefault("datafeed.password", "")
    if SETTINGS["datafeed.name"]:
        return
    if datafeed_mod.datafeed is None:
        datafeed_mod.datafeed = datafeed_mod.BaseDatafeed()


def _persist_local_settings(setting_path: Path) -> None:
    from vnpy.trader.setting import SETTINGS

    data: dict = {}
    if setting_path.exists():
        try:
            data = json.loads(setting_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}

    changed = False
    family = data.get("font.family", "")
    if family in ("", "微软雅黑", "Microsoft YaHei"):
        data["font.family"] = SETTINGS["font.family"]
        data["font.size"] = SETTINGS["font.size"]
        changed = True

    # Empty name = optional / offline. Never seed commercial credentials.
    if "datafeed.name" not in data:
        data["datafeed.name"] = ""
        changed = True

    if changed:
        setting_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=4),
            encoding="utf-8",
        )
