"""POST /api/auth/* — login, refresh, logout (docs/06 B5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from core.config import settings
from core.db import Session, User, get_session, verify_password
from core.deps import create_token, current_user, decode_token, user_public

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


def _issue(user: User) -> dict:
    access = create_token(user.id, "access", timedelta(minutes=settings.access_expire_minutes))
    refresh = create_token(user.id, "refresh", timedelta(days=settings.refresh_expire_days))
    expires = datetime.now(tz=timezone.utc) + timedelta(days=settings.refresh_expire_days)
    db = get_session()
    try:
        db.add(
            Session(
                user_id=user.id,
                refresh_token=refresh,
                expires_at=expires.isoformat(),
                revoked=0,
            )
        )
        db.commit()
    finally:
        db.close()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user": user_public(user),
    }


@router.post("/login")
def login(body: LoginBody) -> dict:
    db = get_session()
    try:
        user = db.scalar(select(User).where(User.username == body.username))
        if user is None or user.status != 1 or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="invalid username or password")
        return _issue(user)
    finally:
        db.close()


@router.post("/refresh")
def refresh(body: RefreshBody) -> dict:
    payload = decode_token(body.refresh_token, expected="refresh")
    db = get_session()
    try:
        row = db.scalar(select(Session).where(Session.refresh_token == body.refresh_token))
        if row is None or row.revoked:
            raise HTTPException(status_code=401, detail="refresh revoked")
        row.revoked = 1
        user = db.get(User, int(payload["sub"]))
        if user is None or user.status != 1:
            raise HTTPException(status_code=401, detail="user disabled")
        db.commit()
        return _issue(user)
    finally:
        db.close()


@router.post("/logout")
def logout(body: RefreshBody, user: User = Depends(current_user)) -> dict:
    db = get_session()
    try:
        row = db.scalar(select(Session).where(Session.refresh_token == body.refresh_token))
        if row and row.user_id == user.id:
            row.revoked = 1
            db.commit()
    finally:
        db.close()
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_public(user)
