"""内核会话信息模型测试。"""

from __future__ import annotations

import json
from datetime import datetime

from app.core.auth.session import SessionInfo
from app.plugin.module_monitor.online.schema import OnlineOutSchema


def test_session_info_json_roundtrip() -> None:
    """字段可序列化为 JSON 字符串并被解析回来（与 ``OnlineOutSchema`` 契约零差异）。"""
    login_time = datetime(2026, 9, 12, 10, 20, 30)
    info = SessionInfo(
        session_id="s-1",
        user_id=1,
        name="管理员",
        user_name="super",
        ipaddr="127.0.0.1",
        login_location="内网",
        os="macOS",
        browser="Chrome",
        login_time=login_time,
        login_type="0",
    )
    raw = info.model_dump_json()
    assert '"session_id":"s-1"' in raw
    assert SessionInfo.model_validate_json(raw).user_id == 1

    # 字段顺序与必填性必须与 module_monitor.OnlineOutSchema 完全一致
    assert list(SessionInfo.model_fields) == [
        "name",
        "session_id",
        "user_id",
        "user_name",
        "ipaddr",
        "login_location",
        "os",
        "browser",
        "login_time",
        "login_type",
    ]
    required = {key for key, field in SessionInfo.model_fields.items() if field.is_required()}
    assert required == {"name", "session_id", "user_id", "user_name"}

    # login_time 走内核 DateTimeStr（DATETIME_DISPLAY_FMT），不得回退为 ISO 8601
    assert json.loads(raw)["login_time"] == "2026-09-12 10:20:30"
    assert SessionInfo.model_validate_json(raw).login_time == login_time


def test_online_out_schema_mirrors_session_info() -> None:
    """监控插件子类的子类契约：字段顺序与必填集合与内核模型逐项一致。

    ``OnlineOutSchema`` 只是内核 ``SessionInfo`` 的对外别名（零新增字段）。一旦有人
    在子类上重排字段、补字段或改必填性，对外的在线用户响应模型就与写进 JWT/Redis
    的内核模型分叉——本测试把这个不变量钉住。
    """
    assert SessionInfo.model_config.get("from_attributes") is True
    assert OnlineOutSchema.model_config.get("from_attributes") is True

    assert list(OnlineOutSchema.model_fields) == list(SessionInfo.model_fields)
    assert {
        key for key, field in OnlineOutSchema.model_fields.items() if field.is_required()
    } == {key for key, field in SessionInfo.model_fields.items() if field.is_required()}

    # 类 docstring 会被 pydantic 提升为 JSON Schema 的 description（对外 OpenAPI 文本），
    # 因此子类 docstring 必须与迁移前逐字一致；机制说明只能放注释。
    assert OnlineOutSchema.model_json_schema()["description"] == "在线用户对应pydantic模型"
