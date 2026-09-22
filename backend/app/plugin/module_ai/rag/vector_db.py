"""PgVector 向量数据库初始化。"""
from functools import lru_cache
from typing import Any

from agno.vectordb.pgvector import PgVector

from app.config.setting import settings
from app.core.logger import log


@lru_cache
def get_vector_db(table_name: str = "ai_knowledge") -> PgVector:
    """
    获取 PgVector 向量数据库实例（单例缓存）。

    Embedder 由 AgnoEmbedderFactory 创建（支持 fastembed/openai-like/ollama 等多类型，
    见 embedder_factory.py），默认 fastembed（本地，384维，无需 API key）。

    参数:
    - table_name (str): 向量表名，默认 ai_knowledge

    返回:
    - PgVector: 向量数据库实例
    """
    from .embedder_factory import get_embedder

    embedder: Any = get_embedder()

    db = PgVector(
        table_name=table_name,
        schema="ai",  # 显式使用 ai schema，与 public 业务表分离
        db_url=settings.DB_URI,
        embedder=embedder,
    )
    log.info(
        f"PgVector 向量库初始化完成: table={table_name} schema=ai embedder={type(embedder).__name__}"
    )
    return db
