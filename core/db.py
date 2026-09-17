"""MySQL business store: users / accounts / sessions / subscriptions / logs / strategies.

Hot-path tick / 分时 stay in ClickHouse. `.vntrader/` is only for vnpy CTP session
files and JSON settings — not for app business tables.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session as SASession, mapped_column, sessionmaker

from core.config import settings

logger = logging.getLogger("stabx.db")

SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(tz=SHANGHAI).replace(microsecond=0).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "account_name", name="uq_accounts_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    gateway_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    gateway_type: Mapped[str] = mapped_column(String(32), nullable=False, default="CTP")
    account_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connect_settings: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auto_connect: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    refresh_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[str] = mapped_column(String(32), nullable=False)
    revoked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StrategyInstance(Base):
    """Strategy instance metadata (CTA runtime state may still live in .vntrader JSON)."""

    __tablename__ = "strategy_instances"
    __table_args__ = (UniqueConstraint("strategy_name", name="uq_strategy_instances_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    gateway_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy_class: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    vt_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-instance IDE override; when set, run/backtest compile this instead of class default
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="stopped")
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class StrategyClass(Base):
    """Strategy class meta + source code (authoritative for editable strategies/)."""

    __tablename__ = "strategy_classes"

    class_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    file_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    module: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    editable: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class StrategyBaseClass(Base):
    """Catalog of CTA parent templates (EliteCtaTemplate / TargetPosTemplate / …)."""

    __tablename__ = "strategy_base_classes"

    class_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    module: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    import_stmt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    base_chain: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_default: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class Watchlist(Base):
    __tablename__ = "watchlists"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    vt_symbol: Mapped[str] = mapped_column(String(64), primary_key=True)


class MarketSubscription(Base):
    """Persisted CTP market-data subscriptions (per user + gateway)."""

    __tablename__ = "market_subscriptions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "gateway_name",
            "symbol",
            "exchange",
            name="uq_market_subscriptions_user_gw_sym_ex",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    gateway_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class Instrument(Base):
    """Contract / instrument display names."""

    __tablename__ = "instruments"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_instruments_symbol_exchange"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    product: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class BacktestMeta(Base):
    __tablename__ = "backtest_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    params: Mapped[str] = mapped_column(Text, nullable=False)
    result_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


class ChannelOpLog(Base):
    __tablename__ = "channel_op_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    gateway_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    message: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, default=_now)


_engine: Engine | None = None
SessionLocal: sessionmaker[SASession] | None = None
_ready = False
_last_error: str | None = None


def configured() -> bool:
    return bool(settings.mysql_host and settings.mysql_user and settings.mysql_database)


def available() -> bool:
    return _ready


def status(*, refresh: bool = False) -> dict[str, Any]:
    if refresh and configured() and not _ready:
        init_db()
    payload: dict[str, Any] = {
        "ok": _ready,
        "state": "ok" if _ready else ("unconfigured" if not configured() else "down"),
        "host": settings.mysql_host or "",
        "port": settings.mysql_port,
        "database": settings.mysql_database,
        "user": settings.mysql_user,
        "backend": "mysql",
    }
    if not _ready and _last_error:
        payload["error"] = _last_error
    return payload


def describe() -> str:
    return (
        f"{settings.mysql_host}:{settings.mysql_port} "
        f"database={settings.mysql_database} user={settings.mysql_user}"
    )


def _server_url() -> str:
    user = quote_plus(settings.mysql_user)
    pwd = quote_plus(settings.mysql_password or "")
    return (
        f"mysql+pymysql://{user}:{pwd}@{settings.mysql_host}:{settings.mysql_port}"
        f"/?charset=utf8mb4"
    )


def _db_url() -> str:
    user = quote_plus(settings.mysql_user)
    pwd = quote_plus(settings.mysql_password or "")
    db = quote_plus(settings.mysql_database)
    return (
        f"mysql+pymysql://{user}:{pwd}@{settings.mysql_host}:{settings.mysql_port}"
        f"/{db}?charset=utf8mb4"
    )


def init_db() -> None:
    """Create MySQL database + tables. Raises if MySQL is required but unreachable."""
    global _engine, SessionLocal, _ready, _last_error
    if not configured():
        _ready = False
        _last_error = "STABX_MYSQL_HOST / MYSQL_HOST not set"
        raise RuntimeError(
            "MySQL is required (STABX_MYSQL_HOST or MYSQL_HOST). "
            "Business tables no longer use SQLite."
        )
    try:
        db_name = settings.mysql_database
        if not db_name.replace("_", "").isalnum():
            raise ValueError(f"invalid MySQL database name: {db_name}")

        server = create_engine(_server_url(), pool_pre_ping=True, pool_recycle=3600)
        with server.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
        server.dispose()

        _engine = create_engine(_db_url(), pool_pre_ping=True, pool_recycle=3600)
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(_engine)
        _ensure_strategy_instance_source_column()
        try:
            from core import base_class_store

            base_class_store.ensure_defaults()
        except Exception:
            logger.exception("seed strategy_base_classes on init failed")
        _ready = True
        _last_error = None
        logger.info("MySQL ready %s", describe())
        _bootstrap_admin()
    except Exception as exc:
        _ready = False
        _last_error = str(exc)
        _engine = None
        SessionLocal = None
        logger.exception("MySQL init failed %s", describe())
        raise


def _ensure_strategy_instance_source_column() -> None:
    """Add strategy_instances.source_code on existing DBs (create_all skips new cols)."""
    if _engine is None:
        return
    try:
        with _engine.connect() as conn:
            rows = conn.execute(
                text("SHOW COLUMNS FROM strategy_instances LIKE 'source_code'")
            ).fetchall()
            if not rows:
                conn.execute(text("ALTER TABLE strategy_instances ADD COLUMN source_code TEXT NULL"))
                conn.commit()
                logger.info("added strategy_instances.source_code")
    except Exception:
        logger.exception("ensure strategy_instances.source_code failed")

def get_session() -> SASession:
    if SessionLocal is None or not _ready:
        raise RuntimeError("database is not initialized (MySQL)")
    return SessionLocal()


def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt

    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def _bootstrap_admin() -> None:
    db = get_session()
    try:
        exists = db.scalar(select(User).where(User.username == settings.admin_username))
        if exists:
            return
        db.add(
            User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                display_name="Administrator",
                status=1,
                is_admin=1,
                created_at=_now(),
            )
        )
        db.commit()
        logger.info("bootstrapped admin user %s", settings.admin_username)
    finally:
        db.close()


def upsert_instrument(*, symbol: str, exchange: str, name: str, product: str | None = None) -> None:
    if not name.strip():
        return
    sym = symbol.strip()
    ex = exchange.strip().upper()
    nm = name.strip()
    db = get_session()
    try:
        row = db.scalar(
            select(Instrument).where(Instrument.symbol == sym, Instrument.exchange == ex)
        )
        if row is None:
            db.add(
                Instrument(symbol=sym, exchange=ex, name=nm, product=product, updated_at=_now())
            )
        else:
            row.name = nm
            if product:
                row.product = product
            row.updated_at = _now()
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("upsert instrument failed %s.%s", sym, ex)
    finally:
        db.close()


def lookup_instrument_name(symbol: str, exchange: str) -> str | None:
    db = get_session()
    try:
        row = db.scalar(
            select(Instrument).where(
                Instrument.symbol == symbol.strip(),
                Instrument.exchange == exchange.strip().upper(),
            )
        )
        return (row.name or "").strip() or None if row else None
    finally:
        db.close()


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "status": user.status,
        "is_admin": bool(user.is_admin),
        "created_at": user.created_at,
    }


def account_to_dict(account: Account, *, include_secrets: bool = False) -> dict[str, Any]:
    data = {
        "id": account.id,
        "user_id": account.user_id,
        "gateway_name": account.gateway_name,
        "gateway_type": account.gateway_type,
        "account_name": account.account_name,
        "status": account.status,
        "auto_connect": bool(getattr(account, "auto_connect", 0)),
        "created_at": account.created_at,
    }
    if include_secrets:
        data["connect_settings"] = account.connect_settings
    return data


def account_channel_dict(
    account: Account,
    *,
    conn_status: str = "DISCONNECTED",
    login_status: str = "DISCONNECTED",
    quote_status: str = "DISCONNECTED",
    front_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Public channel row: never includes 密码."""
    from core.crypto import decrypt
    from mystabx.config.simnow import (
        apply_simnow_auto_fronts,
        auto_front_enabled,
        merge_connect_settings,
        public_connect_settings,
    )

    data = account_to_dict(account)
    try:
        stored = decrypt(account.connect_settings)
    except Exception:
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    merged = merge_connect_settings(stored)
    data["connect"] = public_connect_settings(merged)
    data["auto_front"] = auto_front_enabled(merged)
    data["conn_status"] = conn_status
    data["login_status"] = login_status
    data["td_status"] = login_status
    data["trade_status"] = login_status
    data["quote_status"] = quote_status
    data["md_status"] = quote_status
    if front_info:
        data["front_env"] = front_info.get("front_env")
        data["front_label"] = front_info.get("front_label")
        data["交易服务器"] = front_info.get("交易服务器")
        data["行情服务器"] = front_info.get("行情服务器")
        if "front_fallback" in front_info:
            data["front_fallback"] = front_info.get("front_fallback")
        if "front_preferred" in front_info:
            data["front_preferred"] = front_info.get("front_preferred")
    else:
        _resolved, meta = apply_simnow_auto_fronts(merged)
        data["front_env"] = meta["front_env"]
        data["front_label"] = meta["front_label"]
        data["交易服务器"] = meta.get("交易服务器")
        data["行情服务器"] = meta.get("行情服务器")
    return data
