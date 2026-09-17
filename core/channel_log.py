"""Per-channel operation logs in MySQL. Never persist passwords or auth codes."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import or_, select

from core.db import ChannelOpLog, User, get_session

logger = logging.getLogger("stabx.channel_log")

_SHANGHAI = timezone(timedelta(hours=8))

_SECRET_RE = re.compile(
    r"(密码|授权编码|password|passwd|auth_?code|AuthCode)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


def sanitize_message(text: str) -> str:
    cleaned = _SECRET_RE.sub(r"\1=***", str(text or ""))
    return cleaned[:2000]


def operator_fields(user: User | None) -> dict[str, Any]:
    if user is None:
        return {"operator_id": None, "operator_name": None}
    name = (user.username or user.display_name or "").strip() or None
    return {"operator_id": user.id, "operator_name": name}


def record_channel_op(
    *,
    account_id: int | None,
    gateway_name: str,
    action: str,
    result: str,
    message: str = "",
    operator_id: int | None = None,
    operator_name: str | None = None,
) -> None:
    try:
        db = get_session()
        try:
            db.add(
                ChannelOpLog(
                    account_id=account_id,
                    gateway_name=gateway_name or "",
                    action=action,
                    result=result,
                    message=sanitize_message(message),
                    operator_id=operator_id,
                    operator_name=operator_name,
                    created_at=datetime.now(tz=_SHANGHAI).replace(microsecond=0).isoformat(),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("failed to write channel op log %s %s", gateway_name, action)


def record_for_user(
    user: User | None,
    *,
    account_id: int | None,
    gateway_name: str,
    action: str,
    result: str,
    message: str = "",
) -> None:
    record_channel_op(
        account_id=account_id,
        gateway_name=gateway_name,
        action=action,
        result=result,
        message=message,
        **operator_fields(user),
    )


def test_result_label(payload: dict[str, Any] | None, *, ok: bool = False) -> tuple[str, str]:
    if not payload:
        return ("fail", "联通测试失败")
    summary = str(payload.get("summary") or "").strip()
    if payload.get("ok") or ok:
        return ("success", summary or "联通测试成功")
    if payload.get("reachable"):
        return ("warning", summary or "前置可连，柜台未确认")
    return ("fail", summary or "联通测试失败")


def list_channel_logs(
    account_id: int,
    *,
    keyword: str = "",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    db = get_session()
    try:
        stmt = select(ChannelOpLog).where(ChannelOpLog.account_id == account_id)
        q = keyword.strip()
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(
                    ChannelOpLog.action.like(like),
                    ChannelOpLog.result.like(like),
                    ChannelOpLog.message.like(like),
                    ChannelOpLog.operator_name.like(like),
                )
            )
        rows = list(db.scalars(stmt.order_by(ChannelOpLog.id.desc())))
        total = len(rows)
        start = (page - 1) * page_size
        items = [_log_dict(row) for row in rows[start : start + page_size]]
        return {"items": items, "total": total, "page": page, "page_size": page_size, "store": "mysql"}
    finally:
        db.close()


def _log_dict(row: ChannelOpLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "account_id": row.account_id,
        "gateway_name": row.gateway_name,
        "action": row.action,
        "result": row.result,
        "message": row.message or "",
        "operator_id": row.operator_id,
        "operator_name": row.operator_name or "",
        "created_at": row.created_at,
    }
