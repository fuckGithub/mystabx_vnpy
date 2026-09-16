"""vnpy objects → JSON envelope payloads (docs/04)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

SHANGHAI = timezone(timedelta(hours=8))

_STATUS_OUT = {
    "NOTTRADED": "NOT_TRADED",
    "PARTTRADED": "PART_TRADED",
    "ALLTRADED": "ALL_TRADED",
}


def dt_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=SHANGHAI)
    return value.isoformat(timespec="milliseconds")


def enum_out(value: Any) -> str | None:
    if value is None:
        return None
    name = value.name if isinstance(value, Enum) else str(value)
    return _STATUS_OUT.get(name, name)


def envelope(msg_type: str, data: dict) -> dict:
    return {
        "type": msg_type,
        "ts": int(datetime.now(tz=SHANGHAI).timestamp() * 1000),
        "data": data,
    }


def tick_payload(tick) -> dict:
    return {
        "symbol": tick.symbol,
        "exchange": enum_out(tick.exchange),
        "datetime": dt_iso(tick.datetime),
        "name": tick.name,
        "last_price": tick.last_price,
        "last_volume": tick.last_volume,
        "volume": tick.volume,
        "turnover": tick.turnover,
        "open_interest": tick.open_interest,
        "open_price": tick.open_price,
        "high_price": tick.high_price,
        "low_price": tick.low_price,
        "pre_close": tick.pre_close,
        "limit_up": tick.limit_up,
        "limit_down": tick.limit_down,
        "bid_price_1": tick.bid_price_1,
        "bid_volume_1": tick.bid_volume_1,
        "ask_price_1": tick.ask_price_1,
        "ask_volume_1": tick.ask_volume_1,
        "bid_price_2": tick.bid_price_2,
        "bid_volume_2": tick.bid_volume_2,
        "ask_price_2": tick.ask_price_2,
        "ask_volume_2": tick.ask_volume_2,
        "bid_price_3": tick.bid_price_3,
        "bid_volume_3": tick.bid_volume_3,
        "ask_price_3": tick.ask_price_3,
        "ask_volume_3": tick.ask_volume_3,
        "bid_price_4": tick.bid_price_4,
        "bid_volume_4": tick.bid_volume_4,
        "ask_price_4": tick.ask_price_4,
        "ask_volume_4": tick.ask_volume_4,
        "bid_price_5": tick.bid_price_5,
        "bid_volume_5": tick.bid_volume_5,
        "ask_price_5": tick.ask_price_5,
        "ask_volume_5": tick.ask_volume_5,
        "gateway_name": tick.gateway_name,
    }


def order_payload(order) -> dict:
    return {
        "symbol": order.symbol,
        "exchange": enum_out(order.exchange),
        "orderid": order.orderid,
        "vt_orderid": getattr(order, "vt_orderid", ""),
        "type": enum_out(order.type),
        "direction": enum_out(order.direction),
        "offset": enum_out(order.offset),
        "price": order.price,
        "volume": order.volume,
        "traded": order.traded,
        "status": enum_out(order.status),
        "datetime": dt_iso(order.datetime),
        "reference": order.reference,
        "gateway_name": order.gateway_name,
    }


def trade_payload(trade) -> dict:
    return {
        "symbol": trade.symbol,
        "exchange": enum_out(trade.exchange),
        "orderid": trade.orderid,
        "tradeid": trade.tradeid,
        "direction": enum_out(trade.direction),
        "offset": enum_out(trade.offset),
        "price": trade.price,
        "volume": trade.volume,
        "datetime": dt_iso(trade.datetime),
        "gateway_name": trade.gateway_name,
    }


def position_payload(pos) -> dict:
    return {
        "symbol": pos.symbol,
        "exchange": enum_out(pos.exchange),
        "direction": enum_out(pos.direction),
        "volume": pos.volume,
        "frozen": pos.frozen,
        "price": pos.price,
        "pnl": pos.pnl,
        "yd_volume": pos.yd_volume,
        "gateway_name": pos.gateway_name,
    }


def account_payload(account) -> dict:
    balance = float(getattr(account, "balance", 0) or 0)
    frozen = float(getattr(account, "frozen", 0) or 0)
    available = float(getattr(account, "available", balance - frozen))
    extra = getattr(account, "extra", None) or {}
    margin = extra.get("margin")
    if margin is None:
        margin = max(0.0, balance - available)
    close_profit = extra.get("close_profit")
    position_profit = extra.get("position_profit")
    pre_balance = extra.get("pre_balance")
    return {
        "accountid": account.accountid,
        "balance": balance,
        "frozen": frozen,
        "available": available,
        "margin": margin,
        "close_profit": close_profit,
        "position_profit": position_profit,
        "pre_balance": pre_balance,
        "gateway_name": account.gateway_name,
    }


def contract_payload(contract) -> dict:
    return {
        "symbol": contract.symbol,
        "exchange": enum_out(contract.exchange),
        "name": contract.name,
        "product": enum_out(getattr(contract, "product", None)),
        "size": contract.size,
        "pricetick": contract.pricetick,
        "min_volume": contract.min_volume,
        "gateway_name": contract.gateway_name,
        "vt_symbol": getattr(contract, "vt_symbol", f"{contract.symbol}.{enum_out(contract.exchange)}"),
    }


def log_payload(log) -> dict:
    level = getattr(log, "level", 20)
    names = {10: "debug", 20: "info", 30: "warning", 40: "error", 50: "critical"}
    return {
        "level": names.get(int(level), str(level)),
        "msg": log.msg,
        "time": dt_iso(getattr(log, "time", None)),
        "gateway_name": getattr(log, "gateway_name", "") or None,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return enum_out(value)
    if isinstance(value, datetime):
        return dt_iso(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def cta_strategy_payload(strategy_or_data) -> dict:
    """Serialize CTA strategy instance or EVENT_CTA_STRATEGY dict."""
    if isinstance(strategy_or_data, dict):
        data = dict(strategy_or_data)
        parameters = dict(data.get("parameters") or {})
        variables = dict(data.get("variables") or {}) if isinstance(data.get("variables"), dict) else {}
        gateway_name = parameters.get("gateway_name") or data.get("gateway_name") or ""
        return {
            "strategy_name": data.get("strategy_name", ""),
            "vt_symbol": data.get("vt_symbol", ""),
            "class_name": data.get("class_name", ""),
            "author": data.get("author", ""),
            "parameters": _jsonable(parameters),
            "variables": _jsonable(variables),
            "inited": bool(variables.get("inited", data.get("inited", False))),
            "trading": bool(variables.get("trading", data.get("trading", False))),
            "pos": variables.get("pos", data.get("pos", 0)),
            "gateway_name": gateway_name or None,
        }

    strategy = strategy_or_data
    parameters = dict(strategy.get_parameters()) if hasattr(strategy, "get_parameters") else {}
    variables = dict(strategy.get_variables()) if hasattr(strategy, "get_variables") else {}
    setting_gw = str(parameters.get("gateway_name") or "")
    return {
        "strategy_name": getattr(strategy, "strategy_name", ""),
        "vt_symbol": getattr(strategy, "vt_symbol", ""),
        "class_name": strategy.__class__.__name__,
        "author": getattr(strategy, "author", ""),
        "parameters": _jsonable(parameters),
        "variables": _jsonable(variables),
        "inited": bool(getattr(strategy, "inited", False)),
        "trading": bool(getattr(strategy, "trading", False)),
        "pos": getattr(strategy, "pos", 0),
        "gateway_name": setting_gw or None,
    }


def cta_stop_order_payload(stop_order) -> dict:
    status = getattr(stop_order, "status", None)
    status_name = enum_out(status) if status is not None else None
    # Open-source enum values are localized Chinese; normalize for UI.
    status_map = {
        "WAITING": "WAITING",
        "TRIGGERED": "TRIGGERED",
        "CANCELLED": "CANCELLED",
        "等待中": "WAITING",
        "已触发": "TRIGGERED",
        "已撤销": "CANCELLED",
    }
    return {
        "stop_orderid": getattr(stop_order, "stop_orderid", ""),
        "vt_symbol": getattr(stop_order, "vt_symbol", ""),
        "direction": enum_out(getattr(stop_order, "direction", None)),
        "offset": enum_out(getattr(stop_order, "offset", None)),
        "price": getattr(stop_order, "price", 0),
        "volume": getattr(stop_order, "volume", 0),
        "status": status_map.get(str(status_name or ""), status_name),
        "strategy_name": getattr(stop_order, "strategy_name", ""),
        "vt_orderids": list(getattr(stop_order, "vt_orderids", None) or []),
        "datetime": dt_iso(getattr(stop_order, "datetime", None)),
    }


def backtester_log_payload(log) -> dict:
    return log_payload(log)


def backtester_finished_payload(data: Any = None) -> dict:
    return data if isinstance(data, dict) else {}
