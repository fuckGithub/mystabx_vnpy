"""
OperationLogModel 新增字段的单元测试。

验证 model.py 中新增的 username、mobile、login_platform 三个冗余字段
的定义是否正确，包括类型、可空性、注释等。
"""

from sqlalchemy import String

# ``OperationLogModel`` 以字符串名引用 ``UserModel`` 等关联模型，mapper 初始化需要
# 完整注册表；自 T18 起 ``module_system`` 不再急切聚合全部 controller，故按插件
# 声明的模型清单显式导入（与运行时同源）。
from app.core.plugin.loader import import_plugin_models
from app.plugin.module_system.log.model import OperationLogModel
from app.plugin.module_system.plugin import MODEL_PATHS

import_plugin_models("system", list(MODEL_PATHS))


class TestOperationLogModelNewFields:
    """验证 OperationLogModel 新增的三个冗余字段。"""

    def test_username_column_exists(self) -> None:
        """username 字段应定义为 String(64), nullable=True。"""
        column = OperationLogModel.__table__.columns.get("username")
        assert column is not None, "username 字段不存在"
        assert isinstance(column.type, String), f"username 应为 String 类型，实际为 {type(column.type)}"
        assert column.type.length == 64, f"username 长度应为 64，实际为 {column.type.length}"
        assert column.nullable is True, "username 应为 nullable=True"
        assert column.comment == "操作人账号（冗余）", f"username 注释不匹配: {column.comment}"

    def test_mobile_column_exists(self) -> None:
        """mobile 字段应定义为 String(11), nullable=True。"""
        column = OperationLogModel.__table__.columns.get("mobile")
        assert column is not None, "mobile 字段不存在"
        assert isinstance(column.type, String), f"mobile 应为 String 类型，实际为 {type(column.type)}"
        assert column.type.length == 11, f"mobile 长度应为 11，实际为 {column.type.length}"
        assert column.nullable is True, "mobile 应为 nullable=True"
        assert column.comment == "操作人手机号（冗余）", f"mobile 注释不匹配: {column.comment}"

    def test_login_platform_column_exists(self) -> None:
        """login_platform 字段应定义为 String(32), nullable=True。"""
        column = OperationLogModel.__table__.columns.get("login_platform")
        assert column is not None, "login_platform 字段不存在"
        assert isinstance(column.type, String), f"login_platform 应为 String 类型，实际为 {type(column.type)}"
        assert column.type.length == 32, f"login_platform 长度应为 32，实际为 {column.type.length}"
        assert column.nullable is True, "login_platform 应为 nullable=True"
        assert column.comment == "登录平台(PC/FLUTTER/UNIAPP)", f"login_platform 注释不匹配: {column.comment}"

    def test_new_fields_order(self) -> None:
        """三个新字段应位于 process_time 之后、signature 之前。"""
        columns = [c.name for c in OperationLogModel.__table__.columns]
        assert "process_time" in columns, "process_time 字段不存在"
        assert "signature" in columns, "signature 字段不存在"
        assert "username" in columns, "username 字段不存在"
        assert "mobile" in columns, "mobile 字段不存在"
        assert "login_platform" in columns, "login_platform 字段不存在"

        process_time_idx = columns.index("process_time")
        username_idx = columns.index("username")
        mobile_idx = columns.index("mobile")
        login_platform_idx = columns.index("login_platform")
        signature_idx = columns.index("signature")

        assert process_time_idx < username_idx, "username 应在 process_time 之后"
        assert username_idx < mobile_idx, "mobile 应在 username 之后"
        assert mobile_idx < login_platform_idx, "login_platform 应在 mobile 之后"
        assert login_platform_idx < signature_idx, "signature 应在 login_platform 之后"

    def test_model_create_instance(self) -> None:
        """验证可以创建包含新字段的模型实例。"""
        instance = OperationLogModel(
            type=2,
            request_path="/api/v1/test",
            request_method="GET",
            response_code=200,
            username="testuser",
            mobile="13800138000",
            login_platform="PC",
        )
        assert instance.username == "testuser"
        assert instance.mobile == "13800138000"
        assert instance.login_platform == "PC"

    def test_new_fields_default_none(self) -> None:
        """验证新字段默认值为 None。"""
        instance = OperationLogModel(
            type=2,
            request_path="/api/v1/test",
            request_method="GET",
            response_code=200,
        )
        assert instance.username is None
        assert instance.mobile is None
        assert instance.login_platform is None
