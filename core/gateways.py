"""Multi-gateway account manager (docs/03)."""

from __future__ import annotations

from typing import Any

from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from core.crypto import decrypt
from mystabx.config.simnow import SIMNOW_CONNECT_DEFAULTS


class AccountGatewayManager:
    def __init__(self, main_engine: MainEngine) -> None:
        self.me = main_engine
        self.index: dict[str, dict[str, Any]] = {}
        self.status: dict[str, str] = {}

    def load_all(self, rows: list[dict[str, Any]]) -> None:
        for acc in rows:
            if acc.get("status", 1) == 1:
                self.register(acc)

    def register(self, acc: dict[str, Any]) -> None:
        name = acc["gateway_name"]
        if name not in self.me.gateways:
            self.me.add_gateway(CtpGateway, name)
        self.index[name] = acc
        self.status.setdefault(name, "DISCONNECTED")

    def connect(self, gateway_name: str) -> None:
        acc = self.index[gateway_name]
        setting = dict(SIMNOW_CONNECT_DEFAULTS)
        setting.update(decrypt(acc["connect_settings"]))
        self.status[gateway_name] = "CONNECTING"
        self.me.connect(setting, gateway_name)

    def disconnect(self, gateway_name: str) -> None:
        gateway = self.me.get_gateway(gateway_name)
        if gateway:
            gateway.close()
        self.status[gateway_name] = "DISCONNECTED"

    def remove(self, gateway_name: str) -> None:
        self.disconnect(gateway_name)
        self.index.pop(gateway_name, None)
        self.status.pop(gateway_name, None)

    def gateway_for_user(self, user_id: int) -> list[str]:
        return [gw for gw, acc in self.index.items() if acc["user_id"] == user_id]

    def user_of(self, gateway_name: str) -> int | None:
        acc = self.index.get(gateway_name)
        return None if acc is None else int(acc["user_id"])

    def mark_connected(self, gateway_name: str) -> None:
        if gateway_name in self.status and self.status[gateway_name] != "CONNECTED":
            self.status[gateway_name] = "CONNECTED"
