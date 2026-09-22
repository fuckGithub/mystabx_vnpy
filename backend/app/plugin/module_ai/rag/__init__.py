"""
RAG 知识库模块。

导出:
- get_embedder: 获取 Embedder 实例（多类型支持）
- get_vector_db: 获取 PgVector 向量库实例
- get_knowledge: 获取 Knowledge 知识库实例
"""
from .embedder_factory import AgnoEmbedderFactory, get_embedder
from .knowledge_base import get_knowledge
from .vector_db import get_vector_db

__all__ = [
    "AgnoEmbedderFactory",
    "get_embedder",
    "get_knowledge",
    "get_vector_db",
]
