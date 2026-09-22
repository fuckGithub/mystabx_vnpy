"""传输任务 Schema。"""

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema, UserBySchema
from app.core.validator import DateTimeStr


class StorageTransferCreateSchema(BaseModel):
    """传输任务创建模型。"""

    name: str = Field(..., max_length=100, description="任务名称")
    source_id: int = Field(..., description="源存储节点ID")
    target_id: int = Field(..., description="目标存储节点ID")
    source_path: str | None = Field(default=None, max_length=500, description="源路径")
    target_path: str | None = Field(default=None, max_length=500, description="目标路径")
    transfer_status: int = Field(default=0, description="传输状态: 0待执行 1执行中 2成功 3失败")
    progress: int = Field(default=0, ge=0, le=100, description="进度百分比")
    error_msg: str | None = Field(default=None, description="错误信息")
    description: str | None = Field(default=None, max_length=500, description="描述")


class StorageTransferUpdateSchema(StorageTransferCreateSchema):
    """传输任务更新模型。"""


class StorageTransferOutSchema(StorageTransferCreateSchema, BaseSchema, UserBySchema):
    """传输任务响应模型。"""

    model_config = ConfigDict(from_attributes=True)


class StorageTransferQueryParam:
    """传输任务查询参数。"""

    def __init__(
        self,
        name: str | None = Query(None, description="任务名称"),
        source_id: int | None = Query(None, description="源存储节点ID"),
        target_id: int | None = Query(None, description="目标存储节点ID"),
        transfer_status: int | None = Query(None, description="传输状态"),
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
        self.source_id = (QueueEnum.eq.value, source_id)
        self.target_id = (QueueEnum.eq.value, target_id)
        self.transfer_status = (QueueEnum.eq.value, transfer_status)
        self.status = (QueueEnum.eq.value, status)
        self.created_id = (QueueEnum.eq.value, created_id)
        self.updated_id = (QueueEnum.eq.value, updated_id)

        if created_time and len(created_time) == 2:
            self.created_time = (QueueEnum.between.value, (created_time[0], created_time[1]))
        if updated_time and len(updated_time) == 2:
            self.updated_time = (QueueEnum.between.value, (updated_time[0], updated_time[1]))
