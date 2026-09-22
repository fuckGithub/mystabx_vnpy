"""系统知识库初始化与管理。"""
from typing import Any

from agno.knowledge.knowledge import Knowledge

from app.core.logger import log


def get_knowledge(vector_db: Any | None = None) -> Knowledge:
    """
    获取系统知识库实例。

    参数:
    - vector_db: 向量库实例（PgVector），为 None 时自动创建

    返回:
    - Knowledge: 系统知识库实例
    """
    if vector_db is None:
        from .vector_db import get_vector_db

        vector_db = get_vector_db()

    kb = Knowledge(
        name="FastapiAdmin 系统知识库",
        description="FastapiAdmin 管理后台系统的操作指南、功能说明和使用文档",
        vector_db=vector_db,
        max_results=5,
    )
    log.info("系统知识库实例创建完成")
    return kb
