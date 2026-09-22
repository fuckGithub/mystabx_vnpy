"""
后端接口测试入口。

注意：测试函数使用同步 `def`，由 TestClient 驱动；勿对用例本身使用 `async def`。
执行示例: `pytest tests/test_main.py` 或 `pytest tests/`
"""

import pytest
from fastapi.testclient import TestClient


def test_check_readiness(test_client: TestClient) -> None:
    """
    校验 ``/common/health/ready/``：数据库与 Redis（若启用）均可达时返回 200 与 checks 结构。
    """
    response = test_client.get("/common/health/ready/")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] is not None
    assert "checks" in body["data"]
    assert body["data"]["checks"].get("database") is True


def test_check_health(test_client: TestClient) -> None:
    """
    校验 `/common/health/` 返回统一成功响应结构。

    参数:
    - test_client (TestClient): pytest 注入的客户端。

    返回:
    - None
    """
    response = test_client.get("/common/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["code"] == 0
    assert body["msg"] == "系统健康"
    assert body["data"] is True
    assert body["status_code"] == 200


def test_plugin_runtime_mounted() -> None:
    """插件运行时已挂载到 app.state，且发现了 app/plugin 下的全部插件。"""
    from app.core.plugin.runtime import get_runtime
    from main import create_app

    app = create_app()
    runtime = get_runtime(app)
    assert runtime is not None
    assert {e.plugin_dir.name for e in runtime.registry.entries} >= {
        "ai",
        "example",
        "generator",
        "task",
    }


# 运行所有测试
if __name__ == "__main__":
    pytest.main(["-v", "tests/test_main.py"])
