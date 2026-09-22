"""存储工作流业务逻辑层。"""

from typing import Any

from app.core.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import StorageWorkflowCRUD
from .schema import (
    StorageWorkflowCreateSchema,
    StorageWorkflowOutSchema,
    StorageWorkflowQueryParam,
    StorageWorkflowUpdateSchema,
)


class StorageWorkflowService:
    """存储工作流：CRUD + 分页 + 校验"""

    @staticmethod
    def _out(obj: Any) -> dict:
        """
        将模型实例序列化为输出字典。

        参数:
        - obj (Any): 模型实例。

        返回:
        - dict: 序列化后的字典。
        """
        return StorageWorkflowOutSchema.model_validate(obj).model_dump(mode="json")

    @classmethod
    async def get_workflow_detail_service(cls, auth: AuthSchema, id: int) -> dict:
        """
        获取存储工作流详情。

        参数:
        - auth (AuthSchema): 认证信息。
        - id (int): 工作流 ID。

        返回:
        - dict: 序列化后的工作流详情。

        异常:
        - CustomException: 不存在时抛出。
        """
        obj = await StorageWorkflowCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="存储工作流不存在")
        return cls._out(obj)

    @classmethod
    async def get_workflow_list_service(
        cls,
        auth: AuthSchema,
        search: StorageWorkflowQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        """
        获取存储工作流列表（非分页）。

        参数:
        - auth (AuthSchema): 认证信息。
        - search (StorageWorkflowQueryParam | None): 查询条件。
        - order_by (list[dict[str, str]] | None): 排序。

        返回:
        - list[dict]: 工作流字典列表。
        """
        if order_by is None:
            order_by = [{"updated_time": "desc"}]
        obj_list = await StorageWorkflowCRUD(auth).get_obj_list_crud(
            search=search.__dict__ if search else None,
            order_by=order_by,
        )
        return [cls._out(o) for o in obj_list]

    @classmethod
    async def get_workflow_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: StorageWorkflowQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """
        分页查询存储工作流。

        参数:
        - auth (AuthSchema): 认证信息。
        - page_no (int): 页码。
        - page_size (int): 每页条数。
        - search (StorageWorkflowQueryParam | None): 查询条件。
        - order_by (list[dict[str, str]] | None): 排序。

        返回:
        - dict: 分页结果。
        """
        offset = (page_no - 1) * page_size
        order = order_by or [{"updated_time": "desc"}]
        result = await StorageWorkflowCRUD(auth).page(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search.__dict__ if search else {},
            out_schema=StorageWorkflowOutSchema,
        )
        result["items"] = [
            StorageWorkflowOutSchema.model_validate(item).model_dump(mode="json")
            for item in result["items"]
        ]
        return result

    @classmethod
    async def create_workflow_service(
        cls, auth: AuthSchema, data: StorageWorkflowCreateSchema
    ) -> dict:
        """
        创建存储工作流。

        参数:
        - auth (AuthSchema): 认证信息。
        - data (StorageWorkflowCreateSchema): 创建体。

        返回:
        - dict: 新建工作流字典。

        异常:
        - CustomException: 编码重复或创建失败。
        """
        exist = await StorageWorkflowCRUD(auth).get(code=data.code)
        if exist:
            raise CustomException(msg="工作流编码已存在")
        obj = await StorageWorkflowCRUD(auth).create_obj_crud(data=data)
        if not obj:
            raise CustomException(msg="创建存储工作流失败")
        return cls._out(obj)

    @classmethod
    async def update_workflow_service(
        cls, auth: AuthSchema, id: int, data: StorageWorkflowUpdateSchema
    ) -> dict:
        """
        更新存储工作流。

        参数:
        - auth (AuthSchema): 认证信息。
        - id (int): 工作流 ID。
        - data (StorageWorkflowUpdateSchema): 更新体。

        返回:
        - dict: 更新后工作流字典。

        异常:
        - CustomException: 不存在、编码冲突或更新失败。
        """
        exist = await StorageWorkflowCRUD(auth).get_obj_by_id_crud(id=id)
        if not exist:
            raise CustomException(msg="存储工作流不存在")
        if exist.code != data.code:
            other = await StorageWorkflowCRUD(auth).get(code=data.code)
            if other:
                raise CustomException(msg="工作流编码已存在")
        obj = await StorageWorkflowCRUD(auth).update_obj_crud(id=id, data=data)
        if not obj:
            raise CustomException(msg="更新存储工作流失败")
        return cls._out(obj)

    @classmethod
    async def delete_workflow_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """
        批量删除存储工作流。

        参数:
        - auth (AuthSchema): 认证信息。
        - ids (list[int]): ID 列表。

        返回:
        - None

        异常:
        - CustomException: ID 为空时抛出。
        """
        if not ids:
            raise CustomException(msg="删除ID不能为空")
        await StorageWorkflowCRUD(auth).delete_obj_crud(ids=ids)
