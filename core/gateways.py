"""Multi-gateway account manager (docs/03)."""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Any

from vnpy.event import Event
from vnpy.trader.engine import MainEngine
from vnpy_ctp import CtpGateway

from core.channel_log import record_channel_op
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

DISCONNECTED = "DISCONNECTED"
CONNECTING = "CONNECTING"
CONNECTED = "CONNECTED"

# Auto-reconnect backoff after a real drop (not user 断开).
_RECONNECT_STEPS = (3.0, 8.0, 15.0)
_RECONNECT_CAP = 60.0

logger = logging.getLogger("stabx.gateways")


def reconnect_delay(attempt: int) -> float:
    if attempt < 0:
        attempt = 0
    if attempt < len(_RECONNECT_STEPS):
        return _RECONNECT_STEPS[attempt]
    return _RECONNECT_CAP

_TD_LOGIN_OK = ("交易服务器登录成功",)
_TD_FRONT_OK = ("交易服务器连接成功",)
_TD_DOWN = ("交易服务器连接断开", "交易服务器登录失败")
_MD_LOGIN_OK = ("行情服务器登录成功",)
_MD_FRONT_OK = ("行情服务器连接成功",)
_MD_DOWN = ("行情服务器连接断开", "行情服务器登录失败")


def _derived_conn(td: str, md: str) -> str:
    if td == CONNECTED and md == CONNECTED:
        return CONNECTED
    if td == DISCONNECTED and md == DISCONNECTED:
        return DISCONNECTED
    return CONNECTING


def _from_login_flag(current: str, logged_in: bool) -> str:
    if logged_in:
        return CONNECTED
    if current == CONNECTING:
        return CONNECTING
    if current == CONNECTED:
        return DISCONNECTED
    return current or DISCONNECTED


class AccountGatewayManager:
    """Per-channel CTP session.

    ``login_status`` / ``td_status`` / ``trade_status`` = TdApi investor login.
    ``md_status`` / ``quote_status`` = MdApi market login.
    ``conn_status`` / ``status`` is derived: CONNECTED only when both legs are up.
    """

    def __init__(self, main_engine: MainEngine) -> None:
        self.me = main_engine
        self.index: dict[str, dict[str, Any]] = {}
        self.status: dict[str, str] = {}
        self.td_status: dict[str, str] = {}
        self.md_status: dict[str, str] = {}
        self.front_info: dict[str, dict[str, Any]] = {}
        self.account_cache: dict[str, dict[str, Any]] = {}
        self._last_query: dict[str, float] = {}
        self._account_sync: set[str] = set()
        self._status_watch: set[str] = set()
        self._forced_off: set[str] = set()
        self._sync_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._keepalive_gen: dict[str, int] = {}
        self._connect_lock = threading.Lock()
        self._connect_in_flight: set[str] = set()
        self._reconnect_attempt: dict[str, int] = {}

    def load_all(self, rows: list[dict[str, Any]]) -> None:
        for acc in rows:
            if acc.get("status", 1) == 1:
                self.register(acc)

    def register(self, acc: dict[str, Any]) -> None:
        name = acc["gateway_name"]
        if name not in self.me.gateways:
            self.me.add_gateway(CtpGateway, name)
        self.index[name] = acc
        self.status.setdefault(name, DISCONNECTED)
        self.td_status.setdefault(name, DISCONNECTED)
        self.md_status.setdefault(name, DISCONNECTED)

    def connect(self, gateway_name: str, *, from_user: bool = True) -> dict[str, Any]:
        acc = self.index[gateway_name]
        setting = merge_connect_settings(decrypt(acc["connect_settings"]))
        setting, meta = apply_simnow_auto_fronts(setting)
        self.front_info[gateway_name] = meta
        if from_user:
            self._forced_off.discard(gateway_name)
        elif gateway_name in self._forced_off:
            return meta
        if not str(setting.get("密码") or "").strip():
            logger.info("skip connect %s: no password", gateway_name)
            return meta
        if not from_user and not self._native_session_dropped(gateway_name):
            logger.info(
                "skip reconnect %s: native MdApi/TdApi login_status still true "
                "(Darwin/SimNow session can stay sticky after a disconnect flag; "
                "do not call exit()/close())",
                gateway_name,
            )
            return meta
        with self._connect_lock:
            if gateway_name in self._connect_in_flight:
                return meta
            self._connect_in_flight.add(gateway_name)
        try:
            self._set_leg(gateway_name, td=CONNECTING, md=CONNECTING, publish=True)
            # Darwin: never TdApi/MdApi.exit()/close(); vnpy reconnect is me.connect() only.
            self.me.connect(ctp_connect_payload(setting), gateway_name)
            self.start_status_watch(gateway_name)
            self.start_account_sync(gateway_name)
            if self._auto_connect_enabled(gateway_name):
                self.start_keepalive(gateway_name)
            if not from_user:
                acc_id = acc.get("id")
                record_channel_op(
                    account_id=int(acc_id) if acc_id is not None else None,
                    gateway_name=gateway_name,
                    action="连接",
                    result="success",
                    message="启动自动连接" if self._auto_connect_enabled(gateway_name) else "自动重连",
                    operator_name="系统",
                )
        finally:
            def _clear() -> None:
                time.sleep(2.0)
                with self._connect_lock:
                    self._connect_in_flight.discard(gateway_name)

            threading.Thread(target=_clear, daemon=True, name=f"connect-gate-{gateway_name}").start()
        return meta

    def disconnect(self, gateway_name: str) -> None:
        gateway = self.me.get_gateway(gateway_name)
        if gateway and sys.platform != "darwin":
            try:
                gateway.close()
            except Exception:
                pass
        # macOS + SimNow CTP 6.7.13: TdApi/MdApi.exit() segfaults the process.
        # User 断开 must not auto-reconnect until 连接 / 启动自动连接 / process restart.
        self._forced_off.add(gateway_name)
        self.stop_keepalive(gateway_name)
        self.account_cache.pop(gateway_name, None)
        with self._sync_lock:
            self._account_sync.discard(gateway_name)
        self._set_leg(gateway_name, td=DISCONNECTED, md=DISCONNECTED, publish=True)

    def test_connect(self, gateway_name: str, *, login_wait: float = 10.0) -> dict[str, Any]:
        """Probe fronts over TCP, then confirm CTP TdApi login if reachable.

        Do not call CTP ``close()`` / ``exit()`` after a successful Mac login:
        SimNow v6.7.13 native teardown segfaults the whole Python process.
        Keep the session if login succeeds.
        Account login is TdApi ``login_status``, not contract arrival.
        """
        acc = self.index.get(gateway_name)
        if acc is None:
            raise KeyError(gateway_name)
        setting = merge_connect_settings(decrypt(acc["connect_settings"]))
        setting, meta = apply_simnow_auto_fronts(setting)
        trade = probe_tcp_front(str(setting.get("交易服务器") or ""))
        market = probe_tcp_front(str(setting.get("行情服务器") or ""))
        reachable = bool(trade.get("ok") and market.get("ok"))
        self.refresh_live_status(gateway_name, publish=False)
        prev_td = self.td_status.get(gateway_name, DISCONNECTED)
        login: dict[str, Any] = {
            "attempted": False,
            "ok": False,
            "status": prev_td,
            "message": "",
        }
        if not reachable:
            login["message"] = "前置 TCP 未通，未尝试登录柜台"
        elif prev_td == CONNECTED:
            login.update(attempted=True, ok=True, status=CONNECTED, message="账号已处于登录状态，未重复登录")
            self._publish_status(gateway_name)
            self.start_status_watch(gateway_name)
            self.start_account_sync(gateway_name)
            self.publish_funds(gateway_name)
            self.refresh_account(gateway_name, wait=2.0)
        elif not str(setting.get("密码") or "").strip():
            login["message"] = "前置可连，但未保存密码，无法登录柜台"
        else:
            login["attempted"] = True
            opened_for_test = prev_td != CONNECTING
            if opened_for_test:
                self.connect(gateway_name)
            deadline = time.time() + max(1.0, login_wait)
            while time.time() < deadline:
                self.refresh_live_status(gateway_name, publish=True)
                if self.td_status.get(gateway_name) == CONNECTED:
                    login.update(ok=True, status=CONNECTED, message="柜台登录成功（TdApi 已登录）")
                    break
                time.sleep(0.35)
            if not login["ok"]:
                login["status"] = self.td_status.get(gateway_name, DISCONNECTED)
                login["message"] = (
                    "前置可连，但未在时限内确认交易账号登录。"
                    "请核账号密码；新 SimNow 账号连 7×24 可能要过若干个交易日。"
                )
            else:
                login["message"] += " 通道保持连接，可直接使用。"
                self.start_account_sync(gateway_name)
                self.refresh_account(gateway_name, wait=8.0)
        self.refresh_live_status(gateway_name, publish=True)
        statuses = self.channel_statuses(gateway_name, live=False)
        td_ok = statuses["login_status"] == CONNECTED
        md_ok = statuses["quote_status"] == CONNECTED
        ok = reachable and login["ok"]
        if ok and td_ok and md_ok:
            summary = f"联通正常 · {meta.get('front_label') or '前置'} 账号已登录 · 行情已连接"
        elif ok and td_ok:
            summary = f"账号已登录 · {meta.get('front_label') or '前置'}；行情尚未确认"
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
            **statuses,
        }

    def remove(self, gateway_name: str) -> None:
        self.disconnect(gateway_name)
        self.index.pop(gateway_name, None)
        self.status.pop(gateway_name, None)
        self.td_status.pop(gateway_name, None)
        self.md_status.pop(gateway_name, None)
        self.front_info.pop(gateway_name, None)
        self.account_cache.pop(gateway_name, None)
        self._forced_off.discard(gateway_name)
        self.stop_keepalive(gateway_name)
        self._reconnect_attempt.pop(gateway_name, None)

    def _auto_connect_enabled(self, gateway_name: str) -> bool:
        acc = self.index.get(gateway_name) or {}
        return bool(acc.get("auto_connect"))

    def _has_password(self, gateway_name: str) -> bool:
        acc = self.index.get(gateway_name)
        if not acc:
            return False
        try:
            setting = merge_connect_settings(decrypt(acc["connect_settings"]))
        except Exception:
            return False
        return bool(str(setting.get("密码") or "").strip())

    def _native_session_dropped(self, gateway_name: str) -> bool:
        """True when at least one CTP leg is really down (or APIs not built yet).

        On Darwin, a disconnect *flag* can leave MdApi/TdApi.login_status True.
        Do not call exit()/close(); only me.connect() when a login_status is gone.
        """
        td_api = self._td_api(gateway_name)
        md_api = self._md_api(gateway_name)
        if td_api is None and md_api is None:
            return True
        td_down = td_api is not None and not bool(getattr(td_api, "login_status", False))
        md_down = md_api is not None and not bool(getattr(md_api, "login_status", False))
        return td_down or md_down

    def apply_auto_connect(self, gateway_name: str, enabled: bool) -> None:
        if gateway_name in self.index:
            self.index[gateway_name]["auto_connect"] = bool(enabled)
        if not enabled:
            self.stop_keepalive(gateway_name)
            return
        self._forced_off.discard(gateway_name)
        self.start_keepalive(gateway_name)
        if self._has_password(gateway_name) and self._native_session_dropped(gateway_name):
            threading.Thread(
                target=self._safe_connect,
                args=(gateway_name, True),
                daemon=True,
                name=f"auto-connect-{gateway_name}",
            ).start()

    def kickoff_auto_connects(self) -> None:
        """Non-blocking startup: connect every auto_connect account that has a password."""
        for name, acc in list(self.index.items()):
            if not acc.get("auto_connect"):
                continue
            self.start_keepalive(name)
            if not self._has_password(name):
                logger.info("startup skip %s: auto_connect on but no password", name)
                continue
            threading.Thread(
                target=self._safe_connect,
                args=(name, False),
                daemon=True,
                name=f"startup-connect-{name}",
            ).start()

    def _safe_connect(self, gateway_name: str, from_user: bool) -> None:
        try:
            self.connect(gateway_name, from_user=from_user)
        except Exception:
            logger.exception("auto connect failed %s", gateway_name)

    def start_keepalive(self, gateway_name: str) -> None:
        if not gateway_name:
            return
        with self._sync_lock:
            gen = self._keepalive_gen.get(gateway_name, 0) + 1
            self._keepalive_gen[gateway_name] = gen
        threading.Thread(
            target=self._keepalive_loop,
            args=(gateway_name, gen),
            daemon=True,
            name=f"ctp-keepalive-{gateway_name}",
        ).start()

    def stop_keepalive(self, gateway_name: str) -> None:
        with self._sync_lock:
            self._keepalive_gen[gateway_name] = self._keepalive_gen.get(gateway_name, 0) + 1

    def _keepalive_alive(self, gateway_name: str, gen: int) -> bool:
        return self._keepalive_gen.get(gateway_name) == gen

    def _sleep_interruptible(self, gateway_name: str, gen: int, seconds: float) -> bool:
        deadline = time.time() + max(0.0, seconds)
        while time.time() < deadline:
            if not self._keepalive_alive(gateway_name, gen) or gateway_name in self._forced_off:
                return False
            time.sleep(0.2)
        return self._keepalive_alive(gateway_name, gen) and gateway_name not in self._forced_off

    def _keepalive_loop(self, gateway_name: str, gen: int) -> None:
        connecting_since: float | None = None
        while self._keepalive_alive(gateway_name, gen):
            if gateway_name in self._forced_off or not self._auto_connect_enabled(gateway_name):
                return
            self.refresh_live_status(gateway_name, publish=True)
            td = self.td_status.get(gateway_name, DISCONNECTED)
            md = self.md_status.get(gateway_name, DISCONNECTED)
            if td == CONNECTED and md == CONNECTED:
                self._reconnect_attempt[gateway_name] = 0
                connecting_since = None
                if not self._sleep_interruptible(gateway_name, gen, 2.0):
                    return
                continue
            if td == CONNECTING or md == CONNECTING:
                if connecting_since is None:
                    connecting_since = time.time()
                if time.time() - connecting_since < 45.0:
                    if not self._sleep_interruptible(gateway_name, gen, 1.0):
                        return
                    continue
            connecting_since = None
            if not self._has_password(gateway_name):
                if not self._sleep_interruptible(gateway_name, gen, 5.0):
                    return
                continue
            if not self._native_session_dropped(gateway_name):
                if not self._sleep_interruptible(gateway_name, gen, 2.0):
                    return
                continue
            attempt = self._reconnect_attempt.get(gateway_name, 0)
            delay = reconnect_delay(attempt)
            logger.info("auto reconnect %s in %.0fs (attempt %s)", gateway_name, delay, attempt + 1)
            if not self._sleep_interruptible(gateway_name, gen, delay):
                return
            if gateway_name in self._forced_off or not self._auto_connect_enabled(gateway_name):
                return
            if not self._native_session_dropped(gateway_name):
                continue
            self._reconnect_attempt[gateway_name] = attempt + 1
            self._safe_connect(gateway_name, False)
            connecting_since = time.time()

    def gateway_for_user(self, user_id: int) -> list[str]:
        return [gw for gw, acc in self.index.items() if acc["user_id"] == user_id]

    def user_of(self, gateway_name: str) -> int | None:
        acc = self.index.get(gateway_name)
        return None if acc is None else int(acc["user_id"])

    def mark_connected(self, gateway_name: str) -> None:
        """Backward compat: only marks trading-account login, not market."""
        self.mark_td_connected(gateway_name)

    def mark_td_connected(self, gateway_name: str) -> None:
        if gateway_name in self._forced_off:
            return
        self._set_leg(gateway_name, td=CONNECTED, publish=True)

    def mark_md_connected(self, gateway_name: str) -> None:
        if gateway_name in self._forced_off:
            return
        self._set_leg(gateway_name, md=CONNECTED, publish=True)

    def is_td_connected(self, gateway_name: str) -> bool:
        return self.td_status.get(gateway_name) == CONNECTED

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

    def _md_api(self, gateway_name: str) -> Any:
        gateway = self.me.get_gateway(gateway_name)
        return None if gateway is None else getattr(gateway, "md_api", None)

    def can_query_account(self, gateway_name: str) -> bool:
        """CTP rejects qryTradingAccount while reqQryInstrument is in flight."""
        if gateway_name in self._forced_off:
            return False
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
        if not gateway_name or gateway_name in self._forced_off:
            return
        if self.td_status.get(gateway_name) == DISCONNECTED:
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
                if gateway_name in self._forced_off or self.td_status.get(gateway_name) == DISCONNECTED:
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

    def start_status_watch(self, gateway_name: str) -> None:
        if not gateway_name:
            return
        with self._sync_lock:
            if gateway_name in self._status_watch:
                return
            self._status_watch.add(gateway_name)
        thread = threading.Thread(
            target=self._watch_status_loop,
            args=(gateway_name,),
            daemon=True,
            name=f"status-watch-{gateway_name}",
        )
        thread.start()

    def _watch_status_loop(self, gateway_name: str) -> None:
        try:
            deadline = time.time() + 45.0
            while time.time() < deadline:
                if gateway_name in self._forced_off:
                    return
                self.refresh_live_status(gateway_name, publish=True)
                if (
                    self.td_status.get(gateway_name) == CONNECTED
                    and self.md_status.get(gateway_name) == CONNECTED
                ):
                    return
                time.sleep(0.4)
        finally:
            with self._sync_lock:
                self._status_watch.discard(gateway_name)

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

    def refresh_live_status(self, gateway_name: str, *, publish: bool = True) -> bool:
        """Sync td/md from CtpTdApi / CtpMdApi ``login_status`` flags.

        Missing API objects must not be treated as logged-out (they are often
        not constructed yet). TCP reachability is never used here.
        """
        if not gateway_name or gateway_name in self._forced_off:
            return False
        td_api = self._td_api(gateway_name)
        md_api = self._md_api(gateway_name)
        td = self.td_status.get(gateway_name, DISCONNECTED)
        md = self.md_status.get(gateway_name, DISCONNECTED)
        if td_api is not None:
            td = _from_login_flag(td, bool(getattr(td_api, "login_status", False)))
        if md_api is not None:
            md = _from_login_flag(md, bool(getattr(md_api, "login_status", False)))
        return self._set_leg(gateway_name, td=td, md=md, publish=publish)

    def note_market_event(self, gateway_name: str, *, from_tick: bool = False) -> None:
        """EVENT_TICK ≈ md login; EVENT_CONTRACT refreshes flags (TdApi qry)."""
        if not gateway_name or gateway_name in self._forced_off:
            return
        if from_tick:
            if self.md_status.get(gateway_name) == CONNECTED:
                return
            self.mark_md_connected(gateway_name)
            return
        if (
            self.td_status.get(gateway_name) == CONNECTED
            and self.md_status.get(gateway_name) == CONNECTED
        ):
            return
        self.refresh_live_status(gateway_name, publish=True)

    def apply_log_status(self, gateway_name: str, msg: str) -> None:
        if not gateway_name or gateway_name in self._forced_off or not msg:
            return
        td: str | None = None
        md: str | None = None
        if any(token in msg for token in _TD_LOGIN_OK):
            td = CONNECTED
        elif any(token in msg for token in _TD_DOWN):
            td = DISCONNECTED
        elif any(token in msg for token in _TD_FRONT_OK):
            if self.td_status.get(gateway_name) != CONNECTED:
                td = CONNECTING
        if any(token in msg for token in _MD_LOGIN_OK):
            md = CONNECTED
        elif any(token in msg for token in _MD_DOWN):
            md = DISCONNECTED
        elif any(token in msg for token in _MD_FRONT_OK):
            if self.md_status.get(gateway_name) != CONNECTED:
                md = CONNECTING
        if td is not None or md is not None:
            self._set_leg(gateway_name, td=td, md=md, publish=True)

    def channel_statuses(self, gateway_name: str, *, live: bool = True) -> dict[str, str]:
        if live:
            self.refresh_live_status(gateway_name, publish=False)
        td = self.td_status.get(gateway_name, DISCONNECTED)
        md = self.md_status.get(gateway_name, DISCONNECTED)
        conn = _derived_conn(td, md)
        self.status[gateway_name] = conn
        return {
            "td_status": td,
            "login_status": td,
            "trade_status": td,
            "md_status": md,
            "quote_status": md,
            "conn_status": conn,
            "status": conn,
        }

    def status_payload(self, gateway_name: str, *, live: bool = False) -> dict[str, Any]:
        statuses = self.channel_statuses(gateway_name, live=live)
        acc = self.index.get(gateway_name) or {}
        return {
            "gateway_name": gateway_name,
            "account_name": acc.get("account_name") or "",
            "id": acc.get("id"),
            "auto_connect": bool(acc.get("auto_connect")),
            **statuses,
        }

    def statuses_for(self, gateway_names: set[str] | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in self.index:
            if gateway_names is not None and name not in gateway_names:
                continue
            rows.append(self.status_payload(name, live=True))
        return rows

    def workbench_snapshot(self, gateway_names: set[str] | None = None) -> dict[str, Any]:
        return {
            "gateways": self.statuses_for(gateway_names),
            "accounts": self.funds_for(gateway_names),
        }

    def _set_leg(
        self,
        gateway_name: str,
        *,
        td: str | None = None,
        md: str | None = None,
        publish: bool = True,
    ) -> bool:
        with self._status_lock:
            changed, prev_td, prev_md = self._apply_leg_unlocked(
                gateway_name, td=td, md=md, publish=publish
            )
        if changed:
            self._log_leg_change(gateway_name, prev_td=prev_td, prev_md=prev_md)
        return changed

    def _apply_leg_unlocked(
        self,
        gateway_name: str,
        *,
        td: str | None = None,
        md: str | None = None,
        publish: bool = True,
    ) -> tuple[bool, str | None, str | None]:
        changed = False
        prev_td = self.td_status.get(gateway_name)
        prev_md = self.md_status.get(gateway_name)
        if td is not None and self.td_status.get(gateway_name) != td:
            self.td_status[gateway_name] = td
            changed = True
        elif td is not None:
            self.td_status.setdefault(gateway_name, td)
        if md is not None and self.md_status.get(gateway_name) != md:
            self.md_status[gateway_name] = md
            changed = True
        elif md is not None:
            self.md_status.setdefault(gateway_name, md)
        derived = _derived_conn(
            self.td_status.get(gateway_name, DISCONNECTED),
            self.md_status.get(gateway_name, DISCONNECTED),
        )
        if self.status.get(gateway_name) != derived:
            self.status[gateway_name] = derived
            changed = True
        if changed and publish:
            self._publish_status(gateway_name)
        return changed, prev_td, prev_md

    def _log_leg_change(self, gateway_name: str, *, prev_td: str | None, prev_md: str | None) -> None:
        if gateway_name in self._forced_off:
            return
        acc = self.index.get(gateway_name) or {}
        acc_id = acc.get("id")
        account_id = int(acc_id) if acc_id is not None else None
        td = self.td_status.get(gateway_name)
        md = self.md_status.get(gateway_name)
        if td is not None and td != prev_td and td in (CONNECTED, DISCONNECTED):
            record_channel_op(
                account_id=account_id,
                gateway_name=gateway_name,
                action="交易连接",
                result="success" if td == CONNECTED else "fail",
                message="交易服务器登录成功" if td == CONNECTED else "交易服务器连接断开或登录失败",
                operator_name="系统",
            )
        if md is not None and md != prev_md and md in (CONNECTED, DISCONNECTED):
            record_channel_op(
                account_id=account_id,
                gateway_name=gateway_name,
                action="行情连接",
                result="success" if md == CONNECTED else "fail",
                message="行情服务器登录成功" if md == CONNECTED else "行情服务器连接断开或登录失败",
                operator_name="系统",
            )
            try:
                from features.market.subscriptions import clear_restored, restore_gateway_subscriptions

                if md == CONNECTED:
                    restore_gateway_subscriptions(gateway_name)
                else:
                    clear_restored(gateway_name)
            except Exception:
                logger.exception("market subscription restore failed for %s", gateway_name)

    def _publish_status(self, gateway_name: str) -> None:
        publish_threadsafe(envelope("gateway", self.status_payload(gateway_name)))
