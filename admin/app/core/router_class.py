import json
import time
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute
from user_agents import parse

from app.config.setting import settings
from app.core.database import async_db_session
from app.core.logger import log
from app.core.plugin.contracts import OperationLogEntry
from app.core.plugin.slots import SLOT_LOG_OPERATION_SINK, get
from app.utils.ip_local_util import IpLocalUtil
from app.utils.sm_crypto_util import CommonCryptogramUtil

"""
在 FastAPI 中，route_class 参数用于自定义路由的行为。
通过设置 route_class，你可以定义一个自定义的路由类，从而在每个路由处理之前或之后执行特定的操作。
这对于日志记录、权限验证、性能监控等场景非常有用。
"""


_SIGNED_FIELDS = json.dumps(
    ["request_payload", "response_json", "process_time"],
    ensure_ascii=False,
)
"""操作日志签名所覆盖的字段名"""


def build_operation_log_signature(sign_data: str) -> tuple[str | None, str | None]:
    """
    生成操作日志的 SM2 签名（国密完整性保护）。

    受 ``settings.OPERATION_LOG_SIGN_ENABLE`` 控制。SM2 签名当前为纯 Python 实现，
    单次约 3.6 ms 且受 GIL 限制无法并行。

    ⚠️ **实测结论：放进线程执行无效，故保持同步调用。**
    ``asyncio.to_thread`` 在并发 ≥ 4 时对事件循环停顿无改善（实测 1.0×），
    单请求场景反而因线程切换变慢一倍（3.0 ms → 6.0 ms）——因为线程与事件循环
    争抢同一个 GIL。若要真正并行，只能走进程池；否则应直接关闭本开关。

    Args:
        sign_data: 待签名内容（请求载荷 | 响应 | 耗时）

    Returns:
        tuple[str | None, str | None]: (签名值, 被签字段 JSON)；
            开关关闭或签名失败时两者均为 ``None``。
    """
    if not settings.OPERATION_LOG_SIGN_ENABLE:
        return None, None
    try:
        signature = CommonCryptogramUtil.do_signature(sign_data)
    except Exception as e:
        log.warning(f"SM2日志签名失败: {e}")
        return None, None
    return signature, _SIGNED_FIELDS


class OperationLogRoute(APIRoute):
    """操作日志路由装饰器"""

    def get_route_handler(
        self,
    ) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        """
        自定义路由处理程序,在每个路由处理之前或之后执行特定的操作。

        参数:
        - request (Request): FastAPI请求对象。

        返回:
        - Response: FastAPI响应对象。
        """
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            """
            自定义路由处理程序,在每个路由处理之前或之后执行特定的操作。

            参数:
            - request (Request): FastAPI请求对象。
            描述:
            - 该方法在每个路由处理之前被调用,用于记录操作日志。
            返回:
            - Response: FastAPI响应对象。
            """
            start_time = time.time()
            # 请求前的处理
            response: Response = await original_route_handler(request)

            # 请求后的处理
            if not settings.OPERATION_LOG_RECORD:
                return response
            if request.method not in settings.OPERATION_RECORD_METHOD:
                return response
            route: APIRoute = request.scope.get("route", None)
            if route.name in settings.IGNORE_OPERATION_FUNCTION:
                return response

            user_agent = parse(request.headers.get("user-agent"))
            payload = b"{}"
            req_content_type = request.headers.get("Content-Type", "")

            if req_content_type and (
                req_content_type.startswith((
                    "multipart/form-data",
                    "application/x-www-form-urlencoded",
                ))
            ):
                form_data = await request.form()
                oper_param = "\n".join([f"{k}: {v}" for k, v in form_data.items()])
                payload = oper_param  # 直接使用字符串格式的参数
            else:
                payload = await request.body()
                path_params = request.path_params
                oper_param = {}

                # 处理请求体数据
                if payload:
                    try:
                        oper_param["body"] = json.loads(payload.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        oper_param["body"] = payload.decode("utf-8", errors="ignore")

                # 处理路径参数
                if path_params:
                    oper_param["path_params"] = dict(path_params)

                payload = json.dumps(oper_param, ensure_ascii=False)

                # 日志表请求参数字段长度最大为2000，因此在此处判断长度
                if len(payload) > 2000:
                    payload = "请求参数过长"

            response_data = (
                response.body
                if "application/json" in response.headers.get("Content-Type", "")
                else b"{}"
            )
            response_data_str = (
                response_data.decode()
                if isinstance(response_data, (bytes, bytearray))
                else str(response_data)
            )
            process_time = f"{(time.time() - start_time):.2f}s"

            # 获取当前用户ID,如果是登录接口则为空
            log_type = 1  # 1:登录日志 2:操作日志
            current_user_id = None

            # 优化：只在操作日志场景下获取current_user_id
            if "user_id" in request.scope:
                current_user_id = request.scope.get("user_id")
                log_type = 2

            # 获取操作人信息（由 dependencies.get_current_user / auth.create_token_service 注入 scope）
            username = request.scope.get("user_username")
            mobile = request.scope.get("user_mobile")
            login_platform = request.scope.get("login_type")

            request_ip = None
            x_forwarded_for = request.headers.get("X-Forwarded-For")
            if x_forwarded_for:
                # 取第一个 IP 地址，通常为客户端真实 IP
                request_ip = x_forwarded_for.split(",")[0].strip()
            else:
                # 若没有 X-Forwarded-For 头，则使用 request.client.host
                if request.client:
                    request_ip = request.client.host

            login_location = await IpLocalUtil.resolve_location_for_log(request_ip)

            # 判断请求是否来自api文档
            referer = request.headers.get("referer")
            request_from_swagger = referer and referer.endswith("docs")
            request_from_redoc = referer and referer.endswith("redoc")

            if request_from_swagger or request_from_redoc:
                # 如果请求来自api文档，则不记录日志
                pass
            else:
                # SM2 日志签名（国密完整性保护，可用 OPERATION_LOG_SIGN_ENABLE 关闭）
                sign_data = f"{payload}|{response_data_str}|{process_time}"
                signature, signed_fields = build_operation_log_signature(sign_data)
                # 日志落库走内核槽位：内核只收集 OperationLogEntry，存储实现由插件提供。
                sink = get(SLOT_LOG_OPERATION_SINK)
                if sink is None:
                    # 槽位缺失＝提供方插件未安装（最小部署可缺）：降级为「仅写文件日志」，
                    # 不在热路径记告警（启动期由 lifespan 统一告警）。
                    log.info(f"操作日志: {request.method} {request.url.path} {response.status_code}")
                else:
                    entry = OperationLogEntry(
                        type=log_type,
                        request_path=request.url.path,
                        request_method=request.method,
                        request_payload=payload,
                        request_ip=request_ip,
                        login_location=login_location,
                        request_os=user_agent.os.family,
                        request_browser=user_agent.browser.family,
                        response_code=response.status_code,
                        response_json=response_data_str,
                        process_time=process_time,
                        signature=signature,
                        signed_fields=signed_fields,
                        description=route.summary,
                        created_id=current_user_id,
                        updated_id=current_user_id,
                        username=username,
                        mobile=mobile,
                        login_platform=login_platform,
                    )
                    async with async_db_session() as session:
                        async with session.begin():
                            await sink.write(entry, session)

            return response

        return custom_route_handler
