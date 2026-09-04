"""SQLite business store: users / accounts / sessions (docs/02, docs/03)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import ForeignKey, Integer, String, create_engine, select
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    gateway_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    gateway_type: Mapped[str] = mapped_column(String, nullable=False, default="CTP")
    account_name: Mapped[str | None] = mapped_column(String, nullable=True)
    connect_settings: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
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
    _bootstrap_admin()


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
        "created_at": account.created_at,
    }
    if include_secrets:
        data["connect_settings"] = account.connect_settings
    return data
