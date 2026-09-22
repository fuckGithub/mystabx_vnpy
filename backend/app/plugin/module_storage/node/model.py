"""存储节点模型。"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, UserMixin


class StorageNodeModel(ModelMixin, UserMixin):
    """存储节点：代表一个存储源（本地磁盘、S3、FTP 等）。"""

    __tablename__: str = "storage_node"
    __table_args__: dict[str, str] = {"comment": "存储节点表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by"]

    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="节点名称")
    type: Mapped[str] = mapped_column(String(50), nullable=False, comment="存储类型: local/oss/s3/ftp/sftp")
    config: Mapped[str | None] = mapped_column(Text, nullable=True, comment="连接配置 JSON")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="描述")
