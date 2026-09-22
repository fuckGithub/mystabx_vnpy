from typing import Any

from app.core.exceptions import CustomException
from app.core.logger import log

from .crud import AiModelCRUD, AiProviderCRUD
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
    AiProviderUpdateSchema,
)
from .utils import AgnoModelFactory


class AiProviderService:
    """AI 供应商管理服务层（一级）"""

    @classmethod
    async def get_obj_detail_service(cls, auth: Any, id: int) -> dict:
        """
        获取供应商详情（含嵌套模型列表）。

        参数:
        - auth: 认证信息。
        - id (int): 供应商ID。

        返回:
        - dict: 供应商详情（含 models 列表）。

        异常:
        - CustomException: 供应商不存在时抛出。
        """
        obj = await AiProviderCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg=f"供应商不存在: {id}")
        return AiProviderDetailOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def get_obj_list_service(
        cls, auth: Any, search: AiProviderQueryParam | None = None, order_by: list[dict] | None = None
    ) -> list[dict]:
        """
        获取供应商列表（不含嵌套模型）。

        参数:
        - auth: 认证信息。
        - search (AiProviderQueryParam | None): 查询参数。
        - order_by (list[dict] | None): 排序。

        返回:
        - list[dict]: 供应商列表。
        """
        obj_list = await AiProviderCRUD(auth).get_obj_list_crud(
            search=search.model_dump(exclude_none=True) if search else None,
            order_by=order_by,
        )
        return [AiProviderOutSchema.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def get_obj_page_service(
        cls, auth: Any, page_no: int, page_size: int,
        search: AiProviderQueryParam | None = None, order_by: list[dict] | None = None,
    ) -> dict:
        """
        分页查询供应商。

        参数:
        - auth: 认证信息。
        - page_no (int): 页码。
        - page_size (int): 每页条数。
        - search (AiProviderQueryParam | None): 查询参数。
        - order_by (list[dict] | None): 排序。

        返回:
        - dict: 分页结果（items/total 等）。
        """
        return await AiProviderCRUD(auth).page(
            offset=(page_no - 1) * page_size,
            limit=page_size,
            order_by=order_by or [{"sort_order": "desc"}, {"id": "asc"}],
            search=search.model_dump(exclude_none=True) if search else {},
            out_schema=AiProviderOutSchema,
        )

    @classmethod
    async def create_obj_service(cls, auth: Any, data: AiProviderCreateSchema) -> dict:
        """
        创建供应商；若标记为默认则清除其他默认标记。

        参数:
        - auth: 认证信息。
        - data (AiProviderCreateSchema): 创建参数。

        返回:
        - dict: 新建供应商详情。
        """
        crud = AiProviderCRUD(auth)
        obj = await crud.create(data=data)
        if data.is_default:
            await crud.set_default_crud(provider_id=obj.id)
        return AiProviderOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_obj_service(cls, auth: Any, id: int, data: AiProviderUpdateSchema) -> dict:
        """
        更新供应商；若标记为默认则清除其他默认标记。

        参数:
        - auth: 认证信息。
        - id (int): 供应商ID。
        - data (AiProviderUpdateSchema): 更新参数。

        返回:
        - dict: 更新后的供应商详情。
        """
        crud = AiProviderCRUD(auth)
        obj = await crud.update(id=id, data=data)
        if data.is_default:
            await crud.set_default_crud(provider_id=id)
        return AiProviderOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def delete_obj_service(cls, auth: Any, ids: list[int]) -> None:
        """
        批量删除供应商（级联删除其下模型）。

        参数:
        - auth: 认证信息。
        - ids (list[int]): 供应商ID列表。

        返回:
        - None
        """
        await AiProviderCRUD(auth).delete(ids=ids)

    @classmethod
    async def set_default_service(cls, auth: Any, id: int) -> None:
        """
        设置默认供应商。

        参数:
        - auth: 认证信息。
        - id (int): 供应商ID。

        返回:
        - None

        异常:
        - CustomException: 供应商不存在或停用时抛出。
        """
        crud = AiProviderCRUD(auth)
        obj = await crud.get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg=f"供应商不存在: {id}")
        if obj.status != "0":
            raise CustomException(msg="停用状态的供应商不能设为默认")
        await crud.set_default_crud(provider_id=id)

    @classmethod
    async def test_connectivity_service(cls, auth: Any, data: Any) -> dict:
        """
        测试供应商连通性：用真实 model_key 构建 agno 模型实例并发送 aresponse。

        参数:
        - auth: 认证信息。
        - data: 供应商配置（含 api_key / base_url / vendor / api_type / model_key）。

        返回:
        - dict: { success: bool, latency_ms: int | None, error: str | None }
        """
        import time

        from agno.models.message import Message

        config: dict[str, Any] = {
            "api_type": data.api_type,
            "vendor": data.vendor,
            "api_key": data.api_key,
            "model_key": data.model_key,
            "name": data.model_key,
            "url": data.base_url,
        }
        try:
            model = AgnoModelFactory.build_model(config)
            start = time.monotonic()
            messages = [Message(role="user", content="hi")]
            await model.aresponse(messages=messages)
            latency = int((time.monotonic() - start) * 1000)
            return {"success": True, "latency_ms": latency, "error": None}
        except Exception as e:
            log.warning(f"供应商连通性测试失败: {e}")
            return {"success": False, "latency_ms": None, "error": str(e)}


class AiModelService:
    """AI 模型管理服务层（二级）"""

    @classmethod
    async def get_obj_detail_service(cls, auth: Any, id: int) -> dict:
        """
        获取模型详情（含归属供应商摘要）。

        参数:
        - auth: 认证信息。
        - id (int): 模型ID。

        返回:
        - dict: 模型详情（含 provider 摘要）。

        异常:
        - CustomException: 模型不存在时抛出。
        """
        obj = await AiModelCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg=f"模型不存在: {id}")
        return AiModelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def get_obj_list_service(
        cls, auth: Any, search: AiModelQueryParam | None = None, order_by: list[dict] | None = None
    ) -> list[dict]:
        """
        获取模型列表（含归属供应商信息）。

        参数:
        - auth: 认证信息。
        - search (AiModelQueryParam | None): 查询参数。
        - order_by (list[dict] | None): 排序。

        返回:
        - list[dict]: 模型列表。
        """
        obj_list = await AiModelCRUD(auth).get_obj_list_crud(
            search=search.model_dump(exclude_none=True) if search else None,
            order_by=order_by,
            preload=["provider_obj"],
        )
        return [AiModelOutSchema.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def get_obj_page_service(
        cls, auth: Any, page_no: int, page_size: int,
        search: AiModelQueryParam | None = None, order_by: list[dict] | None = None,
    ) -> dict:
        """
        分页查询模型（含归属供应商信息）。

        参数:
        - auth: 认证信息。
        - page_no (int): 页码。
        - page_size (int): 每页条数。
        - search (AiModelQueryParam | None): 查询参数。
        - order_by (list[dict] | None): 排序。

        返回:
        - dict: 分页结果。
        """
        return await AiModelCRUD(auth).page(
            offset=(page_no - 1) * page_size,
            limit=page_size,
            order_by=order_by or [{"sort_order": "desc"}, {"id": "asc"}],
            search=search.model_dump(exclude_none=True) if search else {},
            out_schema=AiModelOutSchema,
            preload=["provider_obj"],
        )

    @classmethod
    async def get_models_by_provider_service(cls, auth: Any, provider_id: int) -> list[dict]:
        """
        获取指定供应商下的启用模型列表（前端按供应商分类下拉）。

        参数:
        - auth: 认证信息。
        - provider_id (int): 供应商ID。

        返回:
        - list[dict]: 模型列表（含供应商摘要，不暴露密钥）。
        """
        obj_list = await AiModelCRUD(auth).get_models_by_provider_crud(provider_id=provider_id)
        return [AiModelListOutSchema.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def create_obj_service(cls, auth: Any, data: AiModelCreateSchema) -> dict:
        """
        创建模型；若标记为默认则清除其他默认标记。

        参数:
        - auth: 认证信息。
        - data (AiModelCreateSchema): 创建参数。

        返回:
        - dict: 新建模型详情。
        """
        crud = AiModelCRUD(auth)
        obj = await crud.create(data=data)
        if data.is_default:
            await crud.set_default_model_crud(model_id=obj.id)
        return AiModelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_obj_service(cls, auth: Any, id: int, data: AiModelUpdateSchema) -> dict:
        """
        更新模型；若标记为默认则清除其他默认标记。

        参数:
        - auth: 认证信息。
        - id (int): 模型ID。
        - data (AiModelUpdateSchema): 更新参数。

        返回:
        - dict: 更新后的模型详情。
        """
        crud = AiModelCRUD(auth)
        obj = await crud.update(id=id, data=data)
        if data.is_default:
            await crud.set_default_model_crud(model_id=id)
        return AiModelOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def delete_obj_service(cls, auth: Any, ids: list[int]) -> None:
        """
        批量删除模型。

        参数:
        - auth: 认证信息。
        - ids (list[int]): 模型ID列表。

        返回:
        - None
        """
        await AiModelCRUD(auth).delete(ids=ids)

    @classmethod
    async def set_default_service(cls, auth: Any, id: int) -> None:
        """
        设置默认模型。

        参数:
        - auth: 认证信息。
        - id (int): 模型ID。

        返回:
        - None

        异常:
        - CustomException: 模型不存在或停用时抛出。
        """
        crud = AiModelCRUD(auth)
        obj = await crud.get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg=f"模型不存在: {id}")
        if obj.status != "0":
            raise CustomException(msg="停用状态的模型不能设为默认")
        await crud.set_default_model_crud(model_id=id)

    @classmethod
    async def build_model_by_id(
        cls, auth: Any, id: int | None = None, enable_thinking: bool | None = None
    ) -> Any:
        """
        根据模型配置构建 Agno 模型实例（聊天模块调用）。

        api_type 决定协议（如 mimo 的 messages → Claude 协议），
        vendor 兜底推测；模型级 url 覆盖供应商默认。

        参数:
        - auth: 认证信息。
        - id (int | None): 模型ID；None 时使用默认模型。
        - enable_thinking (bool | None): 是否开启思考模式；None=用模型配置，True/False=覆盖。

        返回:
        - Any: Agno 模型实例。

        异常:
        - CustomException: 模型不存在、未启用或 SDK 未安装时抛出。
        """
        crud = AiModelCRUD(auth)
        if id:
            model = await crud.get_obj_by_id_crud(id=id, preload=["provider_obj"])
            if not model:
                raise CustomException(msg=f"模型不存在: {id}")
            if model.status != "0":
                raise CustomException(msg=f"模型未启用: {model.name}")
        else:
            model = await crud.get_default_model_crud()
            if not model:
                raise CustomException(msg="未配置默认模型，请先在模型管理中设置")

        # 合并供应商 + 模型配置（模型级覆盖供应商级）
        provider = model.provider_obj
        config: dict[str, Any] = {
            "api_type": provider.api_type,
            "vendor": provider.vendor,
            "api_key": provider.api_key,
            "model_key": model.model_key,
            "name": model.name,
            "url": model.url or provider.base_url,
            "temperature": model.temperature,
            "thinking": model.thinking,
            "vision": model.vision,
            "tool_calling": model.tool_calling,
            "max_input_tokens": model.max_input_tokens,
            "max_output_tokens": model.max_output_tokens,
        }
        # 显式传入的思考开关覆盖模型配置
        if enable_thinking is not None:
            config["enable_thinking"] = enable_thinking
        try:
            return AgnoModelFactory.build_model(config)
        except ImportError as e:
            log.error(f"模型 SDK 未安装: {e}")
            raise CustomException(msg=str(e)) from e
        except ValueError as e:
            log.error(f"不支持的模型协议: {e}")
            raise CustomException(msg=str(e)) from e
