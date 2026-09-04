"""Admin user / account CRUD with Fernet-encrypted settings (docs/06 B6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.crypto import decrypt, encrypt
from core.db import Account, User, account_to_dict, get_session, hash_password, user_to_dict
from core.deps import require_admin
from core.runtime import runtime
from mystabx.config.simnow import (
    SIMNOW_24H,
    SIMNOW_CONNECT_DEFAULTS,
    SIMNOW_SESSION,
    merge_connect_settings,
    public_connect_settings,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    is_admin: bool = False


class AccountCreate(BaseModel):
    user_id: int
    account_name: str | None = None
    gateway_type: str = "CTP"
    connect_settings: dict = Field(default_factory=dict)


def _safe_decrypt(ciphertext: str) -> dict:
    try:
        raw = decrypt(ciphertext)
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _account_admin_row(account: Account) -> dict:
    row = account_to_dict(account)
    stored = _safe_decrypt(account.connect_settings)
    row["connect"] = public_connect_settings(merge_connect_settings(stored))
    row["conn_status"] = runtime.gw.status.get(account.gateway_name, "DISCONNECTED")
    return row


@router.get("/connect-defaults")
def connect_defaults(_: User = Depends(require_admin)) -> dict:
    return {
        "defaults": dict(SIMNOW_CONNECT_DEFAULTS),
        "environments": {
            "session": {"label": "交易时段", **SIMNOW_SESSION},
            "24h": {"label": "7×24", **SIMNOW_24H},
        },
        "interface": {
            "柜台环境": "实盘",
            "note": "本机仅打包实盘 CTP API，SimNow 走生产前置。",
        },
    }


@router.get("/users")
def list_users(_: User = Depends(require_admin)) -> list[dict]:
    db = get_session()
    try:
        return [user_to_dict(u) for u in db.scalars(select(User))]
    finally:
        db.close()


@router.post("/users")
def create_user(body: UserCreate, _: User = Depends(require_admin)) -> dict:
    db = get_session()
    try:
        if db.scalar(select(User).where(User.username == body.username)):
            raise HTTPException(status_code=400, detail="username exists")
        user = User(
            username=body.username,
            password_hash=hash_password(body.password),
            display_name=body.display_name or body.username,
            status=1,
            is_admin=1 if body.is_admin else 0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user_to_dict(user)
    finally:
        db.close()


@router.get("/accounts")
def list_accounts(_: User = Depends(require_admin)) -> list[dict]:
    db = get_session()
    try:
        return [_account_admin_row(a) for a in db.scalars(select(Account))]
    finally:
        db.close()


@router.post("/accounts")
def create_account(body: AccountCreate, _: User = Depends(require_admin)) -> dict:
    db = get_session()
    try:
        owner = db.get(User, body.user_id)
        if owner is None:
            raise HTTPException(status_code=404, detail="user not found")
        setting = merge_connect_settings(body.connect_settings)
        acc = Account(
            user_id=body.user_id,
            gateway_name="pending",
            gateway_type=body.gateway_type,
            account_name=body.account_name,
            connect_settings=encrypt(setting),
            status=1,
        )
        db.add(acc)
        db.flush()
        acc.gateway_name = f"{body.gateway_type}.{acc.id}"
        db.commit()
        db.refresh(acc)
        runtime.gw.register(account_to_dict(acc, include_secrets=True))
        return _account_admin_row(acc)
    finally:
        db.close()
