"""存储浏览服务。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.config.setting import settings
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.core.logger import log
from app.plugin.module_storage.node.model import StorageNodeModel
from app.utils.oss_util import OssUtil, _normalize_rel_path

from .schema import BrowseItem, BrowseQuery, BrowseResult


class BrowseService:
    """存储浏览服务。"""

    @classmethod
    async def browse(cls, query: BrowseQuery) -> BrowseResult:
        """浏览存储节点的指定路径。

        参数:
            query: 浏览请求参数

        返回:
            BrowseResult: 浏览结果
        """
        log.info(f"浏览存储节点 {query.node_id} 路径: {query.path}")
        async with async_db_session() as session:
            result = await session.execute(
                select(StorageNodeModel).where(
                    StorageNodeModel.id == query.node_id,
                    StorageNodeModel.is_deleted.is_(False),
                )
            )
            node = result.scalar_one_or_none()
        if not node:
            raise CustomException(msg="存储节点不存在")

        node_type = (node.type or "").lower()
        if node_type in ("oss", "s3", "aliyun"):
            return await cls._browse_oss(node, query)
        if node_type == "local":
            return await cls._browse_local(node, query)

        log.warning(f"暂不支持的存储类型: {node_type}")
        return BrowseResult(node_id=query.node_id, path=query.path, items=[])

    @classmethod
    async def _browse_oss(cls, node: StorageNodeModel, query: BrowseQuery) -> BrowseResult:
        """浏览 OSS / S3 兼容节点。"""
        config: dict = {}
        if node.config:
            try:
                config = json.loads(node.config)
            except json.JSONDecodeError:
                raise CustomException(msg="存储节点配置 JSON 无效")

        use_settings = bool(config.get("use_settings", True))
        if use_settings:
            if not OssUtil.is_ready():
                raise CustomException(msg="全局 OSS 未配置或未启用")
            entries = await OssUtil.list_dir(query.path)
        else:
            # 节点级凭证（较少用）：临时覆盖不可行，要求走全局配置
            raise CustomException(msg="请使用全局 OSS 配置（config.use_settings=true）")

        items: list[BrowseItem] = []
        for e in entries:
            mtime = e.modified_time.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S") if e.modified_time else None
            items.append(
                BrowseItem(
                    name=e.name,
                    type="directory" if e.is_dir else "file",
                    size=e.size,
                    modified_time=mtime,
                )
            )
        return BrowseResult(node_id=query.node_id, path=query.path or "/", items=items)

    @classmethod
    async def _browse_local(cls, node: StorageNodeModel, query: BrowseQuery) -> BrowseResult:
        """浏览本地目录节点。"""
        from pathlib import Path

        root = settings.UPLOAD_FILE_PATH
        if node.config:
            try:
                cfg = json.loads(node.config)
                if cfg.get("root"):
                    root = Path(cfg["root"])
            except json.JSONDecodeError:
                raise CustomException(msg="存储节点配置 JSON 无效")

        rel = _normalize_rel_path(query.path)
        target = root.joinpath(rel) if rel else root
        if not target.exists() or not target.is_dir():
            raise CustomException(msg="目录不存在")

        items: list[BrowseItem] = []
        for child in sorted(target.iterdir(), key=lambda p: p.name):
            if child.name.startswith("."):
                continue
            stat = child.stat()
            items.append(
                BrowseItem(
                    name=child.name,
                    type="directory" if child.is_dir() else "file",
                    size=None if child.is_dir() else stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                )
            )
        return BrowseResult(node_id=query.node_id, path=query.path or "/", items=items)
