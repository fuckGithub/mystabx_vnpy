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

from core.gateways import EVENT_ENSURE_ACCOUNT, AccountGatewayManager
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
from features.market.tick_buffer import record_tick
from features.market.tick_writer import enqueue_tick


def _gateway_name(data) -> str | None:
    return getattr(data, "gateway_name", None)


def bind_events(event_engine: EventEngine, manager: AccountGatewayManager) -> None:
    def on_tick(event: Event) -> None:
        from core.metrics import metrics, perf_counter

        t0 = perf_counter()
        tick = event.data
        gw = _gateway_name(tick)
        if gw:
            manager.note_market_event(str(gw), from_tick=True)
        payload = tick_payload(tick)
        metrics.note_tick_arrival(str(payload.get("symbol") or ""), str(payload.get("exchange") or ""))
        record_tick(payload)
        enqueue_tick(payload)
        publish_threadsafe(envelope("tick", payload))
        metrics.observe_tick_handler((perf_counter() - t0) * 1000.0)

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
            manager.mark_td_connected(str(gw))
            manager.cache_account(payload)
        publish_threadsafe(envelope("account", payload))

    def on_contract(event: Event) -> None:
        gw = _gateway_name(event.data)
        if gw:
            manager.note_market_event(str(gw), from_tick=False)
        publish_threadsafe(envelope("contract", contract_payload(event.data)))

    def on_log(event: Event) -> None:
        publish_threadsafe(envelope("log", log_payload(event.data)))
        msg = str(getattr(event.data, "msg", "") or "")
        gw = _gateway_name(event.data)
        if not gw:
            return
        manager.apply_log_status(str(gw), msg)
        if "合约信息查询成功" in msg:
            manager.start_account_sync(str(gw))
            manager.request_account_query(str(gw))

    def on_ensure_account(event: Event) -> None:
        name = event.data
        if isinstance(name, dict):
            name = name.get("gateway_name")
        if name:
            manager.query_snapshot(str(name))

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
    event_engine.register(EVENT_ENSURE_ACCOUNT, on_ensure_account)
