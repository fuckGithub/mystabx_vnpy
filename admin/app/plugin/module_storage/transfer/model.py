"""传输任务模型。"""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class StorageTransferModel(ModelMixin, UserMixin):
    """传输任务：从源节点到目标节点的数据传输。"""

    __tablename__: str = "storage_transfer"
    __table_args__: dict[str, str] = {"comment": "传输任务表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务名称")
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="源存储节点ID")
    target_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="目标存储节点ID")
    source_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="源路径")
    target_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="目标路径")
    transfer_status: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="传输状态: 0待执行 1执行中 2成功 3失败"
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="进度百分比")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
