"""Multi-gateway account manager (docs/03)."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any

from vnpy.event import Event
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from core.crypto import decrypt
from core.serialize import account_payload, envelope
from core.ws import publish_threadsafe
from mystabx.config.simnow import (
    apply_simnow_auto_fronts,
    ctp_connect_payload,
    merge_connect_settings,
    probe_tcp_front,
)

# Run CTP qry on EventEngine thread — TdApi is not safe from FastAPI workers.
EVENT_ENSURE_ACCOUNT = "eEnsureAccount"


class AccountGatewayManager:
    def __init__(self, main_engine: MainEngine) -> None:
        self.me = main_engine
        self.index: dict[str, dict[str, Any]] = {}
        self.status: dict[str, str] = {}
        self.front_info: dict[str, dict[str, Any]] = {}
        self.account_cache: dict[str, dict[str, Any]] = {}
        self._last_query: dict[str, float] = {}
        self._account_sync: set[str] = set()
        self._sync_lock = threading.Lock()

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
        self._publish_status(gateway_name, "CONNECTING")
        self.me.connect(ctp_connect_payload(setting), gateway_name)
        self.start_account_sync(gateway_name)
        return meta

    def disconnect(self, gateway_name: str) -> None:
        gateway = self.me.get_gateway(gateway_name)
        if gateway and sys.platform != "darwin":
            try:
                gateway.close()
            except Exception:
                pass
        # macOS + SimNow CTP 6.7.13: TdApi/MdApi.exit() segfaults the process.
        self.status[gateway_name] = "DISCONNECTED"
        self.account_cache.pop(gateway_name, None)
        with self._sync_lock:
            self._account_sync.discard(gateway_name)
        self._publish_status(gateway_name, "DISCONNECTED")

    def test_connect(self, gateway_name: str, *, login_wait: float = 10.0) -> dict[str, Any]:
        """Probe fronts over TCP, then confirm CTP login if reachable.

        Do not call CTP ``close()`` / ``exit()`` after a successful Mac login:
        SimNow v6.7.13 native teardown segfaults the whole Python process.
        Keep the session if login succeeds.
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
            self._publish_status(gateway_name, "CONNECTED")
            self.start_account_sync(gateway_name)
            self.publish_funds(gateway_name)
            self.refresh_account(gateway_name, wait=2.0)
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
            elif login["ok"]:
                login["message"] += " 通道保持连接，可直接使用。"
                self.mark_connected(gateway_name)
                self._publish_status(gateway_name, "CONNECTED")
                self.start_account_sync(gateway_name)
                self.refresh_account(gateway_name, wait=8.0)
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
            "conn_status": self.status.get(gateway_name, "DISCONNECTED"),
        }

    def remove(self, gateway_name: str) -> None:
        self.disconnect(gateway_name)
        self.index.pop(gateway_name, None)
        self.status.pop(gateway_name, None)
        self.front_info.pop(gateway_name, None)
        self.account_cache.pop(gateway_name, None)

    def gateway_for_user(self, user_id: int) -> list[str]:
        return [gw for gw, acc in self.index.items() if acc["user_id"] == user_id]

    def user_of(self, gateway_name: str) -> int | None:
        acc = self.index.get(gateway_name)
        return None if acc is None else int(acc["user_id"])

    def mark_connected(self, gateway_name: str) -> None:
        if gateway_name in self.status:
            self.status[gateway_name] = "CONNECTED"

    def cache_account(self, payload: dict[str, Any]) -> None:
        name = str(payload.get("gateway_name") or "")
        if name:
            self.account_cache[name] = payload

    def has_account(self, gateway_name: str) -> bool:
        if gateway_name in self.account_cache:
            return True
        try:
            return any(getattr(acc, "gateway_name", "") == gateway_name for acc in self.me.get_all_accounts())
        except Exception:
            return False

    def funds_for(self, gateway_names: set[str] | None = None) -> list[dict[str, Any]]:
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        names = gateway_names
        for payload in self.account_cache.values():
            gw = str(payload.get("gateway_name") or "")
            if names is not None and gw not in names:
                continue
            merged[(gw, str(payload.get("accountid") or ""))] = payload
        try:
            accounts = self.me.get_all_accounts()
        except Exception:
            accounts = []
        for account in accounts:
            gw = str(getattr(account, "gateway_name", "") or "")
            if names is not None and gw not in names:
                continue
            payload = account_payload(account)
            merged[(gw, str(payload.get("accountid") or ""))] = payload
        return list(merged.values())

    def publish_funds(self, gateway_name: str) -> None:
        for payload in self.funds_for({gateway_name}):
            publish_threadsafe(envelope("account", payload))

    def _td_api(self, gateway_name: str) -> Any:
        gateway = self.me.get_gateway(gateway_name)
        return None if gateway is None else getattr(gateway, "td_api", None)

    def can_query_account(self, gateway_name: str) -> bool:
        """CTP rejects qryTradingAccount while reqQryInstrument is in flight."""
        td = self._td_api(gateway_name)
        if td is None:
            return False
        if not getattr(td, "login_status", False):
            return False
        if hasattr(td, "contract_inited"):
            return bool(td.contract_inited)
        return True

    def query_snapshot(self, gateway_name: str) -> None:
        if not self.can_query_account(gateway_name):
            return
        gateway = self.me.get_gateway(gateway_name)
        if gateway is None:
            return
        for method in ("query_account", "query_position"):
            func = getattr(gateway, method, None)
            if callable(func):
                try:
                    func()
                except Exception:
                    pass

    def request_account_query(self, gateway_name: str) -> None:
        if not gateway_name or not self.can_query_account(gateway_name):
            return
        now = time.time()
        if now - self._last_query.get(gateway_name, 0) < 1.5:
            return
        self._last_query[gateway_name] = now
        try:
            self.me.event_engine.put(Event(EVENT_ENSURE_ACCOUNT, gateway_name))
        except Exception:
            self.query_snapshot(gateway_name)

    def start_account_sync(self, gateway_name: str) -> None:
        if not gateway_name or self.status.get(gateway_name) == "DISCONNECTED":
            return
        if self.has_account(gateway_name):
            return
        with self._sync_lock:
            if gateway_name in self._account_sync:
                return
            self._account_sync.add(gateway_name)
        thread = threading.Thread(
            target=self._sync_account_loop,
            args=(gateway_name,),
            daemon=True,
            name=f"account-sync-{gateway_name}",
        )
        thread.start()

    def _sync_account_loop(self, gateway_name: str) -> None:
        try:
            deadline = time.time() + 120.0
            while time.time() < deadline:
                if self.status.get(gateway_name) == "DISCONNECTED":
                    return
                if self.has_account(gateway_name):
                    self.publish_funds(gateway_name)
                    return
                if self.can_query_account(gateway_name):
                    self.request_account_query(gateway_name)
                time.sleep(2.0)
            if self.has_account(gateway_name):
                self.publish_funds(gateway_name)
        finally:
            with self._sync_lock:
                self._account_sync.discard(gateway_name)

    def refresh_account(self, gateway_name: str, *, wait: float = 0.0, min_interval: float = 2.0) -> None:
        self.start_account_sync(gateway_name)
        now = time.time()
        if self.can_query_account(gateway_name) and (
            wait > 0 or now - self._last_query.get(gateway_name, 0) >= min_interval
        ):
            self.request_account_query(gateway_name)
        deadline = time.time() + max(0.0, wait)
        while time.time() < deadline:
            if self.has_account(gateway_name):
                self.publish_funds(gateway_name)
                return
            time.sleep(0.3)
            if self.can_query_account(gateway_name) and time.time() + 1.2 >= deadline:
                self.request_account_query(gateway_name)

    def status_payload(self, gateway_name: str, status: str | None = None) -> dict[str, Any]:
        current = status or self.status.get(gateway_name, "DISCONNECTED")
        acc = self.index.get(gateway_name) or {}
        return {
            "gateway_name": gateway_name,
            "status": current,
            "conn_status": current,
            "account_name": acc.get("account_name") or "",
            "id": acc.get("id"),
        }

    def statuses_for(self, gateway_names: set[str] | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in self.index:
            if gateway_names is not None and name not in gateway_names:
                continue
            rows.append(self.status_payload(name))
        return rows

    def workbench_snapshot(self, gateway_names: set[str] | None = None) -> dict[str, Any]:
        return {
            "gateways": self.statuses_for(gateway_names),
            "accounts": self.funds_for(gateway_names),
        }

    def _publish_status(self, gateway_name: str, status: str | None = None) -> None:
        publish_threadsafe(envelope("gateway", self.status_payload(gateway_name, status)))
