"""存储浏览 Schema。"""

from pydantic import Field

from app.core.base_schema import BaseSchema


class BrowseQuery(BaseSchema):
    """浏览请求参数。"""

    node_id: int = Field(..., description="存储节点ID")
    path: str = Field(default="/", description="浏览路径")


class BrowseItem(BaseSchema):
    """单个文件/目录条目。"""

    name: str = Field(..., description="文件/目录名")
    type: str = Field(..., description="类型: file/directory")
    size: int | None = Field(default=None, description="文件大小（字节）")
    modified_time: str | None = Field(default=None, description="修改时间")


class BrowseResult(BaseSchema):
    """浏览结果。"""

    node_id: int
    path: str
    items: list[BrowseItem]
