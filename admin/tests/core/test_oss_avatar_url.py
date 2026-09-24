"""OSS 头像 URL：私有桶须签名；库内存 canonical。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.config.setting import settings
from app.utils.oss_util import OssUtil


@pytest.fixture(autouse=True)
def _oss_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "OSS_ENABLE", True)
    monkeypatch.setattr(settings, "OSS_ACCESS_KEY", "ak")
    monkeypatch.setattr(settings, "OSS_SECRET_KEY", "sk")
    monkeypatch.setattr(settings, "OSS_BUCKET_NAME", "stabx-dev")
    monkeypatch.setattr(settings, "OSS_ENDPOINT", "https://oss-cn-beijing.aliyuncs.com")
    monkeypatch.setattr(
        settings, "OSS_CUSTOM_DOMAIN", "https://stabx-dev.oss-cn-beijing.aliyuncs.com"
    )
    monkeypatch.setattr(settings, "OSS_PREFIX", "upload/")
    monkeypatch.setattr(settings, "OSS_PUBLIC_READ", False)
    monkeypatch.setattr(settings, "OSS_SIGN_URL_EXPIRE_SECONDS", 3600)
    OssUtil.clear_cache()
    yield
    OssUtil.clear_cache()


def test_canonical_url_uses_custom_domain():
    assert (
        OssUtil.canonical_url("upload/2026/09/24/a.jpg")
        == "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/2026/09/24/a.jpg"
    )


def test_key_from_custom_domain_url():
    url = "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/2026/09/24/a.jpg"
    assert OssUtil.key_from_url_or_path(url) == "upload/2026/09/24/a.jpg"


def test_to_storage_url_strips_signature():
    signed = (
        "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/2026/09/24/a.jpg"
        "?Expires=1&OSSAccessKeyId=ak&Signature=abc&t=9"
    )
    assert (
        OssUtil.to_storage_url(signed)
        == "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/2026/09/24/a.jpg"
    )


def test_public_or_signed_url_signs_when_private():
    mock_bucket = MagicMock()
    mock_bucket.sign_url.return_value = (
        "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/a.jpg"
        "?Expires=1&OSSAccessKeyId=ak&Signature=sig"
    )
    with patch.object(OssUtil, "_bucket", return_value=mock_bucket):
        url = OssUtil.public_or_signed_url("upload/a.jpg")
    assert "Signature=sig" in url
    assert url.startswith("https://stabx-dev.oss-cn-beijing.aliyuncs.com/")
    mock_bucket.sign_url.assert_called_once()


def test_public_or_signed_url_public_read_skips_sign(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "OSS_PUBLIC_READ", True)
    mock_bucket = MagicMock()
    with patch.object(OssUtil, "_bucket", return_value=mock_bucket):
        url = OssUtil.public_or_signed_url("upload/a.jpg")
    assert url == "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/a.jpg"
    mock_bucket.sign_url.assert_not_called()


def test_ensure_browser_url_resigns_canonical():
    mock_bucket = MagicMock()
    mock_bucket.sign_url.return_value = (
        "https://oss-cn-beijing.aliyuncs.com/stabx-dev/upload/a.jpg"
        "?Expires=1&OSSAccessKeyId=ak&Signature=new"
    )
    canonical = "https://stabx-dev.oss-cn-beijing.aliyuncs.com/upload/a.jpg"
    with patch.object(OssUtil, "_bucket", return_value=mock_bucket):
        out = OssUtil.ensure_browser_url(canonical)
    assert out is not None
    assert "Signature=new" in out
