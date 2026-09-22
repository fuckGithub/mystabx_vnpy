"""内核会话信息模型。

登录链路（``module_system.auth.service``）需要把会话信息序列化后写入 JWT 的
``sub`` 并落 Redis；此前该模型定义在 ``module_monitor.online.schema`` 中，使核心
业务模块反向依赖监控插件。模型迁入内核后，监控插件改为继承本模型。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.validator import DateTimeStr


class SessionInfo(BaseModel):
    """登录会话信息，序列化后写入 JWT 的 ``sub`` 并落 Redis 会话。

    字段顺序与必填性等价于原 ``module_monitor.online.schema.OnlineOutSchema``，
    ``login_time`` 使用内核 ``DateTimeStr`` 以保证 JSON 序列化格式
    （``DATETIME_DISPLAY_FMT``）稳定。
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="用户名称")
    session_id: str = Field(..., description="会话编号")
    user_id: int = Field(..., description="用户ID")
    user_name: str = Field(..., description="用户名")
    ipaddr: str | None = Field(default=None, description="登陆IP地址")
    login_location: str | None = Field(default=None, description="登录所属地")
    os: str | None = Field(default=None, description="操作系统")
    browser: str | None = Field(default=None, description="浏览器")
    login_time: DateTimeStr | None = Field(default=None, description="登录时间")
    login_type: str | None = Field(default=None, description="登录类型 PC端 | 移动端")
