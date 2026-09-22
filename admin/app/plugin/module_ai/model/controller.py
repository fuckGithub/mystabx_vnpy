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
    AiModelCreateSchema,
    AiModelListOutSchema,
    AiModelOutSchema,
    AiModelQueryParam,
    AiModelUpdateSchema,
    AiProviderCreateSchema,
    AiProviderDetailOutSchema,
    AiProviderOutSchema,
    AiProviderQueryParam,
    AiProviderTestConnectivitySchema,
    AiProviderUpdateSchema,
)
from .service import AiModelService, AiProviderService

# ============================================================ #
# 一级：AI 供应商路由
# ============================================================ #
AiProviderRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/provider",
    tags=["AI供应商管理"],
)


@AiProviderRouter.get(
    "/detail/{id}",
    summary="获取供应商详情",
    description="获取供应商详情（含其下模型列表）",
    response_model=ResponseSchema[AiProviderDetailOutSchema],
)
async def get_provider_detail_controller(
    id: Annotated[int, Path(description="供应商ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:detail"]))],
) -> JSONResponse:
    """
    获取供应商详情（含嵌套模型列表）。

    参数:
    - id (int): 供应商ID。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 供应商详情响应。
    """
    result = await AiProviderService.get_obj_detail_service(auth=auth, id=id)
    log.info(f"获取供应商详情成功 {id}")
    return SuccessResponse(data=result, msg="获取供应商详情成功")


@AiProviderRouter.get(
    "/list",
    summary="查询供应商列表",
    description="查询供应商列表",
    response_model=ResponseSchema[list[AiProviderOutSchema]],
)
async def get_provider_list_controller(
    search: Annotated[AiProviderQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    查询供应商列表。

    参数:
    - search (AiProviderQueryParam): 查询参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 供应商列表响应。
    """
    result = await AiProviderService.get_obj_list_service(auth=auth, search=search)
    log.info("查询供应商列表成功")
    return SuccessResponse(data=result, msg="查询供应商列表成功")


@AiProviderRouter.get(
    "/page",
    summary="分页查询供应商",
    description="分页查询供应商",
    response_model=ResponseSchema[dict],
)
async def get_provider_page_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AiProviderQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    分页查询供应商。

    参数:
    - page (PaginationQueryParam): 分页参数。
    - search (AiProviderQueryParam): 查询参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 供应商分页响应。
    """
    result = await AiProviderService.get_obj_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("供应商分页查询成功")
    return SuccessResponse(data=result, msg="供应商分页查询成功")


@AiProviderRouter.post(
    "/create",
    summary="创建供应商",
    description="创建供应商（可一次性携带其下模型列表）",
    response_model=ResponseSchema[AiProviderDetailOutSchema],
)
async def create_provider_controller(
    data: AiProviderCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:create"]))],
) -> JSONResponse:
    """
    创建供应商。

    参数:
    - data (AiProviderCreateSchema): 供应商创建参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 新建供应商响应。
    """
    result = await AiProviderService.create_obj_service(auth=auth, data=data)
    log.info(f"创建供应商成功 {result.get('id')}")
    return SuccessResponse(data=result, msg="创建供应商成功")


@AiProviderRouter.put(
    "/update/{id}",
    summary="更新供应商",
    description="更新供应商",
    response_model=ResponseSchema[AiProviderOutSchema],
)
async def update_provider_controller(
    id: Annotated[int, Path(description="供应商ID", ge=1)],
    data: AiProviderUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:update"]))],
) -> JSONResponse:
    """
    更新供应商。

    参数:
    - id (int): 供应商ID。
    - data (AiProviderUpdateSchema): 供应商更新参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 更新后的供应商响应。
    """
    result = await AiProviderService.update_obj_service(auth=auth, id=id, data=data)
    log.info(f"更新供应商成功 {id}")
    return SuccessResponse(data=result, msg="更新供应商成功")


@AiProviderRouter.delete(
    "/delete",
    summary="删除供应商",
    description="删除供应商（级联删除其下模型）",
    response_model=ResponseSchema[None],
)
async def delete_provider_controller(
    ids: Annotated[list[int], Body(..., description="供应商ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:delete"]))],
) -> JSONResponse:
    """
    删除供应商（批量，级联删除其下模型）。

    参数:
    - ids (list[int]): 供应商ID列表。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 删除结果响应。
    """
    await AiProviderService.delete_obj_service(auth=auth, ids=ids)
    log.info(f"删除供应商成功 {ids}")
    return SuccessResponse(data=None, msg="删除供应商成功")


@AiProviderRouter.post(
    "/test-connectivity",
    summary="测试供应商连通性",
    description="使用供应商配置的 API 地址和密钥发送一条轻量请求，验证连通性",
    response_model=ResponseSchema[dict],
)
async def test_provider_connectivity_controller(
    data: AiProviderTestConnectivitySchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    测试供应商连通性。

    参数:
    - data (AiProviderCreateSchema): 供应商配置（含 api_key / base_url / vendor / api_type）。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 连通性测试结果（success / latency_ms / error）。
    """
    result = await AiProviderService.test_connectivity_service(auth=auth, data=data)
    log.info(f"供应商连通性测试: {result}")
    return SuccessResponse(data=result, msg="连通性测试完成")


@AiProviderRouter.put(
    "/set-default/{id}",
    summary="设置默认供应商",
    description="将指定供应商设置为默认供应商",
    response_model=ResponseSchema[None],
)
async def set_default_provider_controller(
    id: Annotated[int, Path(description="供应商ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:update"]))],
) -> JSONResponse:
    """
    设置默认供应商。

    参数:
    - id (int): 供应商ID。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 设置结果响应。
    """
    await AiProviderService.set_default_service(auth=auth, id=id)
    log.info(f"设置默认供应商成功 {id}")
    return SuccessResponse(data=None, msg="设置默认供应商成功")


# ============================================================ #
# 二级：AI 模型路由
# ============================================================ #
AiModelRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/model",
    tags=["AI模型管理"],
)


@AiModelRouter.get(
    "/detail/{id}",
    summary="获取模型详情",
    description="获取模型详情（含所属供应商信息）",
    response_model=ResponseSchema[AiModelOutSchema],
)
async def get_model_detail_controller(
    id: Annotated[int, Path(description="模型ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:detail"]))],
) -> JSONResponse:
    """
    获取模型详情。

    参数:
    - id (int): 模型ID。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 模型详情响应。
    """
    result = await AiModelService.get_obj_detail_service(auth=auth, id=id)
    log.info(f"获取模型详情成功 {id}")
    return SuccessResponse(data=result, msg="获取模型详情成功")


@AiModelRouter.get(
    "/list",
    summary="查询模型列表",
    description="查询模型列表",
    response_model=ResponseSchema[list[AiModelOutSchema]],
)
async def get_model_list_controller(
    search: Annotated[AiModelQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    查询模型列表。

    参数:
    - search (AiModelQueryParam): 查询参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 模型列表响应。
    """
    result = await AiModelService.get_obj_list_service(auth=auth, search=search)
    log.info("查询模型列表成功")
    return SuccessResponse(data=result, msg="查询模型列表成功")


@AiModelRouter.get(
    "/page",
    summary="分页查询模型",
    description="分页查询模型",
    response_model=ResponseSchema[dict],
)
async def get_model_page_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[AiModelQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    分页查询模型。

    参数:
    - page (PaginationQueryParam): 分页参数。
    - search (AiModelQueryParam): 查询参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 模型分页响应。
    """
    result = await AiModelService.get_obj_page_service(
        auth=auth,
        page_no=page.page_no,
        page_size=page.page_size,
        search=search,
        order_by=page.order_by,
    )
    log.info("模型分页查询成功")
    return SuccessResponse(data=result, msg="模型分页查询成功")


@AiModelRouter.get(
    "/by-provider/{provider_id}",
    summary="查询供应商下的模型",
    description="查询指定供应商下的启用模型列表（前端按供应商分类下拉用）",
    response_model=ResponseSchema[list[AiModelListOutSchema]],
)
async def get_models_by_provider_controller(
    provider_id: Annotated[int, Path(description="供应商ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:query"]))],
) -> JSONResponse:
    """
    查询指定供应商下的启用模型列表。

    参数:
    - provider_id (int): 供应商ID。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 模型列表响应（不暴露密钥）。
    """
    result = await AiModelService.get_models_by_provider_service(
        auth=auth, provider_id=provider_id
    )
    log.info(f"查询供应商 {provider_id} 下的模型成功")
    return SuccessResponse(data=result, msg="查询供应商下的模型成功")


@AiModelRouter.post(
    "/create",
    summary="创建模型",
    description="创建模型（需指定归属供应商 provider_id）",
    response_model=ResponseSchema[AiModelOutSchema],
)
async def create_model_controller(
    data: AiModelCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:create"]))],
) -> JSONResponse:
    """
    创建模型。

    参数:
    - data (AiModelCreateSchema): 模型创建参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 新建模型响应。
    """
    result = await AiModelService.create_obj_service(auth=auth, data=data)
    log.info(f"创建模型成功 {result.get('id')}")
    return SuccessResponse(data=result, msg="创建模型成功")


@AiModelRouter.put(
    "/update/{id}",
    summary="更新模型",
    description="更新模型",
    response_model=ResponseSchema[AiModelOutSchema],
)
async def update_model_controller(
    id: Annotated[int, Path(description="模型ID", ge=1)],
    data: AiModelUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:update"]))],
) -> JSONResponse:
    """
    更新模型。

    参数:
    - id (int): 模型ID。
    - data (AiModelUpdateSchema): 模型更新参数。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 更新后的模型响应。
    """
    result = await AiModelService.update_obj_service(auth=auth, id=id, data=data)
    log.info(f"更新模型成功 {id}")
    return SuccessResponse(data=result, msg="更新模型成功")


@AiModelRouter.delete(
    "/delete",
    summary="删除模型",
    description="删除模型（批量）",
    response_model=ResponseSchema[None],
)
async def delete_model_controller(
    ids: Annotated[list[int], Body(..., description="模型ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:delete"]))],
) -> JSONResponse:
    """
    删除模型（批量）。

    参数:
    - ids (list[int]): 模型ID列表。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 删除结果响应。
    """
    await AiModelService.delete_obj_service(auth=auth, ids=ids)
    log.info(f"删除模型成功 {ids}")
    return SuccessResponse(data=None, msg="删除模型成功")


@AiModelRouter.put(
    "/set-default/{id}",
    summary="设置默认模型",
    description="将指定模型设置为默认模型",
    response_model=ResponseSchema[None],
)
async def set_default_model_controller(
    id: Annotated[int, Path(description="模型ID", ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_ai:model:update"]))],
) -> JSONResponse:
    """
    设置默认模型。

    参数:
    - id (int): 模型ID。
    - auth (AuthSchema): 认证信息模型。

    返回:
    - JSONResponse: 设置结果响应。
    """
    await AiModelService.set_default_service(auth=auth, id=id)
    log.info(f"设置默认模型成功 {id}")
    return SuccessResponse(data=None, msg="设置默认模型成功")
