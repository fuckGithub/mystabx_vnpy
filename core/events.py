"""Forward vnpy EventEngine events to the WebSocket hub (docs/06 B9)."""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.event import (
    EVENT_ACCOUNT,
    EVENT_CONTRACT,
    EVENT_LOG,
    EVENT_ORDER,
    EVENT_POSITION,
    EVENT_QUOTE,
    EVENT_TICK,
    EVENT_TRADE,
)

from core.gateways import AccountGatewayManager
from core.serialize import (
    account_payload,
    contract_payload,
    envelope,
    log_payload,
    order_payload,
    position_payload,
    tick_payload,
    trade_payload,
)
from core.ws import publish_threadsafe


def _gateway_name(data) -> str | None:
    return getattr(data, "gateway_name", None)


def bind_events(event_engine: EventEngine, manager: AccountGatewayManager) -> None:
    def on_tick(event: Event) -> None:
        publish_threadsafe(envelope("tick", tick_payload(event.data)))

    def on_order(event: Event) -> None:
        publish_threadsafe(envelope("order", order_payload(event.data)))

    def on_trade(event: Event) -> None:
        publish_threadsafe(envelope("trade", trade_payload(event.data)))

    def on_position(event: Event) -> None:
        publish_threadsafe(envelope("position", position_payload(event.data)))

    def on_account(event: Event) -> None:
        payload = account_payload(event.data)
        gw = payload.get("gateway_name") or _gateway_name(event.data)
        if gw:
            manager.mark_connected(str(gw))
            manager.cache_account(payload)
            manager._publish_status(str(gw), "CONNECTED")
        publish_threadsafe(envelope("account", payload))

    def on_contract(event: Event) -> None:
        gw = _gateway_name(event.data)
        if gw:
            manager.mark_connected(gw)
        publish_threadsafe(envelope("contract", contract_payload(event.data)))

    def on_log(event: Event) -> None:
        publish_threadsafe(envelope("log", log_payload(event.data)))

    def on_quote(event: Event) -> None:
        data = event.data
        publish_threadsafe(
            envelope(
                "quote",
                {
                    "symbol": getattr(data, "symbol", ""),
                    "exchange": str(getattr(getattr(data, "exchange", None), "name", getattr(data, "exchange", ""))),
                    "gateway_name": getattr(data, "gateway_name", ""),
                },
            )
        )

    event_engine.register(EVENT_TICK, on_tick)
    event_engine.register(EVENT_ORDER, on_order)
    event_engine.register(EVENT_TRADE, on_trade)
    event_engine.register(EVENT_POSITION, on_position)
    event_engine.register(EVENT_ACCOUNT, on_account)
    event_engine.register(EVENT_CONTRACT, on_contract)
    event_engine.register(EVENT_LOG, on_log)
    event_engine.register(EVENT_QUOTE, on_quote)
