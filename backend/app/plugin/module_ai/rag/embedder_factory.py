"""
Embedder 工厂 - 按配置创建多类型嵌入模型
============================================

设计目标：支持多种 Embedder，满足不同部署场景：

| 类型               | 值                | 适用场景                                     |
| ------------------ | ----------------- | -------------------------------------------- |
| 本地 FastEmbed     | `fastembed`       | 默认；离线、免 API key、隐私好、启动快        |
| OpenAI 兼容 API    | `openai` / `openai-like` | 复用 ai_provider 供应商配置（DeepSeek/硅基流动/DashScope 等）|
| Ollama 本地        | `ollama`          | 本地 Ollama embedding 模型（如 nomic-embed-text）|
| SentenceTransformers | `sentence-transformer` | 本地 HF 模型（需安装 sentence-transformers）|

配置方式（优先级从高到低）：
1. `settings.RAG_EMBEDDER_TYPE`（env: RAG_EMBEDDER_TYPE）指定类型
2. `settings.RAG_EMBEDDER_*` 前缀配置项（如 RAG_EMBEDDER_MODEL / RAG_EMBEDDER_BASE_URL / RAG_EMBEDDER_API_KEY）
3. 若未指定类型，默认使用 `fastembed`（开箱即用）

OpenAI 兼容 API 的供应商接入：
- 可将 ai_provider 表中的一个供应商标记为 embedding 用途（vendor 为 openai/deepseek/siliconflow/dashscope 等），
  通过其 base_url + api_key + 一个支持 embedding 的模型（如 text-embedding-3-small）构建。
- 未显式配置时，可回退读取默认供应商（is_default=true）或环境变量 RAG_EMBEDDER_*。
"""

from functools import lru_cache
from typing import Any

from app.config.setting import settings
from app.core.logger import log

# 支持的 Embedder 类型 → 说明
SUPPORTED_EMBEDDER_TYPES: dict[str, str] = {
    "fastembed": "本地 FastEmbed（默认，免API key，离线）",
    "openai": "OpenAI 官方 API",
    "openai-like": "OpenAI 兼容 API（DeepSeek/硅基流动/DashScope/OneAPI 等）",
    "ollama": "Ollama 本地",
    "sentence-transformer": "SentenceTransformers 本地 HF 模型",
}


class AgnoEmbedderFactory:
    """Embedder 工厂：根据配置创建多种类型的嵌入模型。"""

    # ==================================================== #
    # Embedder 类型 → 构造参数（供各类型 builder 使用）
    # ==================================================== #

    @classmethod
    def _get_embedder_type(cls) -> str:
        """确定 Embedder 类型（配置优先，默认 fastembed）。"""
        embedder_type = (getattr(settings, "RAG_EMBEDDER_TYPE", "") or "").strip().lower()
        if not embedder_type:
            embedder_type = "fastembed"
        if embedder_type not in SUPPORTED_EMBEDDER_TYPES:
            log.warning(
                f"不支持的 Embedder 类型: {embedder_type!r}，回退使用 fastembed。"
                f"支持: {sorted(SUPPORTED_EMBEDDER_TYPES.keys())}"
            )
            embedder_type = "fastembed"
        return embedder_type

    # ==================================================== #
    # 各类 Embedder 构建
    # ==================================================== #

    @classmethod
    def _build_fastembed(cls) -> Any:
        """构建本地 FastEmbed（默认方案，384维，无需 API key）。"""
        from agno.knowledge.embedder.fastembed import FastEmbedEmbedder

        model = getattr(settings, "RAG_EMBEDDER_MODEL", "") or "BAAI/bge-small-en-v1.5"
        return FastEmbedEmbedder(id=model)

    @classmethod
    def _build_openai_like(cls) -> Any:
        """
        构建 OpenAI 兼容 API Embedder。

        优先复用 ai_provider 表配置（可通过 RAG_EMBEDDER_PROVIDER_ID 指定），
        否则回退 RAG_EMBEDDER_BASE_URL / RAG_EMBEDDER_API_KEY / RAG_EMBEDDER_MODEL 环境变量。
        """
        from agno.knowledge.embedder.openai_like import OpenAILikeEmbedder

        base_url = getattr(settings, "RAG_EMBEDDER_BASE_URL", "") or ""
        api_key = getattr(settings, "RAG_EMBEDDER_API_KEY", "") or ""
        model = getattr(settings, "RAG_EMBEDDER_MODEL", "") or "text-embedding-3-small"

        # 若未显式配置 base_url，尝试从 ai_provider 读取
        if not base_url:
            provider = cls._get_embedding_provider()
            if provider:
                base_url = provider.get("base_url") or ""
                api_key = provider.get("api_key") or ""
                model = provider.get("model_key") or model

        if not api_key:
            log.warning("OpenAI 兼容 Embedder 未配置 API key，使用 OpenAILikeEmbedder 的默认（not-provided）")

        log.info(
            f"构建 OpenAI 兼容 Embedder: model={model} base_url={base_url or '(默认)'}"
        )
        return OpenAILikeEmbedder(
            id=model,
            base_url=base_url or None,
            api_key=api_key or None,
        )

    @classmethod
    def _build_openai(cls) -> Any:
        """构建 OpenAI 官方 Embedder（需 OpenAI API key）。"""
        from agno.knowledge.embedder.openai import OpenAIEmbedder

        api_key = getattr(settings, "RAG_EMBEDDER_API_KEY", "") or None
        model = getattr(settings, "RAG_EMBEDDER_MODEL", "") or "text-embedding-3-small"
        base_url = getattr(settings, "RAG_EMBEDDER_BASE_URL", "") or None
        return OpenAIEmbedder(
            id=model,
            api_key=api_key,
            base_url=base_url,
        )

    @classmethod
    def _build_ollama(cls) -> Any:
        """构建 Ollama 本地 Embedder（需安装 ollama SDK 与模型）。"""
        try:
            from agno.knowledge.embedder.ollama import OllamaEmbedder
        except ImportError as e:
            raise ImportError(
                "Ollama Embedder 需要安装 ollama SDK: `pip install ollama`。"
            ) from e

        model = getattr(settings, "RAG_EMBEDDER_MODEL", "") or "nomic-embed-text"
        host = getattr(settings, "RAG_EMBEDDER_BASE_URL", "") or None
        return OllamaEmbedder(id=model, host=host)

    @classmethod
    def _build_sentence_transformer(cls) -> Any:
        """构建 SentenceTransformers 本地 Embedder（需安装 sentence-transformers）。"""
        try:
            from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder
        except ImportError as e:
            raise ImportError(
                "SentenceTransformers Embedder 需要安装: `pip install sentence-transformers`。"
            ) from e

        model = getattr(settings, "RAG_EMBEDDER_MODEL", "") or "sentence-transformers/all-MiniLM-L6-v2"
        return SentenceTransformerEmbedder(id=model)

    # ==================================================== #
    # 供应商接入（从 ai_provider 读取 embedding 用途配置）
    # ==================================================== #

    @classmethod
    def _get_embedding_provider(cls) -> dict[str, Any] | None:
        """
        从 ai_provider 表中查找用于 embedding 的供应商。

        选择优先级：
        1. 显式配置 RAG_EMBEDDER_PROVIDER_ID 指向的供应商
        2. 默认供应商（is_default=true）中 vendor 为 openai/deepseek/siliconflow/dashscope 等的
        3. 任意 vendor 为 openai/deepseek/siliconflow/dashscope 的供应商

        返回:
        - dict | None: {provider_id, base_url, api_key, model_key}
        """
        try:
            # 同步上下文使用同步会话会报错，这里通过异步方式获取
            import asyncio

            from sqlalchemy import select

            from app.core.database import async_db_session
            from app.plugin.module_ai.model.model import AiModelModel, AiProviderModel

            async def _fetch():
                async with async_db_session() as db:
                    provider_id_cfg = getattr(settings, "RAG_EMBEDDER_PROVIDER_ID", None)
                    # 1. 显式指定供应商
                    if provider_id_cfg:
                        stmt = (
                            select(AiProviderModel, AiModelModel)
                            .join(AiModelModel, AiModelModel.provider_id == AiProviderModel.id)
                            .where(
                                AiProviderModel.id == int(provider_id_cfg),
                                AiProviderModel.is_deleted.is_(False),
                                AiModelModel.is_deleted.is_(False),
                            )
                            .limit(1)
                        )
                        result = await db.execute(stmt)
                        row = result.first()
                        if row:
                            provider, model = row
                            return {
                                "provider_id": provider.id,
                                "base_url": provider.base_url,
                                "api_key": provider.api_key,
                                "model_key": model.model_key,
                            }

                    # 2/3. 按 vendor 匹配 embedding 供应商
                    embed_vendors = ("openai", "deepseek", "siliconflow", "dashscope", "moonshot")
                    stmt = (
                        select(AiProviderModel, AiModelModel)
                        .join(AiModelModel, AiModelModel.provider_id == AiProviderModel.id)
                        .where(
                            AiProviderModel.vendor.in_(embed_vendors),
                            AiProviderModel.is_deleted.is_(False),
                            AiModelModel.is_deleted.is_(False),
                        )
                        .order_by(AiProviderModel.is_default.desc(), AiProviderModel.id)
                        .limit(1)
                    )
                    result = await db.execute(stmt)
                    row = result.first()
                    if row:
                        provider, model = row
                        return {
                            "provider_id": provider.id,
                            "base_url": provider.base_url,
                            "api_key": provider.api_key,
                            "model_key": model.model_key,
                        }
                    return None

            return asyncio.run(_fetch())
        except Exception as e:
            log.warning(f"读取 embedding 供应商配置失败（忽略）: {e}")
            return None

    # ==================================================== #
    # 工厂入口
    # ==================================================== #

    @classmethod
    def build_embedder(cls) -> Any:
        """
        根据配置创建 Embedder 实例。

        返回:
        - Any: agno Embedder 实例（FastEmbedEmbedder / OpenAILikeEmbedder / OllamaEmbedder 等）。
        """
        embedder_type = cls._get_embedder_type()

        if embedder_type == "openai-like":
            return cls._build_openai_like()
        if embedder_type == "openai":
            return cls._build_openai()
        if embedder_type == "ollama":
            return cls._build_ollama()
        if embedder_type == "sentence-transformer":
            return cls._build_sentence_transformer()

        # 默认 fastembed
        embedder = cls._build_fastembed()
        log.info(f"构建 Embedder: 类型={embedder_type} 实例={type(embedder).__name__}")
        return embedder


@lru_cache
def get_embedder() -> Any:
    """获取 Embedder 实例（单例缓存）。"""
    return AgnoEmbedderFactory.build_embedder()
