"""Import FastAPI app and hit /health + login. Does not start uvicorn or the GUI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from mystabx.paths import ensure_project_trader_dir

ensure_project_trader_dir()

from fastapi.testclient import TestClient

from core.config import settings
from core.main import app


def main() -> int:
    with TestClient(app) as client:
        health = client.get("/health")
        health.raise_for_status()
        body = health.json()
        if not body.get("engine"):
            print("health engine not ready", body, file=sys.stderr)
            return 1

        login = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": settings.admin_password},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        for path in ("/api/positions", "/api/orders", "/api/trades", "/api/accounts", "/api/gateways"):
            resp = client.get(path, headers=headers)
            resp.raise_for_status()

        denied = client.get("/api/sse")
        if denied.status_code != 401:
            print("sse missing auth should be 401", denied.status_code, file=sys.stderr)
            return 1

        print(f"health={body}")
        print(f"login_user={login.json()['user']['username']}")
        print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
