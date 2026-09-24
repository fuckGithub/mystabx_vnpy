"""阿里云 OSS 工具（oss2）。

与 mystabx UPMS 配置键对齐：``OSS_ACCESS_KEY`` / ``OSS_SECRET_KEY`` /
``OSS_ENDPOINT`` / ``OSS_BUCKET_NAME`` 等。同步 SDK 通过 ``asyncio.to_thread`` 包装。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.logger import log

# 写入 DB / 持久化时应剥离的 OSS 签名与缓存破坏参数
_OSS_EPHEMERAL_QUERY_KEYS = frozenset(
    {
        "t",
        "expires",
        "signature",
        "ossaccesskeyid",
        "security-token",
        "x-oss-credential",
        "x-oss-date",
        "x-oss-expires",
        "x-oss-signature",
        "x-oss-signature-version",
        "x-oss-security-token",
    }
)


@dataclass(frozen=True)
class OssListEntry:
    """目录列举条目。"""

    name: str
    key: str
    is_dir: bool
    size: int | None
    modified_time: datetime | None


def _normalize_prefix(prefix: str) -> str:
    """规范化对象键前缀（无首斜杠，目录以 / 结尾）。"""
    p = (prefix or "").strip().lstrip("/")
    if p and not p.endswith("/"):
        p = f"{p}/"
    return p


def _normalize_rel_path(path: str | None) -> str:
    """将浏览路径规范为相对前缀内的路径（无首尾多余斜杠）。"""
    if not path:
        return ""
    p = path.strip().replace("\\", "/")
    for prefix in (
        settings.STATIC_URL.rstrip("/") + "/",
        (settings.ROOT_PATH.rstrip("/") + settings.STATIC_URL.rstrip("/") + "/"),
        "upload/",
    ):
        if p.startswith(prefix):
            p = p[len(prefix) :]
            break
    if p.startswith(("http://", "https://")):
        parsed = urlparse(p)
        p = (parsed.path or "").lstrip("/")
        bucket = settings.OSS_BUCKET_NAME.strip()
        if bucket and p.startswith(f"{bucket}/"):
            p = p[len(bucket) + 1 :]
        oss_prefix = _normalize_prefix(settings.OSS_PREFIX)
        if oss_prefix and p.startswith(oss_prefix):
            p = p[len(oss_prefix) :]
    p = p.lstrip("/")
    if ".." in p.split("/") or "\x00" in p:
        raise CustomException(msg="非法的路径格式")
    return p.strip("/")


class OssUtil:
    """阿里云 OSS 封装。"""

    @staticmethod
    def is_ready() -> bool:
        """全局 OSS 是否可用。"""
        return settings.OSS_READY

    @classmethod
    @lru_cache(maxsize=1)
    def _bucket(cls) -> Any:
        """懒加载 Bucket 客户端（凭证变化需进程重启）。"""
        try:
            import oss2
        except ImportError as e:
            raise CustomException(msg="未安装 oss2，请执行 uv sync / pip install oss2") from e

        endpoint = settings.OSS_ENDPOINT.strip()
        auth = oss2.Auth(settings.OSS_ACCESS_KEY.strip(), settings.OSS_SECRET_KEY.strip())
        return oss2.Bucket(auth, endpoint, settings.OSS_BUCKET_NAME.strip())

    @classmethod
    def clear_cache(cls) -> None:
        """清除 Bucket 缓存（测试用）。"""
        cls._bucket.cache_clear()

    @classmethod
    def to_object_key(cls, rel_path: str | None) -> str:
        """相对路径 → 完整对象键。"""
        prefix = _normalize_prefix(settings.OSS_PREFIX)
        rel = _normalize_rel_path(rel_path)
        if not rel:
            return prefix.rstrip("/") if prefix else ""
        return f"{prefix}{rel}" if prefix else rel

    @classmethod
    def to_dir_prefix(cls, rel_path: str | None) -> str:
        """相对目录路径 → 列举用前缀（以 / 结尾，根为 OSS_PREFIX）。"""
        prefix = _normalize_prefix(settings.OSS_PREFIX)
        rel = _normalize_rel_path(rel_path)
        if not rel:
            return prefix
        return f"{prefix}{rel}/"

    @classmethod
    def relative_from_key(cls, key: str) -> str:
        """完整对象键 → 相对路径。"""
        prefix = _normalize_prefix(settings.OSS_PREFIX)
        k = key.lstrip("/")
        if prefix and k.startswith(prefix):
            k = k[len(prefix) :]
        return k.strip("/")

    @classmethod
    def default_bucket_host(cls) -> str:
        """默认 Bucket 公网主机（无协议），如 ``stabx-dev.oss-cn-beijing.aliyuncs.com``。"""
        bucket = settings.OSS_BUCKET_NAME.strip()
        endpoint = settings.OSS_ENDPOINT.strip().rstrip("/")
        parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}")
        host = (parsed.netloc or parsed.path).strip()
        if host.startswith("oss-") and bucket:
            return f"{bucket}.{host}"
        return host

    @classmethod
    def canonical_url(cls, key: str) -> str:
        """持久化用的无签名绝对 URL（自定义域名优先，否则默认 Bucket 域名）。"""
        k = key.lstrip("/")
        custom = settings.OSS_CUSTOM_DOMAIN.strip().rstrip("/")
        if custom:
            return f"{custom}/{k}"
        host = cls.default_bucket_host()
        scheme = "https"
        endpoint = settings.OSS_ENDPOINT.strip()
        if endpoint.startswith("http://"):
            scheme = "http"
        return f"{scheme}://{host}/{k}"

    @classmethod
    def key_from_url_or_path(cls, value: str) -> str | None:
        """从对象键、相对路径或本桶 URL 解析对象键；非本桶资源返回 None。"""
        raw = (value or "").strip()
        if not raw:
            return None
        if not raw.startswith(("http://", "https://")):
            try:
                return cls.to_object_key(raw)
            except CustomException:
                return None

        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lstrip("/")
        bucket = settings.OSS_BUCKET_NAME.strip()
        custom = settings.OSS_CUSTOM_DOMAIN.strip().rstrip("/")
        custom_host = urlparse(custom).netloc.lower() if custom else ""
        default_host = cls.default_bucket_host().lower()
        known_hosts = {h for h in (custom_host, default_host) if h}
        if host not in known_hosts:
            # ``bucket.oss-region.aliyuncs.com`` 变体或 path-style
            if bucket and (host.startswith(f"{bucket}.") or path.startswith(f"{bucket}/")):
                if path.startswith(f"{bucket}/"):
                    path = path[len(bucket) + 1 :]
            else:
                return None
        if bucket and path.startswith(f"{bucket}/"):
            path = path[len(bucket) + 1 :]
        return path or None

    @classmethod
    def to_storage_url(cls, value: str | None) -> str | None:
        """写入 DB 的稳定地址：剥离签名/缓存参数；本桶资源规范为 canonical URL。"""
        if value is None:
            return None
        raw = value.strip()
        if not raw:
            return raw
        key = cls.key_from_url_or_path(raw)
        if key and settings.OSS_READY:
            return cls.canonical_url(key)
        if not raw.startswith(("http://", "https://")):
            return raw
        parsed = urlparse(raw)
        kept = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in _OSS_EPHEMERAL_QUERY_KEYS
        ]
        query = urlencode(kept)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))

    @classmethod
    def public_or_signed_url(cls, key: str, *, expire: int | None = None) -> str:
        """生成浏览器可加载的访问 URL。

        - ``OSS_PUBLIC_READ=True``：自定义域名/默认域名直链（公有读桶）。
        - 否则（默认）：签名 URL；若配置了 ``OSS_CUSTOM_DOMAIN`` 则改写主机名。
        """
        k = key.lstrip("/")
        if settings.OSS_PUBLIC_READ:
            return cls.canonical_url(k)

        expires = expire if expire is not None else settings.OSS_SIGN_URL_EXPIRE_SECONDS
        bucket = cls._bucket()
        signed = bucket.sign_url("GET", k, expires)
        custom = settings.OSS_CUSTOM_DOMAIN.strip().rstrip("/")
        if not custom:
            return signed
        signed_parsed = urlparse(signed)
        custom_parsed = urlparse(custom if "://" in custom else f"https://{custom}")
        return urlunparse(
            (
                custom_parsed.scheme or "https",
                custom_parsed.netloc or custom_parsed.path,
                signed_parsed.path,
                "",
                signed_parsed.query,
                "",
            )
        )

    @classmethod
    def ensure_browser_url(cls, value: str | None, *, expire: int | None = None) -> str | None:
        """将库内头像/文件地址转为当前可加载 URL（私有桶重新签名）。"""
        if value is None:
            return None
        raw = value.strip()
        if not raw:
            return raw
        if not settings.OSS_READY:
            return raw
        key = cls.key_from_url_or_path(raw)
        if not key:
            return raw
        return cls.public_or_signed_url(key, expire=expire)

    @classmethod
    def _list_sync(cls, dir_prefix: str) -> list[OssListEntry]:
        """同步列举一层目录（delimiter=/）。"""
        import oss2

        bucket = cls._bucket()
        entries: list[OssListEntry] = []
        for obj in oss2.ObjectIterator(bucket, prefix=dir_prefix, delimiter="/"):
            key = obj.key
            is_prefix = bool(obj.is_prefix()) if callable(getattr(obj, "is_prefix", None)) else False
            if is_prefix or (key.endswith("/") and key != dir_prefix):
                name = key[len(dir_prefix) :].rstrip("/") if key.startswith(dir_prefix) else key.rstrip("/").rsplit("/", 1)[-1]
                if not name:
                    continue
                entries.append(
                    OssListEntry(name=name, key=key, is_dir=True, size=None, modified_time=None)
                )
                continue
            if key == dir_prefix:
                continue
            name = key[len(dir_prefix) :] if key.startswith(dir_prefix) else key.rsplit("/", 1)[-1]
            if not name or "/" in name:
                continue
            mtime = None
            if getattr(obj, "last_modified", None):
                mtime = datetime.fromtimestamp(obj.last_modified, tz=UTC)
            entries.append(
                OssListEntry(
                    name=name,
                    key=key,
                    is_dir=False,
                    size=int(getattr(obj, "size", 0) or 0),
                    modified_time=mtime,
                )
            )
        seen: set[str] = set()
        unique: list[OssListEntry] = []
        for e in entries:
            mark = f"{'d' if e.is_dir else 'f'}:{e.name}"
            if mark in seen:
                continue
            seen.add(mark)
            unique.append(e)
        return unique

    @classmethod
    async def list_dir(cls, rel_path: str | None = None) -> list[OssListEntry]:
        """异步列举目录。"""
        dir_prefix = cls.to_dir_prefix(rel_path)
        return await asyncio.to_thread(cls._list_sync, dir_prefix)

    @classmethod
    def _put_sync(cls, key: str, data: bytes, *, headers: dict[str, str] | None = None) -> None:
        bucket = cls._bucket()
        bucket.put_object(key, data, headers=headers or {})

    @classmethod
    async def put_bytes(cls, rel_path: str, data: bytes) -> str:
        """上传字节，返回对象键。"""
        key = cls.to_object_key(rel_path)
        await asyncio.to_thread(cls._put_sync, key, data)
        return key

    @classmethod
    def _get_sync(cls, key: str) -> bytes:
        bucket = cls._bucket()
        result = bucket.get_object(key)
        return result.read()

    @classmethod
    async def get_bytes(cls, rel_path: str) -> bytes:
        """下载对象内容。"""
        key = cls.to_object_key(rel_path)
        try:
            return await asyncio.to_thread(cls._get_sync, key)
        except Exception as e:
            log.error(f"OSS 下载失败: {e}")
            raise CustomException(msg="文件不存在或下载失败") from e

    @classmethod
    def _exists_sync(cls, key: str) -> bool:
        return bool(cls._bucket().object_exists(key))

    @classmethod
    async def exists(cls, rel_path: str) -> bool:
        """对象是否存在。"""
        key = cls.to_object_key(rel_path)
        if not key:
            return True
        return await asyncio.to_thread(cls._exists_sync, key)

    @classmethod
    def _delete_sync(cls, key: str) -> None:
        cls._bucket().delete_object(key)

    @classmethod
    def _delete_prefix_sync(cls, prefix: str) -> None:
        import oss2

        bucket = cls._bucket()
        for obj in oss2.ObjectIterator(bucket, prefix=prefix):
            bucket.delete_object(obj.key)

    @classmethod
    async def delete(cls, rel_path: str, *, is_dir: bool = False) -> None:
        """删除文件或目录前缀。"""
        if is_dir:
            prefix = cls.to_dir_prefix(rel_path)
            await asyncio.to_thread(cls._delete_prefix_sync, prefix)
        else:
            key = cls.to_object_key(rel_path)
            await asyncio.to_thread(cls._delete_sync, key)

    @classmethod
    def _copy_sync(cls, src_key: str, dst_key: str) -> None:
        bucket = cls._bucket()
        bucket.copy_object(settings.OSS_BUCKET_NAME.strip(), src_key, dst_key)

    @classmethod
    async def copy(cls, src_rel: str, dst_rel: str, *, is_dir: bool = False) -> None:
        """复制文件或目录。"""
        if not is_dir:
            src = cls.to_object_key(src_rel)
            dst = cls.to_object_key(dst_rel)
            await asyncio.to_thread(cls._copy_sync, src, dst)
            return
        import oss2

        src_prefix = cls.to_dir_prefix(src_rel)
        dst_prefix = cls.to_dir_prefix(dst_rel)

        def _copy_tree() -> None:
            bucket = cls._bucket()
            for obj in oss2.ObjectIterator(bucket, prefix=src_prefix):
                suffix = obj.key[len(src_prefix) :]
                await_key = f"{dst_prefix}{suffix}"
                bucket.copy_object(settings.OSS_BUCKET_NAME.strip(), obj.key, await_key)

        await asyncio.to_thread(_copy_tree)

    @classmethod
    async def move(cls, src_rel: str, dst_rel: str, *, is_dir: bool = False) -> None:
        """移动（复制后删除）。"""
        await cls.copy(src_rel, dst_rel, is_dir=is_dir)
        await cls.delete(src_rel, is_dir=is_dir)

    @classmethod
    async def create_dir(cls, rel_path: str) -> None:
        """创建目录占位对象（key 以 / 结尾）。"""
        key = cls.to_dir_prefix(rel_path)
        await asyncio.to_thread(cls._put_sync, key, b"")

    @classmethod
    def settings_node_config_json(cls) -> str:
        """生成存储节点 config JSON（不含密钥，仅引用全局配置）。"""
        return json.dumps(
            {
                "provider": "aliyun",
                "use_settings": True,
                "endpoint": settings.OSS_ENDPOINT,
                "bucket": settings.OSS_BUCKET_NAME,
                "region": settings.OSS_REGION,
                "prefix": settings.OSS_PREFIX,
                "custom_domain": settings.OSS_CUSTOM_DOMAIN or None,
            },
            ensure_ascii=False,
        )
