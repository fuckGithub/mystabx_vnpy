"""操作日志 SM2 签名的开关与降级行为测试。

``build_operation_log_signature`` 是 ``OperationLogRoute`` 收尾阶段的签名入口，
每个被记录的请求都会经过它（纯 Python SM2 单次约数毫秒），因此单独锁定其行为：
开关语义、签名可验证性，以及异常必须降级而不得让请求收尾失败。
"""

from __future__ import annotations

import json

import pytest

from app.config.setting import settings
from app.core.router_class import build_operation_log_signature
from app.utils.sm_crypto import Sm2Cipher

GOLDEN_SM2_PRIV = "fef1cd14d44d8a57afa854312a2fb11155638a9d6444d8a35db0e75cf4949246"
GOLDEN_SM2_PUB = (
    "046574bf3f968a9fc217ce48f65543c64be1a6a8dc8325ffed3125e425fb09626"
    "b3996ca6e16bc109c3e43a1133a2c16485f4f67dd0d8dded6b837f4e9dca2ea21"
)

SIGN_DATA = "payload|response|0.003"
EXPECTED_SIGNED_FIELDS = json.dumps(
    ["request_payload", "response_json", "process_time"], ensure_ascii=False
)


def test_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """开关关闭时不产生签名与字段列表（该路径应零开销）。"""
    monkeypatch.setattr(settings, "OPERATION_LOG_SIGN_ENABLE", False)

    assert build_operation_log_signature(SIGN_DATA) == (None, None)


def test_enabled_returns_verifiable_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    """开关开启时返回能被公钥验证的签名，以及固定的被签字段列表。"""
    monkeypatch.setattr(settings, "OPERATION_LOG_SIGN_ENABLE", True)
    monkeypatch.setattr(settings, "SM2_PRIVATE_KEY", GOLDEN_SM2_PRIV)
    monkeypatch.setattr(settings, "SM2_PUBLIC_KEY", GOLDEN_SM2_PUB)

    signature, signed_fields = build_operation_log_signature(SIGN_DATA)

    assert signature is not None
    assert signed_fields == EXPECTED_SIGNED_FIELDS
    assert Sm2Cipher.verify(GOLDEN_SM2_PUB, SIGN_DATA.encode("utf-8"), signature) is True


def test_signature_failure_degrades_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """密钥缺失等异常必须降级为「无签名」，不得让请求收尾失败。"""
    monkeypatch.setattr(settings, "OPERATION_LOG_SIGN_ENABLE", True)
    monkeypatch.setattr(settings, "SM2_PRIVATE_KEY", "")
    monkeypatch.setattr(settings, "SM2_PUBLIC_KEY", "")

    assert build_operation_log_signature(SIGN_DATA) == (None, None)


def test_default_is_enabled() -> None:
    """默认保持开启，避免静默改变已有的数据写入行为。"""
    field = type(settings).model_fields["OPERATION_LOG_SIGN_ENABLE"]

    assert field.default is True
