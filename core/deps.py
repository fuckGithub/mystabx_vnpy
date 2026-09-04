"""FastAPI dependencies: JWT user and visible gateways (docs/03)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from core.config import settings
from core.db import Account, User, get_session, user_to_dict
from core.runtime import runtime

bearer = HTTPBearer(auto_error=False)


def create_token(user_id: int, token_type: str, expire: timedelta) -> str:
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "exp": datetime.now(tz=timezone.utc) + expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc
    if expected and payload.get("type") != expected:
        raise HTTPException(status_code=401, detail="wrong token type")
    return payload


def get_user_by_id(user_id: int) -> User:
    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None or user.status != 1:
            raise HTTPException(status_code=401, detail="user disabled")
        return user
    finally:
        db.close()


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="missing token")
    payload = decode_token(creds.credentials, expected="access")
    return get_user_by_id(int(payload["sub"]))


def require_admin(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="admin only")
    return user


def visible_gateways(user: User) -> list[str]:
    db = get_session()
    try:
        stmt = select(Account).where(Account.status == 1)
        if not user.is_admin:
            stmt = stmt.where(Account.user_id == user.id)
        return [row.gateway_name for row in db.scalars(stmt)]
    finally:
        db.close()


def user_public(user: User) -> dict:
    data = user_to_dict(user)
    data["gateways"] = visible_gateways(user)
    return data


def get_runtime():
    return runtime
