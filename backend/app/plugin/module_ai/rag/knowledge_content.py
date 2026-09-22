"""系统知识文档加载与初始化。"""
from pathlib import Path
from typing import Any

from agno.knowledge.knowledge import Knowledge

from app.config.setting import settings
from app.core.logger import log

# 知识文档目录：随插件存放（module_ai/knowledge/），使插件保持"可整目录移除"——
# 删除 module_ai 即不再留下孤儿文档。
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"

# 知识库加载状态（进程内一次性标志）
_knowledge_loaded = False

# 降级告警状态（只打一次，避免每条聊天消息都刷日志）
_rag_unsupported_warned = False


def rag_supported() -> bool:
    """
    当前数据库后端是否支持向量检索。

    ``PgVector`` 仅支持 PostgreSQL，其他后端在构建/建表阶段即抛错。此处集中判定，
    调用方据此降级为"仅注入系统查询工具"，避免整个聊天链路不可用。

    返回:
    - bool: 支持返回 True；否则返回 False 并打印一次降级告警。
    """
    global _rag_unsupported_warned
    if settings.DATABASE_TYPE == "postgres":
        return True
    if not _rag_unsupported_warned:
        _rag_unsupported_warned = True
        log.warning(
            f"数据库后端为 {settings.DATABASE_TYPE}，不支持 PgVector 向量库；"
            "已跳过 RAG 知识库注入（聊天仍可用，仅启用系统查询工具）"
        )
    return False


async def load_system_knowledge(knowledge: Knowledge) -> None:
    """
    将系统文档加载到知识库向量表中。

    扫描插件内 ``module_ai/knowledge/`` 下所有 .md 文件，逐个插入知识库。

    注意: agno 3.0 的 Content 类没有 content 参数，
    必须使用 knowledge.ainsert(text_content=...) 直接插入文本。

    参数:
    - knowledge (Knowledge): 系统知识库实例
    """
    if not KNOWLEDGE_DIR.exists():
        log.warning(f"知识库目录不存在: {KNOWLEDGE_DIR}")
        return

    md_files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    if not md_files:
        log.warning("未找到任何知识文档")
        return

    log.info(f"开始加载 {len(md_files)} 个知识文档...")
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8").strip()
        if not content:
            continue

        # 从文档中提取标题作为名称
        name = _extract_title(content, md_file.stem)

        await knowledge.ainsert(
            name=name,
            description=f"FastapiAdmin 系统文档：{name}",
            text_content=content,
        )
        log.info(f"✅ 已加载文档: {name}")

    log.info("系统知识文档加载完成")


async def ensure_knowledge_loaded(knowledge: Knowledge) -> None:
    """
    确保知识库已加载（幂等，进程内只加载一次）。

    参数:
    - knowledge (Knowledge): 系统知识库实例
    """
    global _knowledge_loaded
    if _knowledge_loaded:
        return
    try:
        await load_system_knowledge(knowledge)
        _knowledge_loaded = True
    except Exception as e:
        log.error(f"知识库加载失败: {e}")


def _extract_title(content: str, fallback: str) -> str:
    """从 Markdown 内容中提取标题。"""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


async def get_knowledge_context(knowledge: Knowledge, query: str, max_results: int = 5) -> str:
    """
    检索知识库并返回上下文文本（供自定义检索时使用）。

    参数:
    - knowledge (Knowledge): 系统知识库实例
    - query (str): 查询文本
    - max_results (int): 最大返回结果数

    返回:
    - str: 拼接的检索结果上下文
    """
    try:
        results: list[Any] = knowledge.search(query, max_results=max_results)
        if not results:
            return ""
        parts = []
        for doc in results:
            content = getattr(doc, "content", None) or str(doc)
            name = getattr(doc, "name", None) or ""
            parts.append(f"【{name}】\n{content}" if name else content)
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        log.error(f"知识库检索失败: {e}")
        return ""
