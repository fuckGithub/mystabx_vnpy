"""FastAPI app: assemble routers, headless engine, WebSocket / SSE (docs/05, docs/06)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from mystabx.paths import PROJECT_ROOT, ensure_project_trader_dir

ensure_project_trader_dir()

from core.clickhouse import describe as clickhouse_describe  # noqa: E402
from core.clickhouse import init_clickhouse, status as clickhouse_status  # noqa: E402
from core.config import settings  # noqa: E402
from core.db import Account, User, account_to_dict, get_session, init_db  # noqa: E402
from core.deps import decode_token, get_user_by_id, user_public, visible_gateways  # noqa: E402
from core.engine import build_headless_engines  # noqa: E402
from core.events import bind_events  # noqa: E402
from core.gateways import AccountGatewayManager  # noqa: E402
from core.metrics import metrics  # noqa: E402
from core.runtime import runtime  # noqa: E402
from core.serialize import envelope  # noqa: E402
from core.sse import SseClient, format_sse, sse_hub  # noqa: E402
from core.ws import Connection, hub, pong, set_loop  # noqa: E402
from features.account.api import router as account_router  # noqa: E402
from features.admin.api import router as admin_router  # noqa: E402
from features.auth.api import router as auth_router  # noqa: E402
from features.market.api import router as market_router  # noqa: E402
from features.market.tick_writer import start_tick_writer, stop_tick_writer  # noqa: E402
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
    where = clickhouse_describe()
    if init_clickhouse():
        logger.info("ClickHouse reachable %s", where)
    else:
        logger.warning("ClickHouse unreachable %s — 分时今日走内存，历史交易日不可查", where)
    start_tick_writer()
    main_engine, event_engine = build_headless_engines()
    manager = AccountGatewayManager(main_engine)
    manager.load_all(_load_accounts())
    bind_events(event_engine, manager)
    runtime.main_engine = main_engine
    runtime.event_engine = event_engine
    runtime.gateways = manager
    set_loop(asyncio.get_running_loop())
    manager.kickoff_auto_connects()

    def _event_depth() -> int | None:
        ee = runtime.event_engine
        if ee is None:
            return None
        q = getattr(ee, "_queue", None)
        if q is None:
            return None
        try:
            return int(q.qsize())
        except Exception:
            return None

    metrics.bind_event_depth(_event_depth)
    logger.info("headless engine ready, gateways=%s", list(manager.index))
    try:
        yield
    finally:
        stop_tick_writer()
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
        "sse": sse_hub.snapshot_counts(),
        "clickhouse": clickhouse_status(refresh=True),
        "metrics": metrics.snapshot(thresholds=settings.metric_thresholds()),
    }


def _token_from_request(request: Request) -> str | None:
    token = request.query_params.get("token")
    if token:
        return token
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def _authenticate_sse(request: Request) -> tuple[User | None, list[str] | None]:
    token = _token_from_request(request)
    if not token:
        return None, None
    try:
        payload = decode_token(token, expected="access")
        user = get_user_by_id(int(payload["sub"]))
    except Exception:
        return None, None
    return user, visible_gateways(user)


def _kick_account_sync(names: set[str] | None) -> None:
    if not runtime.gateways:
        return
    targets = runtime.gw.index.keys() if names is None else names
    for name in targets:
        if runtime.gw.is_td_connected(name) and not runtime.gw.has_account(name):
            runtime.gw.start_account_sync(name)


@app.get("/api/sse")
async def sse_endpoint(request: Request):
    user, gateways = _authenticate_sse(request)
    if user is None:
        return JSONResponse({"detail": "token 无效"}, status_code=401)
    visible = set(gateways or [])
    names = None if user.is_admin else visible
    client = SseClient(user_id=user.id, is_admin=bool(user.is_admin), gateways=visible)
    sse_hub.register(client)
    _kick_account_sync(names)

    async def stream():
        try:
            snap = runtime.gw.workbench_snapshot(names) if runtime.gateways else {"gateways": [], "accounts": []}
            yield format_sse("snapshot", envelope("snapshot", snap))
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(client.queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if msg is None:
                    break
                yield format_sse(str(msg.get("type") or "message"), msg)
        finally:
            sse_hub.remove(client)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
                names = None if conn.is_admin else conn.gateways
                if runtime.gateways and ("gateway" in conn.topics or not conn.topics):
                    for payload in runtime.gw.statuses_for(names):
                        await ws.send_json(envelope("gateway", payload))
                if runtime.gateways and ("account" in conn.topics or not conn.topics):
                    for payload in runtime.gw.funds_for(names):
                        await ws.send_json(envelope("account", payload))
                    for name in conn.gateways:
                        if runtime.gw.is_td_connected(name) and not runtime.gw.has_account(name):
                            runtime.gw.start_account_sync(name)
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
