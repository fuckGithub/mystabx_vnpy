from collections.abc import Sequence

from app.core.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase
from app.core.exceptions import CustomException

from .model import AiModelModel, AiProviderModel
from .schema import (
    AiModelCreateSchema,
    AiModelUpdateSchema,
    AiProviderCreateSchema,
    AiProviderUpdateSchema,
)


class AiProviderCRUD(
    CRUDBase[AiProviderModel, AiProviderCreateSchema, AiProviderUpdateSchema]
):
    """AI 供应商数据层（一级）"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化 AI 供应商数据层。

        参数:
        - auth (AuthSchema): 认证信息模型（含 DB 会话等上下文）。

        返回:
        - None
        """
        self.auth = auth
        super().__init__(model=AiProviderModel, auth=auth)

    async def get_obj_by_id_crud(self, id: int, preload: list | None = None) -> AiProviderModel | None:
        """
        获取供应商详情（默认预加载模型列表）。

        参数:
        - id (int): 供应商ID。
        - preload (list | None): 预加载关系；默认含 models。

        返回:
        - AiProviderModel | None: 供应商模型；不存在为 None。
        """
        if preload is None:
            preload = ["models"]
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict] | None = None,
    ) -> Sequence[AiProviderModel]:
        """
        获取供应商列表（不含嵌套模型）。

        参数:
        - search (dict | None): 查询参数（name/vendor/api_type/status 等）。
        - order_by (list[dict] | None): 排序参数。

        返回:
        - Sequence[AiProviderModel]: 供应商模型序列。
        """
        return await self.list(search=search, order_by=order_by)

    async def get_default_provider_crud(self) -> AiProviderModel | None:
        """
        获取当前默认供应商（is_default=True 且 status='0'）。

        返回:
        - AiProviderModel | None: 默认供应商；无则为 None。
        """
        return await self.get(is_default=True, status="0")

    async def set_default_crud(self, provider_id: int) -> None:
        """
        设置默认供应商：清除旧默认标记，将指定供应商置为默认。

        参数:
        - provider_id (int): 目标供应商ID。

        返回:
        - None

        异常:
        - CustomException: 供应商不存在时抛出。
        """
        old_default = await self.get(is_default=True)
        if old_default is not None:
            await self.update(id=old_default.id, data={"is_default": False})

        target = await self.get(id=provider_id)
        if target is None:
            raise CustomException(msg=f"供应商不存在: {provider_id}")
        await self.update(id=provider_id, data={"is_default": True})


class AiModelCRUD(CRUDBase[AiModelModel, AiModelCreateSchema, AiModelUpdateSchema]):
    """AI 模型数据层（二级）"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化 AI 模型数据层。

        参数:
        - auth (AuthSchema): 认证信息模型（含 DB 会话等上下文）。

        返回:
        - None
        """
        self.auth = auth
        super().__init__(model=AiModelModel, auth=auth)

    async def get_obj_by_id_crud(self, id: int, preload: list | None = None) -> AiModelModel | None:
        """
        获取模型详情（默认预加载归属供应商）。

        参数:
        - id (int): 模型ID。
        - preload (list | None): 预加载关系；默认含 provider_obj。

        返回:
        - AiModelModel | None: 模型实例；不存在为 None。
        """
        if preload is None:
            preload = ["provider_obj"]
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict] | None = None,
        preload: list | None = None,
    ) -> Sequence[AiModelModel]:
        """
        获取模型列表（默认预加载供应商）。

        参数:
        - search (dict | None): 查询参数（provider_id/model_key/name/status 等）。
        - order_by (list[dict] | None): 排序参数。
        - preload (list | None): 预加载关系；默认含 provider_obj。

        返回:
        - Sequence[AiModelModel]: 模型实例序列。
        """
        if preload is None:
            preload = ["provider_obj"]
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def get_models_by_provider_crud(
        self, provider_id: int, order_by: list[dict] | None = None
    ) -> Sequence[AiModelModel]:
        """
        获取指定供应商下的启用模型列表（前端按供应商分类下拉）。

        参数:
        - provider_id (int): 供应商ID。
        - order_by (list[dict] | None): 排序参数。

        返回:
        - Sequence[AiModelModel]: 启用模型实例序列。
        """
        return await self.list(
            search={"provider_id": provider_id, "status": "0"},
            order_by=order_by or [{"sort_order": "desc"}, {"id": "asc"}],
            preload=["provider_obj"],
        )

    async def get_default_model_crud(self) -> AiModelModel | None:
        """
        获取当前默认模型（is_default=True 且 status='0'）。

        返回:
        - AiModelModel | None: 默认模型；无则为 None。
        """
        return await self.get(is_default=True, status="0")

    async def set_default_model_crud(self, model_id: int) -> None:
        """
        设置默认模型：清除旧默认标记，将指定模型置为默认。

        参数:
        - model_id (int): 目标模型ID。

        返回:
        - None

        异常:
        - CustomException: 模型不存在时抛出。
        """
        old_default = await self.get(is_default=True)
        if old_default is not None:
            await self.update(id=old_default.id, data={"is_default": False})

        target = await self.get(id=model_id)
        if target is None:
            raise CustomException(msg=f"模型不存在: {model_id}")
        await self.update(id=model_id, data={"is_default": True})
