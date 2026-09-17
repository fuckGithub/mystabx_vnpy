"""Persist and restore CTP market-data subscriptions (SQLite)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, select
from vnpy.trader.constant import Exchange
from vnpy.trader.object import SubscribeRequest

from core.db import MarketSubscription, get_session
from core.runtime import runtime

logger = logging.getLogger(__name__)

# Gateways whose MD login already triggered a restore in this process.
_restored_gateways: set[str] = set()


def vt_symbol_of(symbol: str, exchange: str) -> str:
    return f"{symbol}.{str(exchange).upper()}"


def subscription_to_dict(row: MarketSubscription) -> dict[str, Any]:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "gateway_name": row.gateway_name,
        "symbol": row.symbol,
        "exchange": str(row.exchange).upper(),
        "name": row.name or "",
        "vt_symbol": vt_symbol_of(row.symbol, row.exchange),
        "created_at": row.created_at,
    }


def lookup_contract_name(symbol: str, exchange: str, gateway_name: str = "") -> str | None:
    want_sym = symbol.upper()
    want_ex = exchange.upper()
    try:
        contracts = runtime.oms.get_all_contracts()
    except Exception:
        return None
    for contract in contracts:
        if str(getattr(contract, "symbol", "")).upper() != want_sym:
            continue
        ex = getattr(getattr(contract, "exchange", None), "name", str(getattr(contract, "exchange", "")))
        if str(ex).upper() != want_ex:
            continue
        if gateway_name and getattr(contract, "gateway_name", "") not in ("", gateway_name):
            continue
        name = str(getattr(contract, "name", "") or "").strip()
        if name:
            return name
    return None


def upsert_subscription(
    *,
    user_id: int,
    gateway_name: str,
    symbol: str,
    exchange: str,
    name: str | None = None,
) -> MarketSubscription:
    sym = symbol.strip()
    ex = exchange.strip().upper()
    gw = gateway_name.strip()
    resolved = (name or "").strip() or lookup_contract_name(sym, ex, gw)
    db = get_session()
    try:
        row = db.scalar(
            select(MarketSubscription).where(
                MarketSubscription.user_id == user_id,
                MarketSubscription.gateway_name == gw,
                MarketSubscription.symbol == sym,
                MarketSubscription.exchange == ex,
            )
        )
        if row is None:
            row = MarketSubscription(
                user_id=user_id,
                gateway_name=gw,
                symbol=sym,
                exchange=ex,
                name=resolved,
            )
            db.add(row)
        elif resolved and not (row.name or "").strip():
            row.name = resolved
        elif resolved:
            row.name = resolved
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


def delete_subscription(
    *,
    user_id: int,
    gateway_name: str,
    symbol: str,
    exchange: str,
) -> bool:
    sym = symbol.strip()
    ex = exchange.strip().upper()
    gw = gateway_name.strip()
    db = get_session()
    try:
        result = db.execute(
            delete(MarketSubscription).where(
                MarketSubscription.user_id == user_id,
                MarketSubscription.gateway_name == gw,
                MarketSubscription.symbol == sym,
                MarketSubscription.exchange == ex,
            )
        )
        db.commit()
        return bool(result.rowcount)
    finally:
        db.close()


def list_user_subscriptions(user_id: int, *, gateway_names: set[str] | None = None) -> list[dict[str, Any]]:
    db = get_session()
    try:
        stmt = select(MarketSubscription).where(MarketSubscription.user_id == user_id)
        if gateway_names is not None:
            stmt = stmt.where(MarketSubscription.gateway_name.in_(gateway_names))
        rows = list(db.scalars(stmt.order_by(MarketSubscription.id)))
        return [subscription_to_dict(row) for row in rows]
    finally:
        db.close()


def list_gateway_subscriptions(gateway_name: str) -> list[MarketSubscription]:
    db = get_session()
    try:
        return list(
            db.scalars(
                select(MarketSubscription).where(MarketSubscription.gateway_name == gateway_name)
            )
        )
    finally:
        db.close()


def clear_restored(gateway_name: str) -> None:
    _restored_gateways.discard(gateway_name)


def restore_gateway_subscriptions(gateway_name: str, *, force: bool = False) -> int:
    """Re-subscribe persisted contracts via MainEngine after MD login."""
    gw = (gateway_name or "").strip()
    if not gw:
        return 0
    if not force and gw in _restored_gateways:
        return 0
    rows = list_gateway_subscriptions(gw)
    if not rows:
        _restored_gateways.add(gw)
        return 0
    # Deduplicate by symbol.exchange (multiple users may share one gateway row set).
    seen: set[tuple[str, str]] = set()
    ok = 0
    for row in rows:
        key = (row.symbol.upper(), str(row.exchange).upper())
        if key in seen:
            continue
        seen.add(key)
        try:
            exchange = Exchange[str(row.exchange).upper()]
        except KeyError:
            logger.warning("skip restore %s.%s: invalid exchange", row.symbol, row.exchange)
            continue
        try:
            runtime.me.subscribe(
                SubscribeRequest(symbol=row.symbol, exchange=exchange),
                gw,
            )
            ok += 1
        except Exception:
            logger.exception(
                "restore subscribe failed %s %s.%s",
                gw,
                row.symbol,
                row.exchange,
            )
    _restored_gateways.add(gw)
    if ok:
        logger.info("restored %s market subscription(s) for gateway %s", ok, gw)
    return ok
