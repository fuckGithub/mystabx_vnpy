"""存储工作流 Schema。"""

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_schema import UserBySchema
from app.core.validator import DateTimeStr


class StorageWorkflowCreateSchema(BaseModel):
    """创建存储工作流"""

    name: str = Field(..., max_length=100, description="工作流名称")
    code: str = Field(..., max_length=50, description="工作流编码")
    description: str | None = Field(default=None, max_length=500, description="描述")
    nodes_json: str | None = Field(default=None, description="节点配置 JSON")
    edges_json: str | None = Field(default=None, description="连线配置 JSON")


class StorageWorkflowUpdateSchema(StorageWorkflowCreateSchema):
    """更新存储工作流"""

    pass


class StorageWorkflowOutSchema(UserBySchema):
    """存储工作流输出"""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = Field(default=None, description="主键ID")
    uuid: str | None = Field(default=None, description="UUID")
    name: str = Field(description="工作流名称")
    code: str = Field(description="工作流编码")
    description: str | None = Field(default=None, description="描述")
    nodes_json: str | None = Field(default=None, description="节点配置 JSON")
    edges_json: str | None = Field(default=None, description="连线配置 JSON")
    status: str = Field(default="0", description="状态(0:正常 1:禁用)")
    created_time: DateTimeStr | None = Field(default=None, description="创建时间")
    updated_time: DateTimeStr | None = Field(default=None, description="更新时间")


class StorageWorkflowQueryParam:
    """存储工作流查询参数"""

    def __init__(
        self,
        name: str | None = Query(None, description="工作流名称"),
        code: str | None = Query(None, description="工作流编码"),
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
        self.code = (QueueEnum.like.value, code)
        self.status = (QueueEnum.eq.value, status)
        self.created_id = (QueueEnum.eq.value, created_id)
        self.updated_id = (QueueEnum.eq.value, updated_id)
        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
