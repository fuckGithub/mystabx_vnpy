"""存储工作流模型。"""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class StorageWorkflowModel(ModelMixin, UserMixin):
    """存储工作流：定义源→目标的自动化传输流程。"""

    __tablename__: str = "storage_workflow"
    __table_args__ = (
        UniqueConstraint("code", name="uq_storage_workflow_code"),
        {"comment": "存储工作流表"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="工作流名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="工作流编码")
    nodes_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="节点配置 JSON")
    edges_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="连线配置 JSON")
