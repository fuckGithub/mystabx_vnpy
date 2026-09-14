"""Account connection + live funds (docs/03, docs/06 B7/B10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from core.channel_log import record_for_user, test_result_label
from core.db import Account, User, account_channel_dict, account_to_dict, get_session
from core.deps import current_user, visible_gateways
from core.runtime import runtime

router = APIRouter(tags=["account"])


class AutoConnectBody(BaseModel):
    auto_connect: bool


def _owned_account(user: User, account_id: int) -> tuple[int, str]:
    db = get_session()
    try:
        acc = db.get(Account, account_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="account not found")
        if not user.is_admin and acc.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权限操作该账户")
        return acc.id, acc.gateway_name
    finally:
        db.close()


@router.get("/api/gateways")
def list_gateways(user: User = Depends(current_user)) -> list[dict]:
    db = get_session()
    try:
        stmt = select(Account).where(Account.status == 1)
        if not user.is_admin:
            stmt = stmt.where(Account.user_id == user.id)
        rows = []
        for acc in db.scalars(stmt):
            st = runtime.gw.channel_statuses(acc.gateway_name)
            rows.append(
                account_channel_dict(
                    acc,
                    conn_status=st["conn_status"],
                    login_status=st["login_status"],
                    quote_status=st["quote_status"],
                    front_info=runtime.gw.front_info.get(acc.gateway_name),
                )
            )
        return rows
    finally:
        db.close()


@router.post("/api/gateways/{account_id}/connect")
def connect_gateway(account_id: int, user: User = Depends(current_user)) -> dict:
    row_id, gateway_name = _owned_account(user, account_id)
    if gateway_name not in runtime.gw.index:
        db = get_session()
        try:
            fresh = db.get(Account, row_id)
            if fresh is None:
                raise HTTPException(status_code=404, detail="account not found")
            runtime.gw.register(account_to_dict(fresh, include_secrets=True))
        finally:
            db.close()
    try:
        meta = runtime.gw.connect(gateway_name)
    except Exception as exc:
        record_for_user(
            user,
            account_id=row_id,
            gateway_name=gateway_name,
            action="连接",
            result="fail",
            message=str(exc),
        )
        raise
    record_for_user(
        user,
        account_id=row_id,
        gateway_name=gateway_name,
        action="连接",
        result="success",
        message="已发起连接",
    )
    return {"ok": True, "gateway_name": gateway_name, **runtime.gw.channel_statuses(gateway_name, live=False), **meta}


@router.post("/api/gateways/{account_id}/test-connect")
def test_gateway(account_id: int, user: User = Depends(current_user)) -> dict:
    row_id, gateway_name = _owned_account(user, account_id)
    if gateway_name not in runtime.gw.index:
        db = get_session()
        try:
            fresh = db.get(Account, row_id)
            if fresh is None:
                raise HTTPException(status_code=404, detail="account not found")
            runtime.gw.register(account_to_dict(fresh, include_secrets=True))
        finally:
            db.close()
    try:
        payload = runtime.gw.test_connect(gateway_name)
    except KeyError:
        record_for_user(
            user,
            account_id=row_id,
            gateway_name=gateway_name,
            action="测试联通",
            result="fail",
            message="gateway not registered",
        )
        raise HTTPException(status_code=404, detail="gateway not registered") from None
    except Exception as exc:
        record_for_user(
            user,
            account_id=row_id,
            gateway_name=gateway_name,
            action="测试联通",
            result="fail",
            message=f"联通测试异常：{exc}",
        )
        raise HTTPException(status_code=500, detail=f"联通测试异常：{exc}") from exc
    result, message = test_result_label(payload)
    record_for_user(
        user,
        account_id=row_id,
        gateway_name=gateway_name,
        action="测试联通",
        result=result,
        message=message,
    )
    return payload


@router.post("/api/gateways/{account_id}/disconnect")
def disconnect_gateway(account_id: int, user: User = Depends(current_user)) -> dict:
    _row_id, gateway_name = _owned_account(user, account_id)
    try:
        runtime.gw.disconnect(gateway_name)
    except Exception as exc:
        record_for_user(
            user,
            account_id=_row_id,
            gateway_name=gateway_name,
            action="断开",
            result="fail",
            message=str(exc),
        )
        raise
    record_for_user(
        user,
        account_id=_row_id,
        gateway_name=gateway_name,
        action="断开",
        result="success",
        message="已断开连接",
    )
    return {"ok": True, "gateway_name": gateway_name, **runtime.gw.channel_statuses(gateway_name, live=False)}


@router.post("/api/gateways/{account_id}/auto-connect")
def set_auto_connect(account_id: int, body: AutoConnectBody, user: User = Depends(current_user)) -> dict:
    row_id, gateway_name = _owned_account(user, account_id)
    db = get_session()
    try:
        acc = db.get(Account, row_id)
        if acc is None:
            raise HTTPException(status_code=404, detail="account not found")
        acc.auto_connect = 1 if body.auto_connect else 0
        db.commit()
        db.refresh(acc)
        runtime.gw.register(account_to_dict(acc, include_secrets=True))
        runtime.gw.apply_auto_connect(gateway_name, bool(body.auto_connect))
        record_for_user(
            user,
            account_id=row_id,
            gateway_name=gateway_name,
            action="自动连接",
            result="success",
            message="已开启启动自动连接" if body.auto_connect else "已关闭自动连接",
        )
        return {
            "ok": True,
            "gateway_name": gateway_name,
            "auto_connect": bool(acc.auto_connect),
            **runtime.gw.channel_statuses(gateway_name, live=False),
        }
    finally:
        db.close()


@router.post("/api/gateways/{account_id}/query")
def query_gateway(account_id: int, user: User = Depends(current_user)) -> dict:
    _row_id, gateway_name = _owned_account(user, account_id)
    runtime.gw.refresh_account(gateway_name, wait=3.0)
    funds = runtime.gw.funds_for({gateway_name})
    return {"ok": True, "gateway_name": gateway_name, "accounts": funds}


@router.get("/api/accounts")
def list_funds(user: User = Depends(current_user)) -> list[dict]:
    gws = set(visible_gateways(user))
    for name in gws:
        if runtime.gw.is_td_connected(name) and not runtime.gw.has_account(name):
            runtime.gw.refresh_account(name, wait=0.8)
    return runtime.gw.funds_for(gws)
