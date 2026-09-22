"""内核认证基元。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.auth.schema import AuthSchema, JWTPayloadSchema, UserLike
from app.core.auth.session import SessionInfo

if TYPE_CHECKING:
    # 仅为静态分析可见：``AuthPermission`` 由下方 PEP 562 ``__getattr__`` 运行期再导出，
    # 类型检查器跟踪不到这种再导出（否则会报 reportUnsupportedDunderAll）。
    # 放在 TYPE_CHECKING 里不会产生运行期导入，不影响避免循环导入的初衷。
    from app.core.auth.permission import AuthPermission

__all__ = ["AuthPermission", "AuthSchema", "JWTPayloadSchema", "SessionInfo", "UserLike"]


def __getattr__(name: str) -> Any:
    """惰性再导出 ``AuthPermission``（PEP 562）。

    ``app.core.auth.permission`` 需要 ``app.core.dependencies.get_current_user``，
    而后者又需要 ``app.core.auth.schema.AuthSchema`` —— 若在包初始化时就导入
    ``permission``，会形成「dependencies 部分初始化」的循环导入（触发与否取决于
    导入顺序）。故此处按需再导出，保证两种导入顺序都安全。

    参数:
    - name (str): 属性名。

    返回:
    - Any: 对应属性。

    异常:
    - AttributeError: 属性不存在时抛出。
    """
    if name == "AuthPermission":
        from app.core.auth.permission import AuthPermission

        return AuthPermission
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
