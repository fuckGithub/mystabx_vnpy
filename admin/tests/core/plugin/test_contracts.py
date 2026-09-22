"""槽位契约与降级行为测试。"""

from __future__ import annotations

import asyncio

from app.core.plugin.contracts import OperationLogEntry, OperationLogSink, ParamsProvider
from app.core.plugin.slots import (
    SLOT_CONFIG_PARAMS_PROVIDER,
    SLOT_LOG_OPERATION_SINK,
    clear_slots,
    get,
    provide,
)


def test_operation_log_entry_fields() -> None:
    """OperationLogEntry 覆盖改造前 OperationLogCreateSchema 的全部字段。"""
    entry = OperationLogEntry(
        type=2,
        request_path="/x",
        request_method="GET",
        request_payload="{}",
        request_ip="127.0.0.1",
        login_location="内网",
        request_os="macOS",
        request_browser="Chrome",
        response_code=200,
        response_json="{}",
        process_time="0.01s",
        signature=None,
        signed_fields=None,
        description="查询",
        created_id=1,
        updated_id=1,
        username="super",
        mobile=None,
        login_platform="0",
    )
    assert entry.request_path == "/x"


def test_slot_missing_returns_none() -> None:
    """槽位缺失时取到 None，调用方可安全降级。"""
    clear_slots()
    assert get(SLOT_LOG_OPERATION_SINK) is None
    assert get(SLOT_CONFIG_PARAMS_PROVIDER) is None


def test_fake_sink_satisfies_protocol() -> None:
    """自定义实现满足 Protocol（结构类型）。"""

    class _Sink:
        """测试用日志槽位。"""

        def __init__(self) -> None:
            """初始化。"""
            self.entries: list[OperationLogEntry] = []

        async def write(self, entry: OperationLogEntry, session: object) -> None:
            """记录写入。"""
            self.entries.append(entry)

    sink = _Sink()
    assert isinstance(sink, OperationLogSink)

    async def _run() -> None:
        provide(SLOT_LOG_OPERATION_SINK, sink)
        impl = get(SLOT_LOG_OPERATION_SINK)
        entry = OperationLogEntry(
            type=1,
            request_path="/a",
            request_method="POST",
            request_payload="",
            request_ip=None,
            login_location=None,
            request_os=None,
            request_browser=None,
            response_code=200,
            response_json="",
            process_time="0s",
            signature=None,
            signed_fields=None,
            description=None,
            created_id=None,
            updated_id=None,
            username=None,
            mobile=None,
            login_platform=None,
        )
        await impl.write(entry, object())

    asyncio.run(_run())
    assert len(sink.entries) == 1
    clear_slots()


def test_params_provider_protocol_shape() -> None:
    """ParamsProvider 声明读写两类方法。"""
    assert callable(getattr(ParamsProvider, "get_system_config", None))
    assert callable(getattr(ParamsProvider, "set_param", None))
