"""Local ClickHouse HTTP client. Soft-fail when the server is down."""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from core.config import settings
from core.serialize import SHANGHAI, dt_iso
from core.sessions import parse_tick_dt, session_range, trade_date_of

logger = logging.getLogger("stabx.clickhouse")

DATABASE = "vnpy"
TABLE = "market_tick"


def _ttl_days() -> int:
    return max(1, int(settings.clickhouse_tick_ttl_days or 10))


def _table_ddl() -> str:
    days = _ttl_days()
    return f"""
CREATE TABLE IF NOT EXISTS {DATABASE}.{TABLE} (
    symbol        String,
    exchange      String,
    gateway_name  String,
    datetime      DateTime64(3, 'Asia/Shanghai'),
    trade_date    Date,
    last_price    Float64,
    last_volume   Float64,
    volume        Float64,
    turnover      Float64,
    open_interest Float64,
    bid_price_1   Float64,
    bid_volume_1  Float64,
    ask_price_1   Float64,
    ask_volume_1  Float64,
    inserted_at   DateTime64(3, 'Asia/Shanghai') DEFAULT now64(3)
) ENGINE = MergeTree()
PARTITION BY trade_date
ORDER BY (symbol, exchange, datetime)
TTL datetime + INTERVAL {days} DAY DELETE
"""

_ready = False
_down_logged = False
_last_error: str | None = None
_lock = threading.Lock()


def _base_url() -> str:
    raw = (settings.clickhouse_url or "http://127.0.0.1:8123").rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    host = settings.clickhouse_host
    port = settings.clickhouse_port
    return f"http://{host}:{port}"


def _endpoint() -> tuple[str, int]:
    parsed = urlparse(_base_url())
    host = parsed.hostname or settings.clickhouse_host or "127.0.0.1"
    port = parsed.port or int(settings.clickhouse_port or 8123)
    return host, port


def status() -> dict[str, Any]:
    host, port = _endpoint()
    db = settings.clickhouse_database or DATABASE
    payload: dict[str, Any] = {
        "ok": _ready,
        "state": "ok" if _ready else "down",
        "host": host,
        "port": port,
        "url": _base_url(),
        "database": db,
        "table": TABLE,
        "ttl_days": _ttl_days(),
    }
    if not _ready and _last_error:
        payload["error"] = _last_error
    return payload


def describe() -> str:
    host, port = _endpoint()
    db = settings.clickhouse_database or DATABASE
    return f"{host}:{port} database={db}"


def _headers() -> dict[str, str]:
    headers = {"X-ClickHouse-User": settings.clickhouse_user}
    if settings.clickhouse_password:
        headers["X-ClickHouse-Key"] = settings.clickhouse_password
    return headers


def _qstr(value: str) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def _query(sql: str, *, body: bytes | None = None, timeout: float = 8.0) -> bytes:
    db = urllib.parse.quote(settings.clickhouse_database or DATABASE, safe="")
    if body is None:
        url = f"{_base_url()}/?database={db}"
        payload = sql.encode("utf-8")
    else:
        url = f"{_base_url()}/?database={db}&query={urllib.parse.quote(sql)}"
        payload = body
    req = urllib.request.Request(url, data=payload, method="POST", headers=_headers())
    req.add_header("Content-Type", "text/plain; charset=utf-8")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _mark_down(exc: Exception) -> None:
    global _ready, _down_logged, _last_error
    _ready = False
    _last_error = str(exc)
    if not _down_logged:
        logger.warning(
            "ClickHouse unreachable %s: %s (今日分时走内存，历史交易日不可查)",
            describe(),
            exc,
        )
        _down_logged = True


def _mark_up() -> None:
    global _ready, _down_logged, _last_error
    if not _ready or _down_logged:
        logger.info(
            "ClickHouse reachable %s table=%s.%s TTL %sd",
            describe(),
            settings.clickhouse_database or DATABASE,
            TABLE,
            _ttl_days(),
        )
    _ready = True
    _down_logged = False
    _last_error = None


def ping() -> bool:
    try:
        raw = _query("SELECT 1", timeout=3.0)
        return raw.strip() in {b"1", b"1\n"}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def init_clickhouse() -> bool:
    """Create database/table. Returns False if ClickHouse is down (non-fatal)."""
    global _ready
    with _lock:
        try:
            _query(f"CREATE DATABASE IF NOT EXISTS {DATABASE}", timeout=10.0)
            _query(_table_ddl(), timeout=10.0)
            _mark_up()
            return True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            _mark_down(exc)
            return False


def available() -> bool:
    return _ready


def _f(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    if n != n:  # NaN
        return 0.0
    return n


def _row(payload: dict[str, Any]) -> dict[str, Any] | None:
    symbol = str(payload.get("symbol") or "")
    exchange = str(payload.get("exchange") or "")
    dt = parse_tick_dt(payload.get("datetime"))
    if not symbol or not exchange or dt is None:
        return None
    td = trade_date_of(dt, exchange=exchange)
    return {
        "symbol": symbol,
        "exchange": exchange.upper(),
        "gateway_name": str(payload.get("gateway_name") or ""),
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "trade_date": td.isoformat(),
        "last_price": _f(payload.get("last_price")),
        "last_volume": _f(payload.get("last_volume")),
        "volume": _f(payload.get("volume")),
        "turnover": _f(payload.get("turnover")),
        "open_interest": _f(payload.get("open_interest")),
        "bid_price_1": _f(payload.get("bid_price_1")),
        "bid_volume_1": _f(payload.get("bid_volume_1")),
        "ask_price_1": _f(payload.get("ask_price_1")),
        "ask_volume_1": _f(payload.get("ask_volume_1")),
    }


def insert_ticks(payloads: list[dict[str, Any]]) -> int:
    """Batch insert. Returns written count; 0 if down or empty."""
    if not payloads:
        return 0
    rows = [row for row in (_row(p) for p in payloads) if row]
    if not rows:
        return 0
    if not _ready and not init_clickhouse():
        return 0
    body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows).encode("utf-8")
    sql = (
        f"INSERT INTO {DATABASE}.{TABLE} "
        "(symbol, exchange, gateway_name, datetime, trade_date, last_price, last_volume, "
        "volume, turnover, open_interest, bid_price_1, bid_volume_1, ask_price_1, ask_volume_1) "
        "FORMAT JSONEachRow"
    )
    try:
        _query(sql, body=body, timeout=12.0)
        _mark_up()
        return len(rows)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        _mark_down(exc)
        return 0


def _fmt_dt(value: datetime) -> str:
    local = value.astimezone(SHANGHAI) if value.tzinfo else value.replace(tzinfo=SHANGHAI)
    return local.strftime("%Y-%m-%d %H:%M:%S")


def query_ticks(symbol: str, exchange: str, trade_date: date) -> list[dict[str, Any]] | None:
    """Ticks for one 交易日. None = ClickHouse down (caller should fall back)."""
    if not _ready and not init_clickhouse():
        return None
    start, end = session_range(trade_date, exchange=exchange)
    sql = (
        f"SELECT symbol, exchange, gateway_name, datetime, last_price, last_volume, "
        f"volume, turnover, open_interest, bid_price_1, bid_volume_1, ask_price_1, ask_volume_1 "
        f"FROM {DATABASE}.{TABLE} "
        f"WHERE symbol = {_qstr(symbol)} "
        f"AND upper(exchange) = {_qstr(exchange.upper())} "
        f"AND trade_date = '{trade_date.isoformat()}' "
        f"AND datetime >= toDateTime64('{_fmt_dt(start)}', 3, 'Asia/Shanghai') "
        f"AND datetime < toDateTime64('{_fmt_dt(end)}', 3, 'Asia/Shanghai') "
        f"ORDER BY datetime "
        f"LIMIT 80000 "
        f"FORMAT JSONEachRow"
    )
    try:
        raw = _query(sql, timeout=12.0)
        _mark_up()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        _mark_down(exc)
        return None
    out: list[dict[str, Any]] = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dt_raw = row.get("datetime")
        if isinstance(dt_raw, str) and dt_raw and "T" not in dt_raw:
            try:
                parsed = datetime.strptime(dt_raw[:23], "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=SHANGHAI)
            except ValueError:
                try:
                    parsed = datetime.strptime(dt_raw[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=SHANGHAI)
                except ValueError:
                    parsed = None
            row["datetime"] = dt_iso(parsed) if parsed else dt_raw
        out.append(row)
    return out


def list_stored_dates(symbol: str, exchange: str, dates: list[date]) -> set[date] | None:
    """Which of the given trade dates have rows. None = ClickHouse down."""
    if not dates:
        return set()
    if not _ready and not init_clickhouse():
        return None
    in_list = ", ".join(f"'{d.isoformat()}'" for d in dates)
    sql = (
        f"SELECT trade_date FROM {DATABASE}.{TABLE} "
        f"WHERE symbol = {_qstr(symbol)} "
        f"AND upper(exchange) = {_qstr(exchange.upper())} "
        f"AND trade_date IN ({in_list}) "
        f"GROUP BY trade_date "
        f"FORMAT JSONEachRow"
    )
    try:
        raw = _query(sql, timeout=8.0)
        _mark_up()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        _mark_down(exc)
        return None
    found: set[date] = set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw_d = str(row.get("trade_date") or "")[:10]
        try:
            found.add(date.fromisoformat(raw_d))
        except ValueError:
            continue
    return found
