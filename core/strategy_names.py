"""Chinese display names for CTA strategy classes (UI labels only)."""

from __future__ import annotations

import re

# Short Chinese titles by class_name. Keep in sync with built-in + project demos.
STRATEGY_TITLE_ZH: dict[str, str] = {
    "TurtleSignalStrategy": "海龟交易信号策略",
    "DualThrustStrategy": "双推力策略",
    "BollChannelStrategy": "布林带通道策略",
    "AtrRsiStrategy": "ATR-RSI策略",
    "KingKeltnerStrategy": "肯特纳通道策略",
    "MultiSignalStrategy": "多信号策略",
    "MultiTimeframeStrategy": "多周期策略",
    "TestStrategy": "测试策略",
    "DoubleMaStrategy": "双均线策略",
    "DualMaTest": "双均线测试策略",
    "RumiStrategy": "RUMI均线偏差策略",
}


def strategy_title_zh(class_name: str) -> str:
    """Return a short Chinese title; fallback keeps class_name readable."""
    name = (class_name or "").strip()
    if not name:
        return ""
    known = STRATEGY_TITLE_ZH.get(name)
    if known:
        return known
    # CamelCase → spaced words, strip trailing Strategy
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", name).strip()
    if spaced.endswith(" Strategy"):
        spaced = spaced[: -len(" Strategy")].strip()
    return f"{spaced}策略" if spaced else name


def strategy_display_name(class_name: str) -> str:
    """UI label:「中文名 (ClassName)」; unknown classes still safe."""
    name = (class_name or "").strip()
    if not name:
        return ""
    title = strategy_title_zh(name)
    if title == name:
        return name
    return f"{title} ({name})"
