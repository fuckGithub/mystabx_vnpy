"""存储浏览控制器。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.auth.permission import AuthPermission
from app.core.router_class import OperationLogRoute

from .schema import BrowseQuery, BrowseResult
from .service import BrowseService

BrowseRouter = APIRouter(route_class=OperationLogRoute, prefix="/browse", tags=["存储浏览"])


@BrowseRouter.get(
    "/list",
    summary="浏览目录",
    description="浏览存储节点的指定路径，列出文件和目录",
    response_model=ResponseSchema[BrowseResult],
    dependencies=[Depends(AuthPermission(["module_storage:browse:query"]))],
)
async def browse_list_controller(query: Annotated[BrowseQuery, Depends()]) -> JSONResponse:
    """
    浏览目录

    参数:
        query: 浏览请求参数（node_id、path）

    返回:
        JSONResponse: 浏览结果
    """
    data = await BrowseService.browse(query)
    return SuccessResponse(data=data, msg="浏览目录成功")
