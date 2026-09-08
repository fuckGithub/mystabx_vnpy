"""Multi-gateway account manager (docs/03)."""

from __future__ import annotations

import time
from typing import Any

from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from core.crypto import decrypt
from mystabx.config.simnow import (
    apply_simnow_auto_fronts,
    ctp_connect_payload,
    merge_connect_settings,
    probe_tcp_front,
)


class AccountGatewayManager:
    def __init__(self, main_engine: MainEngine) -> None:
        self.me = main_engine
        self.index: dict[str, dict[str, Any]] = {}
        self.status: dict[str, str] = {}
        self.front_info: dict[str, dict[str, Any]] = {}

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

    def connect(self, gateway_name: str) -> dict[str, Any]:
        acc = self.index[gateway_name]
        setting = merge_connect_settings(decrypt(acc["connect_settings"]))
        setting, meta = apply_simnow_auto_fronts(setting)
        self.front_info[gateway_name] = meta
        self.status[gateway_name] = "CONNECTING"
        self.me.connect(ctp_connect_payload(setting), gateway_name)
        return meta

    def disconnect(self, gateway_name: str) -> None:
        gateway = self.me.get_gateway(gateway_name)
        if gateway:
            try:
                gateway.close()
            except Exception:
                # CTP close can raise after a successful login; status still drops.
                pass
        self.status[gateway_name] = "DISCONNECTED"

    def test_connect(self, gateway_name: str, *, login_wait: float = 10.0) -> dict[str, Any]:
        """Probe fronts over TCP, then confirm CTP login if reachable.

        Does not leave a newly opened session behind: if the channel was not
        already CONNECTED, disconnect after the probe.
        """
        acc = self.index.get(gateway_name)
        if acc is None:
            raise KeyError(gateway_name)
        setting = merge_connect_settings(decrypt(acc["connect_settings"]))
        setting, meta = apply_simnow_auto_fronts(setting)
        trade = probe_tcp_front(str(setting.get("交易服务器") or ""))
        market = probe_tcp_front(str(setting.get("行情服务器") or ""))
        reachable = bool(trade.get("ok") and market.get("ok"))
        prev = self.status.get(gateway_name, "DISCONNECTED")
        login: dict[str, Any] = {
            "attempted": False,
            "ok": False,
            "status": prev,
            "message": "",
        }
        if not reachable:
            login["message"] = "前置 TCP 未通，未尝试登录柜台"
        elif prev == "CONNECTED":
            login.update(attempted=True, ok=True, status="CONNECTED", message="通道已处于已连接，未重复登录")
        elif not str(setting.get("密码") or "").strip():
            login["message"] = "前置可连，但未保存密码，无法登录柜台"
        else:
            login["attempted"] = True
            opened_for_test = prev != "CONNECTING"
            if opened_for_test:
                self.connect(gateway_name)
            deadline = time.time() + max(1.0, login_wait)
            while time.time() < deadline:
                if self.status.get(gateway_name) == "CONNECTED":
                    login.update(ok=True, status="CONNECTED", message="柜台登录成功（已收到账户或合约回报）")
                    break
                time.sleep(0.35)
            if not login["ok"]:
                login["status"] = self.status.get(gateway_name, "DISCONNECTED")
                login["message"] = (
                    "前置可连，但未在时限内收到登录确认。"
                    "请核账号密码；新 SimNow 账号连 7×24 可能要过若干个交易日。"
                )
            if opened_for_test:
                try:
                    self.disconnect(gateway_name)
                    if login["ok"]:
                        login["message"] += " 测试结束已断开，正式使用请再点连接。"
                    else:
                        login["status"] = "DISCONNECTED"
                except Exception as exc:
                    login["message"] = (
                        (login["message"] + " ").strip()
                        + f"登录结果已确认，但断开测试连接时异常：{exc}"
                    )
        ok = reachable and login["ok"]
        if ok:
            summary = f"联通正常 · {meta.get('front_label') or '前置'} 登录已确认"
        elif reachable:
            summary = login["message"] or "前置可连，柜台登录未确认"
        else:
            failed = []
            if not trade.get("ok"):
                failed.append(f"交易 {trade.get('address') or '—'}")
            if not market.get("ok"):
                failed.append(f"行情 {market.get('address') or '—'}")
            summary = "前置不可达：" + "；".join(failed)
        return {
            "ok": ok,
            "reachable": reachable,
            "summary": summary,
            "gateway_name": gateway_name,
            "front_env": meta.get("front_env"),
            "front_label": meta.get("front_label"),
            "auto_front": meta.get("auto_front"),
            "trade": trade,
            "market": market,
            "login": login,
        }

    def remove(self, gateway_name: str) -> None:
        self.disconnect(gateway_name)
        self.index.pop(gateway_name, None)
        self.status.pop(gateway_name, None)
        self.front_info.pop(gateway_name, None)

    def gateway_for_user(self, user_id: int) -> list[str]:
        return [gw for gw, acc in self.index.items() if acc["user_id"] == user_id]

    def user_of(self, gateway_name: str) -> int | None:
        acc = self.index.get(gateway_name)
        return None if acc is None else int(acc["user_id"])

    def mark_connected(self, gateway_name: str) -> None:
        if gateway_name in self.status and self.status[gateway_name] != "CONNECTED":
            self.status[gateway_name] = "CONNECTED"
