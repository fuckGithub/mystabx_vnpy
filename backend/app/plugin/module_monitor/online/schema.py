from fastapi import Query

from app.common.enums import QueueEnum
from app.core.auth.session import SessionInfo


# 继承内核 app.core.auth.session.SessionInfo，字段与内核完全一致（零新增字段）。
# 类 docstring 保持与迁移前逐字一致：pydantic 会把类 docstring 提升为 JSON Schema
# 的 description，追加说明会改写对外 OpenAPI 文本；机制说明放这里而非 docstring。
class OnlineOutSchema(SessionInfo):
    """
    在线用户对应pydantic模型
    """

    pass


class OnlineQueryParam:
    """在线用户查询参数"""

    def __init__(
        self,
        name: str | None = Query(None, description="登录名称"),
        ipaddr: str | None = Query(None, description="登陆IP地址"),
        login_location: str | None = Query(None, description="登录所属地"),
    ) -> None:

        # 模糊查询字段
        self.name = (QueueEnum.like.value, f"%{name}%") if name else None
        self.login_location = (QueueEnum.like.value, f"%{login_location}%") if login_location else None
        self.ipaddr = (QueueEnum.like.value, f"%{ipaddr}%") if ipaddr else None
