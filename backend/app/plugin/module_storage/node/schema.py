"""存储节点 Schema。"""

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema, UserBySchema
from app.core.validator import DateTimeStr


class StorageNodeCreateSchema(BaseModel):
    """存储节点创建模型。"""

    name: str = Field(..., max_length=100, description="节点名称")
    type: str = Field(..., max_length=50, description="存储类型: local/s3/ftp/sftp")
    config: str | None = Field(default=None, description="连接配置 JSON")
    description: str | None = Field(default=None, max_length=500, description="描述")


class StorageNodeUpdateSchema(StorageNodeCreateSchema):
    """存储节点更新模型。"""


class StorageNodeOutSchema(StorageNodeCreateSchema, BaseSchema, UserBySchema):
    """存储节点响应模型。"""

    model_config = ConfigDict(from_attributes=True)


class StorageNodeQueryParam:
    """存储节点查询参数。"""

    def __init__(
        self,
        name: str | None = Query(None, description="节点名称"),
        type: str | None = Query(None, description="存储类型"),
        status: str | None = Query(None, description="状态"),
        created_time: list[DateTimeStr] | None = Query(
            None,
            description="创建时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
        updated_time: list[DateTimeStr] | None = Query(
            None,
            description="更新时间范围",
            examples=["2025-01-01 00:00:00", "2025-12-31 23:59:59"],
        ),
        created_id: int | None = Query(None, description="创建人"),
        updated_id: int | None = Query(None, description="更新人"),
    ) -> None:
        self.name = (QueueEnum.like.value, name)
        self.type = (QueueEnum.eq.value, type)
        self.status = (QueueEnum.eq.value, status)
        self.created_id = (QueueEnum.eq.value, created_id)
        self.updated_id = (QueueEnum.eq.value, updated_id)

        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
