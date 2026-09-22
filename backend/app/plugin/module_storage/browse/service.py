"""存储浏览服务。"""

from app.core.logger import log

from .schema import BrowseQuery, BrowseResult


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
        # TODO: 根据节点类型（local/s3/ftp）实现实际浏览逻辑
        # 目前返回空列表作为占位
        log.info(f"浏览存储节点 {query.node_id} 路径: {query.path}")
        return BrowseResult(
            node_id=query.node_id,
            path=query.path,
            items=[],
        )
