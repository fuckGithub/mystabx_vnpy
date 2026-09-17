"""SQLite business store: users / accounts / sessions (docs/02, docs/03)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session as SASession, mapped_column, sessionmaker

from core.config import settings

SHANGHAI = timezone(timedelta(hours=8))


def _now() -> str:
    return datetime.now(tz=SHANGHAI).replace(microsecond=0).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("user_id", "account_name", name="uq_accounts_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    gateway_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    gateway_type: Mapped[str] = mapped_column(String, nullable=False, default="CTP")
    account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    connect_settings: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    auto_connect: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[str] = mapped_column(String, nullable=False)
    revoked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StrategyInstance(Base):
    __tablename__ = "strategy_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    gateway_name: Mapped[str | None] = mapped_column(String, nullable=True)
    strategy_class: Mapped[str] = mapped_column(String, nullable=False)
    vt_symbol: Mapped[str] = mapped_column(String, nullable=False)
    params: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="stopped")
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


class Watchlist(Base):
    __tablename__ = "watchlists"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    vt_symbol: Mapped[str] = mapped_column(String, primary_key=True)


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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    gateway_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    exchange: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class BacktestMeta(Base):
    __tablename__ = "backtest_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    params: Mapped[str] = mapped_column(String, nullable=False)
    result_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


class ChannelOpLog(Base):
    __tablename__ = "channel_op_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    gateway_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    action: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False, default="success")
    message: Mapped[str] = mapped_column(String, nullable=False, default="")
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False, default=_now)


_engine: Engine | None = None
SessionLocal: sessionmaker[SASession] | None = None


def init_db() -> None:
    global _engine, SessionLocal
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(
        f"sqlite:///{settings.sqlite_path}",
        connect_args={"check_same_thread": False},
    )
    with _engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(_engine)
    _ensure_account_name_unique()
    _ensure_account_auto_connect()
    _bootstrap_admin()


def _ensure_account_auto_connect() -> None:
    """SQLite create_all will not add columns to an existing accounts table."""
    if _engine is None:
        return
    with _engine.begin() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(accounts)").fetchall()]
        if "auto_connect" not in cols:
            conn.exec_driver_sql(
                "ALTER TABLE accounts ADD COLUMN auto_connect INTEGER NOT NULL DEFAULT 0"
            )


def _ensure_account_name_unique() -> None:
    """Add (user_id, account_name) unique index when the table has no leftover dupes."""
    if _engine is None:
        return
    with _engine.begin() as conn:
        dupes = conn.exec_driver_sql(
            """
            SELECT 1 FROM accounts
            GROUP BY user_id, COALESCE(account_name, '')
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        ).fetchone()
        if dupes:
            return
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_user_name "
            "ON accounts (user_id, account_name)"
        )


def get_session() -> SASession:
    if SessionLocal is None:
        raise RuntimeError("database is not initialized")
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
