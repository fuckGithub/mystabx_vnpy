"""SSE hub: snapshot + live gateway/account streams for the workbench."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

SSE_TYPES = frozenset({"gateway", "account"})


def format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@dataclass
class SseClient:
    user_id: int
    is_admin: bool
    gateways: set[str]
    queue: asyncio.Queue[dict | None] = field(default_factory=lambda: asyncio.Queue(maxsize=256))


class SseHub:
    def __init__(self) -> None:
        self.clients: list[SseClient] = []

    def register(self, client: SseClient) -> None:
        self.clients.append(client)

    def remove(self, client: SseClient) -> None:
        self.clients = [c for c in self.clients if c is not client]

    def _visible(self, client: SseClient, gateway_name: str | None) -> bool:
        if gateway_name is None:
            return True
        if client.is_admin:
            return True
        return gateway_name in client.gateways

    def push(self, msg: dict) -> None:
        msg_type = msg.get("type")
        if msg_type not in SSE_TYPES:
            return
        data = msg.get("data") or {}
        gateway_name = data.get("gateway_name")
        stale: list[SseClient] = []
        for client in list(self.clients):
            if not self._visible(client, gateway_name):
                continue
            try:
                client.queue.put_nowait(msg)
            except asyncio.QueueFull:
                stale.append(client)
        for client in stale:
            self.remove(client)
            try:
                client.queue.put_nowait(None)
            except Exception:
                pass

    def snapshot_counts(self) -> dict[str, int]:
        return {"connections": len(self.clients)}


sse_hub = SseHub()
