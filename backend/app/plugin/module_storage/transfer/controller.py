"""传输任务控制器。"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.auth.permission import AuthPermission
from app.core.auth.schema import AuthSchema
from app.core.base_params import PaginationQueryParam
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import (
    StorageTransferCreateSchema,
    StorageTransferOutSchema,
    StorageTransferQueryParam,
    StorageTransferUpdateSchema,
)
from .service import StorageTransferService

StorageTransferRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/transfer", tags=["传输任务管理"]
)


@StorageTransferRouter.get(
    "/list",
    summary="查询传输任务列表",
    description="分页查询传输任务",
    response_model=ResponseSchema[list[StorageTransferOutSchema]],
)
async def get_obj_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[StorageTransferQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:transfer:query"]))],
) -> JSONResponse:
    """查询传输任务列表。"""
    result_dict = await StorageTransferService.get_transfer_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("查询传输任务列表成功")
    return SuccessResponse(data=result_dict, msg="查询传输任务列表成功")


@StorageTransferRouter.get(
    "/detail/{id}",
    summary="获取传输任务详情",
    description="获取传输任务详情",
    response_model=ResponseSchema[StorageTransferOutSchema],
)
async def get_obj_detail_controller(
    id: Annotated[int, Path(description="传输任务ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:transfer:query"]))],
) -> JSONResponse:
    """获取传输任务详情。"""
    result_dict = await StorageTransferService.get_transfer_detail_service(id=id, auth=auth)
    log.info(f"获取传输任务详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="获取传输任务详情成功")


@StorageTransferRouter.post(
    "/create",
    summary="创建传输任务",
    description="创建传输任务",
    response_model=ResponseSchema[StorageTransferOutSchema],
)
async def create_obj_controller(
    data: StorageTransferCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:transfer:create"]))],
) -> JSONResponse:
    """创建传输任务。"""
    result_dict = await StorageTransferService.create_transfer_service(auth=auth, data=data)
    log.info(f"创建传输任务成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="创建传输任务成功")


@StorageTransferRouter.put(
    "/update/{id}",
    summary="修改传输任务",
    description="修改传输任务",
    response_model=ResponseSchema[StorageTransferOutSchema],
)
async def update_obj_controller(
    data: StorageTransferUpdateSchema,
    id: Annotated[int, Path(description="传输任务ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:transfer:update"]))],
) -> JSONResponse:
    """修改传输任务。"""
    result_dict = await StorageTransferService.update_transfer_service(auth=auth, id=id, data=data)
    log.info(f"修改传输任务成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="修改传输任务成功")


@StorageTransferRouter.delete(
    "/delete",
    summary="删除传输任务",
    description="删除传输任务",
    response_model=ResponseSchema[None],
)
async def delete_obj_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:transfer:delete"]))],
) -> JSONResponse:
    """删除传输任务。"""
    await StorageTransferService.delete_transfer_service(auth=auth, ids=ids)
    log.info(f"删除传输任务成功: {ids}")
    return SuccessResponse(msg="删除传输任务成功")
