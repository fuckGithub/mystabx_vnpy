"""WebSocket hub: auth, heartbeat, topic filter (docs/04).

P1/P2 (docs/09 §8): serialize each envelope once (orjson when available);
track pending fan-out depth for P8. Routing semantics unchanged.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from core.metrics import metrics
from core.serialize import envelope

try:
    import orjson as _orjson
except ImportError:  # pragma: no cover
    _orjson = None


def _dumps_text(msg: dict) -> str:
    """One JSON encoding for all matching connections (P1)."""
    if _orjson is not None:
        return _orjson.dumps(msg).decode("utf-8")
    return json.dumps(msg, ensure_ascii=False)


@dataclass
class Connection:
    ws: WebSocket
    user_id: int
    is_admin: bool
    gateways: set[str]
    topics: set[str] = field(default_factory=set)


class WsHub:
    def __init__(self) -> None:
        self.connections: list[Connection] = []

    def register(self, conn: Connection) -> None:
        self.connections.append(conn)

    def remove(self, ws: WebSocket) -> None:
        self.connections = [c for c in self.connections if c.ws is not ws]

    def _visible(self, conn: Connection, gateway_name: str | None) -> bool:
        if gateway_name is None:
            return True
        if conn.is_admin:
            return True
        return gateway_name in conn.gateways

    def _topic_ok(self, conn: Connection, msg_type: str, data: dict) -> bool:
        if not conn.topics:
            return True
        if msg_type in conn.topics:
            return True
        symbol = data.get("symbol")
        exchange = data.get("exchange")
        if symbol and exchange and f"{msg_type}:{exchange}.{symbol}" in conn.topics:
            return True
        if symbol and exchange and f"{msg_type}:{symbol}" in conn.topics:
            return True
        return False

    async def send_envelope(self, conn: Connection, msg: dict) -> None:
        if conn.ws.client_state != WebSocketState.CONNECTED:
            return
        try:
            await conn.ws.send_text(_dumps_text(msg))
        except Exception:
            self.remove(conn.ws)

    async def route(self, msg: dict) -> None:
        data = msg.get("data") or {}
        gateway_name = data.get("gateway_name")
        msg_type = msg.get("type")
        targets: list[Connection] = []
        stale: list[WebSocket] = []
        for conn in list(self.connections):
            if not self._visible(conn, gateway_name):
                continue
            if not self._topic_ok(conn, msg_type, data):
                continue
            if conn.ws.client_state != WebSocketState.CONNECTED:
                stale.append(conn.ws)
                continue
            targets.append(conn)
        if not targets and not stale:
            return
        t0 = time.perf_counter()
        payload = _dumps_text(msg) if targets else ""
        for conn in targets:
            try:
                await conn.ws.send_text(payload)
            except Exception:
                stale.append(conn.ws)
        if targets:
            metrics.observe_ws_fanout((time.perf_counter() - t0) * 1000.0)
        for ws in stale:
            self.remove(ws)

    async def send_to_user(self, user_id: int, msg: dict) -> None:
        for conn in list(self.connections):
            if conn.user_id == user_id or conn.is_admin:
                await self.send_envelope(conn, msg)

    def snapshot_counts(self) -> dict[str, int]:
        return {"connections": len(self.connections), "pending_fanouts": metrics.ws_queue_depth()}


hub = WsHub()
_loop: asyncio.AbstractEventLoop | None = None


def set_loop(loop: asyncio.AbstractEventLoop | None) -> None:
    global _loop
    _loop = loop


async def _fanout(msg: dict) -> None:
    from core.sse import sse_hub

    try:
        await hub.route(msg)
        sse_hub.push(msg)
    finally:
        metrics.ws_fanout_end()


def publish_threadsafe(msg: dict) -> None:
    if _loop is None or not _loop.is_running():
        return
    metrics.ws_fanout_begin()
    try:
        asyncio.run_coroutine_threadsafe(_fanout(msg), _loop)
    except Exception:
        metrics.ws_fanout_end()


def pong() -> dict:
    return envelope("pong", {})
