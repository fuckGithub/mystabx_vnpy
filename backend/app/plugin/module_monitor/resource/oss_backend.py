"""文件管理（资源模块）的 OSS 后端实现。"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import UploadFile

from app.core.exceptions import CustomException
from app.core.logger import log
from app.utils.oss_util import OssUtil, _normalize_rel_path
from app.utils.upload_util import DANGEROUS_EXTENSIONS, MIME_TYPE_MAPPING

from .schema import (
    ResourceCopySchema,
    ResourceCreateDirSchema,
    ResourceMoveSchema,
    ResourceRenameSchema,
    ResourceSearchQueryParam,
    ResourceUploadSchema,
)

MAX_UPLOAD_SIZE = 100 * 1024 * 1024


def _entry_to_info(name: str, rel: str, *, is_dir: bool, size: int | None, mtime: datetime | None) -> dict[str, Any]:
    """构造与本地磁盘一致的资源信息字典。"""
    key = OssUtil.to_object_key(rel) if not is_dir else OssUtil.to_dir_prefix(rel)
    file_url = OssUtil.public_or_signed_url(key.rstrip("/") if not is_dir else key)
    ts = mtime.isoformat() if mtime else None
    return {
        "name": name,
        "file_url": file_url,
        "relative_path": rel,
        "is_file": not is_dir,
        "is_dir": is_dir,
        "size": size,
        "created_time": ts,
        "modified_time": ts,
        "is_hidden": name.startswith("."),
    }


class OssResourceBackend:
    """资源管理 OSS 实现。"""

    @classmethod
    async def list_resources(
        cls,
        search: ResourceSearchQueryParam | None = None,
        order_by: str | None = None,
        base_url: str | None = None,
    ) -> list[dict]:
        """列举当前路径下的资源。"""
        _ = base_url
        path = None
        if search and hasattr(search, "path") and search.path and isinstance(search.path, str):
            path = search.path
        entries = await OssUtil.list_dir(path)
        results: list[dict] = []
        for e in entries:
            if e.name.startswith("."):
                continue
            rel = f"{_normalize_rel_path(path)}/{e.name}".strip("/") if path else e.name
            info = _entry_to_info(
                e.name,
                rel,
                is_dir=e.is_dir,
                size=e.size,
                mtime=e.modified_time,
            )
            if search and hasattr(search, "name") and search.name and search.name[1]:
                keyword = str(search.name[1]).lower()
                if keyword not in info["name"].lower():
                    continue
            results.append(info)
        results = sorted(results, key=lambda x: x.get("name", ""))
        return results

    @classmethod
    async def upload(
        cls,
        file: UploadFile,
        target_path: str | None = None,
        base_url: str | None = None,
    ) -> dict:
        """上传到 OSS。"""
        _ = base_url
        if not file or not file.filename:
            raise CustomException(msg="请选择要上传的文件")

        from .service import ResourceService

        safe_filename = ResourceService._sanitize_filename(file.filename)
        if "." not in safe_filename:
            raise CustomException(msg="无法识别文件类型")
        ext = os.path.splitext(safe_filename)[1].lower()
        if ext in DANGEROUS_EXTENSIONS:
            raise CustomException(msg=f"不允许上传此类型的文件: {ext}")

        content = await file.read()
        if len(content) > MAX_UPLOAD_SIZE:
            raise CustomException(msg=f"文件太大，最大支持{MAX_UPLOAD_SIZE // (1024 * 1024)}MB")

        detected = ResourceService._detect_file_type(content)
        if detected:
            expected = MIME_TYPE_MAPPING.get(detected, "")
            if expected and expected != ext:
                log.warning(f"文件类型不匹配: 声明={ext}, 检测={detected}")

        parent = _normalize_rel_path(target_path)
        rel = f"{parent}/{safe_filename}".strip("/") if parent else safe_filename

        # 重名追加序号
        counter = 1
        base_name, extension = os.path.splitext(safe_filename)
        candidate = rel
        while await OssUtil.exists(candidate):
            safe_filename = f"{base_name}_{counter}{extension}"
            candidate = f"{parent}/{safe_filename}".strip("/") if parent else safe_filename
            counter += 1
        rel = candidate

        key = await OssUtil.put_bytes(rel, content)
        file_url = OssUtil.public_or_signed_url(key)
        log.info(f"OSS 上传成功: {rel}")
        return ResourceUploadSchema(
            filename=safe_filename,
            file_url=file_url,
            file_size=len(content),
            upload_time=datetime.now(),
        ).model_dump(mode="json")

    @classmethod
    async def download_bytes(cls, file_path: str) -> tuple[bytes, str]:
        """下载文件内容与文件名。"""
        rel = _normalize_rel_path(file_path)
        if not rel:
            raise CustomException(msg="请选择要下载的文件")
        data = await OssUtil.get_bytes(rel)
        return data, os.path.basename(rel)

    @classmethod
    async def delete(cls, paths: list[str]) -> None:
        """删除文件或目录。"""
        if not paths:
            raise CustomException(msg="删除失败，删除路径不能为空")
        for path in paths:
            rel = _normalize_rel_path(path)
            if not rel:
                raise CustomException(msg="不能删除根目录")
            # 若存在同名目录前缀则按目录删
            dir_prefix = OssUtil.to_dir_prefix(rel)
            file_key = OssUtil.to_object_key(rel)
            # 简单策略：先试文件，再清前缀
            if await OssUtil.exists(rel):
                await OssUtil.delete(rel, is_dir=False)
            await OssUtil.delete(rel, is_dir=True)
            log.info(f"OSS 删除: file={file_key} dir={dir_prefix}")

    @classmethod
    async def move(cls, data: ResourceMoveSchema) -> None:
        """移动。"""
        src = _normalize_rel_path(data.source_path)
        dst = _normalize_rel_path(data.target_path)
        if not src or not dst:
            raise CustomException(msg="源/目标路径无效")
        is_dir = not await OssUtil.exists(src)
        await OssUtil.move(src, dst, is_dir=is_dir)

    @classmethod
    async def copy(cls, data: ResourceCopySchema) -> None:
        """复制。"""
        src = _normalize_rel_path(data.source_path)
        dst = _normalize_rel_path(data.target_path)
        if not src or not dst:
            raise CustomException(msg="源/目标路径无效")
        is_dir = not await OssUtil.exists(src)
        await OssUtil.copy(src, dst, is_dir=is_dir)

    @classmethod
    async def rename(cls, data: ResourceRenameSchema) -> None:
        """重命名。"""
        from .service import ResourceService

        old = _normalize_rel_path(data.old_path)
        if not old:
            raise CustomException(msg="路径无效")
        safe_name = ResourceService._sanitize_filename(data.new_name)
        parent = old.rsplit("/", 1)[0] if "/" in old else ""
        new_rel = f"{parent}/{safe_name}".strip("/") if parent else safe_name
        is_dir = not await OssUtil.exists(old)
        await OssUtil.move(old, new_rel, is_dir=is_dir)

    @classmethod
    async def create_dir(cls, data: ResourceCreateDirSchema) -> None:
        """新建目录。"""
        from .service import ResourceService

        parent = _normalize_rel_path(data.parent_path)
        safe_name = ResourceService._sanitize_filename(data.dir_name)
        rel = f"{parent}/{safe_name}".strip("/") if parent else safe_name
        await OssUtil.create_dir(rel)
