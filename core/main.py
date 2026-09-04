"""FastAPI app: assemble routers, headless engine, WebSocket (docs/05, docs/06)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from mystabx.paths import PROJECT_ROOT, ensure_project_trader_dir

ensure_project_trader_dir()

from core.config import settings  # noqa: E402
from core.db import Account, User, account_to_dict, get_session, init_db  # noqa: E402
from core.deps import decode_token, get_user_by_id, user_public, visible_gateways  # noqa: E402
from core.engine import build_headless_engines  # noqa: E402
from core.events import bind_events  # noqa: E402
from core.gateways import AccountGatewayManager  # noqa: E402
from core.runtime import runtime  # noqa: E402
from core.serialize import envelope  # noqa: E402
from core.ws import Connection, hub, pong, set_loop  # noqa: E402
from features.account.api import router as account_router  # noqa: E402
from features.admin.api import router as admin_router  # noqa: E402
from features.auth.api import router as auth_router  # noqa: E402
from features.market.api import router as market_router  # noqa: E402
from features.trade.api import router as trade_router  # noqa: E402

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("stabx")


def _load_accounts() -> list[dict]:
    db = get_session()
    try:
        return [account_to_dict(row, include_secrets=True) for row in db.scalars(select(Account))]
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    main_engine, event_engine = build_headless_engines()
    manager = AccountGatewayManager(main_engine)
    manager.load_all(_load_accounts())
    bind_events(event_engine, manager)
    runtime.main_engine = main_engine
    runtime.event_engine = event_engine
    runtime.gateways = manager
    set_loop(asyncio.get_running_loop())
    logger.info("headless engine ready, gateways=%s", list(manager.index))
    try:
        yield
    finally:
        set_loop(None)
        runtime.gateways = None
        runtime.event_engine = None
        if runtime.main_engine is not None:
            runtime.main_engine.close()
            runtime.main_engine = None


app = FastAPI(title="Stabx Web Trader", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(account_router)
app.include_router(market_router)
app.include_router(trade_router)


@app.get("/health")
def health() -> dict:
    engine_ok = runtime.main_engine is not None
    return {
        "status": "ok" if engine_ok else "starting",
        "engine": engine_ok,
        "gateways": list(runtime.gw.index) if runtime.gateways else [],
        "ws": hub.snapshot_counts(),
    }


async def _authenticate_ws(ws: WebSocket) -> tuple[User | None, list[str] | None]:
    token = ws.query_params.get("token")
    if not token:
        first = await ws.receive_json()
        if first.get("type") != "auth":
            await ws.send_json(envelope("error", {"code": "AUTH_REQUIRED", "message": "请先发送 auth"}))
            await ws.close()
            return None, None
        token = (first.get("data") or {}).get("token")
    try:
        payload = decode_token(token, expected="access")
        user = get_user_by_id(int(payload["sub"]))
    except Exception:
        await ws.send_json(envelope("error", {"code": "AUTH_FAILED", "message": "token 无效"}))
        await ws.close()
        return None, None
    return user, visible_gateways(user)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    user, gateways = await _authenticate_ws(ws)
    if user is None:
        return
    conn = Connection(
        ws=ws,
        user_id=user.id,
        is_admin=bool(user.is_admin),
        gateways=set(gateways),
    )
    hub.register(conn)
    await ws.send_json(envelope("auth_ok", user_public(user)))
    try:
        while True:
            message = await ws.receive_json()
            msg_type = message.get("type")
            data = message.get("data") or {}
            if msg_type == "ping":
                await ws.send_json(pong())
            elif msg_type == "subscribe":
                topics = {str(t) for t in data.get("topics") or []}
                conn.topics.update(topics)
            elif msg_type == "unsubscribe":
                topics = {str(t) for t in data.get("topics") or []}
                conn.topics.difference_update(topics)
            elif msg_type == "auth":
                await ws.send_json(envelope("auth_ok", user_public(user)))
            else:
                await ws.send_json(envelope("error", {"code": "UNKNOWN_TYPE", "message": str(msg_type)}))
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(ws)


_DIST = PROJECT_ROOT / "dist"
_SPA_RESERVED = frozenset({"api", "ws", "health", "docs", "redoc", "openapi.json"})
if (_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")


@app.get("/{full_path:path}")
async def spa(full_path: str):
    first = full_path.split("/", 1)[0]
    if first in _SPA_RESERVED:
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    index = _DIST / "index.html"
    if not index.is_file():
        return JSONResponse(
            {"detail": "frontend not built; run ./start.sh or npm run build"},
            status_code=503,
        )
    if full_path:
        candidate = (_DIST / full_path).resolve()
        try:
            candidate.relative_to(_DIST.resolve())
        except ValueError:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
    return FileResponse(index)
