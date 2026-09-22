"""存储工作流 API 路由控制器。"""

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
    StorageWorkflowCreateSchema,
    StorageWorkflowOutSchema,
    StorageWorkflowQueryParam,
    StorageWorkflowUpdateSchema,
)
from .service import StorageWorkflowService

StorageWorkflowRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/workflow", tags=["存储工作流管理"]
)


@StorageWorkflowRouter.get(
    "/detail/{id}",
    summary="存储工作流详情",
    description="根据ID获取存储工作流详情",
    response_model=ResponseSchema[StorageWorkflowOutSchema],
)
async def get_workflow_detail_controller(
    id: Annotated[int, Path(description="工作流ID")],
    auth: Annotated[
        AuthSchema, Depends(AuthPermission(["module_storage:workflow:detail"]))
    ],
) -> JSONResponse:
    """
    根据 ID 获取存储工作流详情。

    参数:
    - id (int): 工作流 ID。
    - auth (AuthSchema): 认证信息。

    返回:
    - JSONResponse: 成功响应，data 为详情字典。
    """
    result_dict = await StorageWorkflowService.get_workflow_detail_service(auth=auth, id=id)
    log.info(f"获取存储工作流详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="获取存储工作流详情成功")


@StorageWorkflowRouter.get(
    "/list",
    summary="存储工作流列表",
    description="分页查询存储工作流列表",
    response_model=ResponseSchema[list[StorageWorkflowOutSchema]],
)
async def get_workflow_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[StorageWorkflowQueryParam, Depends()],
    auth: Annotated[
        AuthSchema, Depends(AuthPermission(["module_storage:workflow:query"]))
    ],
) -> JSONResponse:
    """
    分页查询存储工作流列表。

    参数:
    - page (PaginationQueryParam): 分页与排序参数。
    - search (StorageWorkflowQueryParam): 查询条件。
    - auth (AuthSchema): 认证信息。

    返回:
    - JSONResponse: 成功响应，data 为分页结果。
    """
    result_dict = await StorageWorkflowService.get_workflow_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("查询存储工作流列表成功")
    return SuccessResponse(data=result_dict, msg="查询存储工作流列表成功")


@StorageWorkflowRouter.post(
    "/create",
    summary="创建存储工作流",
    description="创建存储工作流",
    response_model=ResponseSchema[StorageWorkflowOutSchema],
)
async def create_workflow_controller(
    data: StorageWorkflowCreateSchema,
    auth: Annotated[
        AuthSchema, Depends(AuthPermission(["module_storage:workflow:create"]))
    ],
) -> JSONResponse:
    """
    创建存储工作流。

    参数:
    - data (StorageWorkflowCreateSchema): 创建体。
    - auth (AuthSchema): 认证信息。

    返回:
    - JSONResponse: 成功响应，data 为新建工作流。
    """
    result_dict = await StorageWorkflowService.create_workflow_service(auth=auth, data=data)
    log.info("创建存储工作流成功")
    return SuccessResponse(data=result_dict, msg="创建存储工作流成功")


@StorageWorkflowRouter.put(
    "/update/{id}",
    summary="更新存储工作流",
    description="更新存储工作流",
    response_model=ResponseSchema[StorageWorkflowOutSchema],
)
async def update_workflow_controller(
    id: Annotated[int, Path(description="工作流ID")],
    data: StorageWorkflowUpdateSchema,
    auth: Annotated[
        AuthSchema, Depends(AuthPermission(["module_storage:workflow:update"]))
    ],
) -> JSONResponse:
    """
    更新存储工作流。

    参数:
    - id (int): 工作流 ID。
    - data (StorageWorkflowUpdateSchema): 更新体。
    - auth (AuthSchema): 认证信息。

    返回:
    - JSONResponse: 成功响应，data 为更新后的工作流。
    """
    result_dict = await StorageWorkflowService.update_workflow_service(
        auth=auth, id=id, data=data
    )
    log.info(f"更新存储工作流成功 {id}")
    return SuccessResponse(data=result_dict, msg="更新存储工作流成功")


@StorageWorkflowRouter.delete(
    "/delete",
    summary="删除存储工作流",
    description="批量删除存储工作流",
    response_model=ResponseSchema[None],
)
async def delete_workflow_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[
        AuthSchema, Depends(AuthPermission(["module_storage:workflow:delete"]))
    ],
) -> JSONResponse:
    """
    批量删除存储工作流。

    参数:
    - ids (list[int]): 工作流 ID 列表。
    - auth (AuthSchema): 认证信息。

    返回:
    - JSONResponse: 成功提示响应。
    """
    await StorageWorkflowService.delete_workflow_service(auth=auth, ids=ids)
    log.info(f"删除存储工作流成功 {ids}")
    return SuccessResponse(msg="删除存储工作流成功")
