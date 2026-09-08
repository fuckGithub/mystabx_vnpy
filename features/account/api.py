"""Account connection + live funds (docs/03, docs/06 B7/B10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from core.db import Account, User, account_channel_dict, account_to_dict, get_session
from core.deps import current_user, visible_gateways
from core.runtime import runtime
from core.serialize import account_payload

router = APIRouter(tags=["account"])


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
            rows.append(
                account_channel_dict(
                    acc,
                    conn_status=runtime.gw.status.get(acc.gateway_name, "DISCONNECTED"),
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
    meta = runtime.gw.connect(gateway_name)
    return {"ok": True, "gateway_name": gateway_name, "status": "CONNECTING", **meta}


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
        return runtime.gw.test_connect(gateway_name)
    except KeyError:
        raise HTTPException(status_code=404, detail="gateway not registered") from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"联通测试异常：{exc}") from exc


@router.post("/api/gateways/{account_id}/disconnect")
def disconnect_gateway(account_id: int, user: User = Depends(current_user)) -> dict:
    _row_id, gateway_name = _owned_account(user, account_id)
    runtime.gw.disconnect(gateway_name)
    return {"ok": True, "gateway_name": gateway_name, "status": "DISCONNECTED"}


@router.get("/api/accounts")
def list_funds(user: User = Depends(current_user)) -> list[dict]:
    gws = set(visible_gateways(user))
    return [account_payload(a) for a in runtime.oms.get_all_accounts() if a.gateway_name in gws]
