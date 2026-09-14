"""Admin user / account CRUD with Fernet-encrypted settings (docs/06 B6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.channel_log import list_channel_logs, record_for_user, test_result_label
from core.crypto import decrypt, encrypt
from core.db import (
    Account,
    User,
    account_channel_dict,
    account_to_dict,
    get_session,
    hash_password,
    user_to_dict,
)
from core.deps import require_admin
from core.runtime import runtime
from core.config import settings
from mystabx.config.simnow import (
    AUTO_FRONT_WINDOWS,
    SIMNOW_24H,
    SIMNOW_ACCOUNT_NAME,
    SIMNOW_CONNECT_DEFAULTS,
    SIMNOW_SESSION,
    merge_connect_settings,
    simnow_fronts_for_now,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    is_admin: bool = False


class AccountCreate(BaseModel):
    id: int | None = None
    user_id: int
    account_name: str | None = None
    gateway_type: str = "CTP"
    connect_settings: dict = Field(default_factory=dict)
    auto_connect: bool | None = None


def _safe_decrypt(ciphertext: str) -> dict:
    try:
        raw = decrypt(ciphertext)
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _channel_row(account: Account) -> dict:
    st = runtime.gw.channel_statuses(account.gateway_name)
    return account_channel_dict(
        account,
        conn_status=st["conn_status"],
        login_status=st["login_status"],
        quote_status=st["quote_status"],
        front_info=runtime.gw.front_info.get(account.gateway_name),
    )


def _find_existing(db, user_id: int, account_name: str, investor_id: str) -> Account | None:
    rows = list(db.scalars(select(Account).where(Account.user_id == user_id)))
    if account_name:
        for acc in rows:
            if (acc.account_name or "").strip() == account_name:
                return acc
    if investor_id:
        for acc in rows:
            stored = _safe_decrypt(acc.connect_settings)
            if str(stored.get("用户名") or "").strip() == investor_id:
                return acc
    return None


def _merge_update(stored: dict, incoming: dict) -> dict:
    combined = dict(stored)
    for key, value in incoming.items():
        if value is None:
            continue
        if key == "密码" and value == "":
            continue
        combined[key] = value
    if not combined.get("密码") and stored.get("密码"):
        combined["密码"] = stored["密码"]
    return merge_connect_settings(combined)


@router.get("/connect-defaults")
def connect_defaults(_: User = Depends(require_admin)) -> dict:
    auto = simnow_fronts_for_now()
    defaults = dict(SIMNOW_CONNECT_DEFAULTS)
    defaults["账户名"] = SIMNOW_ACCOUNT_NAME
    if settings.simnow_user:
        defaults["用户名"] = settings.simnow_user
    if settings.simnow_password:
        defaults["密码"] = settings.simnow_password
    return {
        "defaults": defaults,
        "environments": {
            "session": {"label": "交易时段", **SIMNOW_SESSION},
            "24h": {"label": "7×24", **SIMNOW_24H},
        },
        "interface": {
            "柜台环境": "实盘",
            "note": "本机仅打包实盘 CTP API，SimNow 走生产前置。",
        },
        "auto": {**auto, "windows": AUTO_FRONT_WINDOWS},
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
        return [_channel_row(a) for a in db.scalars(select(Account))]
    finally:
        db.close()


@router.get("/accounts/{account_id}/logs")
def account_op_logs(
    account_id: int,
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    _: User = Depends(require_admin),
) -> dict:
    db = get_session()
    try:
        acc = db.get(Account, account_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="account not found")
    finally:
        db.close()
    return list_channel_logs(account_id, keyword=q, page=page, page_size=page_size)


@router.post("/accounts")
def upsert_account(body: AccountCreate, user: User = Depends(require_admin)) -> dict:
    db = get_session()
    try:
        owner = db.get(User, body.user_id)
        if owner is None:
            raise HTTPException(status_code=404, detail="user not found")
        account_name = (body.account_name or "").strip() or "SimNow"
        investor_id = str(body.connect_settings.get("用户名") or "").strip()
        existing = None
        if body.id:
            existing = db.get(Account, body.id)
            if existing is None:
                raise HTTPException(status_code=404, detail="account not found")
        else:
            existing = _find_existing(db, body.user_id, account_name, investor_id)
        if existing:
            stored = _safe_decrypt(existing.connect_settings)
            setting = _merge_update(stored, body.connect_settings)
            existing.account_name = account_name
            existing.gateway_type = body.gateway_type or existing.gateway_type
            existing.connect_settings = encrypt(setting)
            if body.auto_connect is not None:
                existing.auto_connect = 1 if body.auto_connect else 0
            db.commit()
            db.refresh(existing)
            runtime.gw.register(account_to_dict(existing, include_secrets=True))
            runtime.gw.apply_auto_connect(existing.gateway_name, bool(existing.auto_connect))
            record_for_user(
                user,
                account_id=existing.id,
                gateway_name=existing.gateway_name,
                action="编辑",
                result="success",
                message=f"已更新通道 {existing.account_name or existing.gateway_name}",
            )
            return _channel_row(existing)

        setting = merge_connect_settings(body.connect_settings)
        acc = Account(
            user_id=body.user_id,
            gateway_name="pending",
            gateway_type=body.gateway_type,
            account_name=account_name,
            connect_settings=encrypt(setting),
            status=1,
            auto_connect=1 if body.auto_connect else 0,
        )
        db.add(acc)
        db.flush()
        acc.gateway_name = f"{body.gateway_type}.{acc.id}"
        db.commit()
        db.refresh(acc)
        runtime.gw.register(account_to_dict(acc, include_secrets=True))
        runtime.gw.apply_auto_connect(acc.gateway_name, bool(acc.auto_connect))
        record_for_user(
            user,
            account_id=acc.id,
            gateway_name=acc.gateway_name,
            action="新增",
            result="success",
            message=f"已新增通道 {acc.account_name or acc.gateway_name}",
        )
        return _channel_row(acc)
    finally:
        db.close()


@router.post("/accounts/{account_id}/test-connect")
def test_account_connect(account_id: int, user: User = Depends(require_admin)) -> dict:
    db = get_session()
    try:
        acc = db.get(Account, account_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="account not found")
        runtime.gw.register(account_to_dict(acc, include_secrets=True))
        try:
            payload = runtime.gw.test_connect(acc.gateway_name)
        except KeyError:
            record_for_user(
                user,
                account_id=acc.id,
                gateway_name=acc.gateway_name,
                action="测试联通",
                result="fail",
                message="gateway not registered",
            )
            raise HTTPException(status_code=404, detail="gateway not registered") from None
        except Exception as exc:
            record_for_user(
                user,
                account_id=acc.id,
                gateway_name=acc.gateway_name,
                action="测试联通",
                result="fail",
                message=f"联通测试异常：{exc}",
            )
            raise HTTPException(status_code=500, detail=f"联通测试异常：{exc}") from exc
        result, message = test_result_label(payload)
        record_for_user(
            user,
            account_id=acc.id,
            gateway_name=acc.gateway_name,
            action="测试联通",
            result=result,
            message=message,
        )
        return payload
    finally:
        db.close()


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, user: User = Depends(require_admin)) -> dict:
    db = get_session()
    try:
        acc = db.get(Account, account_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="account not found")
        name = acc.gateway_name
        record_for_user(
            user,
            account_id=acc.id,
            gateway_name=name,
            action="删除",
            result="success",
            message=f"已删除通道 {acc.account_name or name}",
        )
        db.delete(acc)
        db.commit()
        runtime.gw.remove(name)
        return {"ok": True, "id": account_id, "gateway_name": name}
    finally:
        db.close()
