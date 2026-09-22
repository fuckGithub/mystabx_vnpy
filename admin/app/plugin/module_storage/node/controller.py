"""存储节点控制器。"""

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
    StorageNodeCreateSchema,
    StorageNodeOutSchema,
    StorageNodeQueryParam,
    StorageNodeUpdateSchema,
)
from .service import StorageNodeService

StorageNodeRouter = APIRouter(route_class=OperationLogRoute, prefix="/node", tags=["存储节点管理"])


@StorageNodeRouter.get(
    "/list",
    summary="查询存储节点列表",
    description="分页查询存储节点",
    response_model=ResponseSchema[list[StorageNodeOutSchema]],
)
async def get_obj_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[StorageNodeQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:node:query"]))],
) -> JSONResponse:
    """查询存储节点列表。"""
    result_dict = await StorageNodeService.get_node_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("查询存储节点列表成功")
    return SuccessResponse(data=result_dict, msg="查询存储节点列表成功")


@StorageNodeRouter.get(
    "/detail/{id}",
    summary="获取存储节点详情",
    description="获取存储节点详情",
    response_model=ResponseSchema[StorageNodeOutSchema],
)
async def get_obj_detail_controller(
    id: Annotated[int, Path(description="节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:node:query"]))],
) -> JSONResponse:
    """获取存储节点详情。"""
    result_dict = await StorageNodeService.get_node_detail_service(id=id, auth=auth)
    log.info(f"获取存储节点详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="获取存储节点详情成功")


@StorageNodeRouter.post(
    "/create",
    summary="创建存储节点",
    description="创建存储节点",
    response_model=ResponseSchema[StorageNodeOutSchema],
)
async def create_obj_controller(
    data: StorageNodeCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:node:create"]))],
) -> JSONResponse:
    """创建存储节点。"""
    result_dict = await StorageNodeService.create_node_service(auth=auth, data=data)
    log.info(f"创建存储节点成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="创建存储节点成功")


@StorageNodeRouter.put(
    "/update/{id}",
    summary="修改存储节点",
    description="修改存储节点",
    response_model=ResponseSchema[StorageNodeOutSchema],
)
async def update_obj_controller(
    data: StorageNodeUpdateSchema,
    id: Annotated[int, Path(description="节点ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:node:update"]))],
) -> JSONResponse:
    """修改存储节点。"""
    result_dict = await StorageNodeService.update_node_service(auth=auth, id=id, data=data)
    log.info(f"修改存储节点成功: {result_dict}")
    return SuccessResponse(data=result_dict, msg="修改存储节点成功")


@StorageNodeRouter.delete(
    "/delete",
    summary="删除存储节点",
    description="删除存储节点",
    response_model=ResponseSchema[None],
)
async def delete_obj_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_storage:node:delete"]))],
) -> JSONResponse:
    """删除存储节点。"""
    await StorageNodeService.delete_node_service(auth=auth, ids=ids)
    log.info(f"删除存储节点成功: {ids}")
    return SuccessResponse(msg="删除存储节点成功")
