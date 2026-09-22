"""存储工作流 CRUD。"""

from collections.abc import Sequence
from typing import Any

from app.core.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import StorageWorkflowModel
from .schema import StorageWorkflowCreateSchema, StorageWorkflowUpdateSchema


class StorageWorkflowCRUD(
    CRUDBase[StorageWorkflowModel, StorageWorkflowCreateSchema, StorageWorkflowUpdateSchema]
):
    """存储工作流数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化存储工作流 CRUD。

        参数:
        - auth (AuthSchema): 认证信息。

        返回:
        - None
        """
        self.auth = auth
        super().__init__(model=StorageWorkflowModel, auth=auth)

    async def get_obj_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> StorageWorkflowModel | None:
        """
        按主键查询存储工作流。

        参数:
        - id (int): 工作流 ID。
        - preload (list[str | Any] | None): 预加载关系。

        返回:
        - StorageWorkflowModel | None: 实体或 None。
        """
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[StorageWorkflowModel]:
        """
        条件列表查询存储工作流。

        参数:
        - search (dict | None): 查询条件。
        - order_by (list[dict[str, str]] | None): 排序。
        - preload (list[str | Any] | None): 预加载关系。

        返回:
        - Sequence[StorageWorkflowModel]: 工作流列表。
        """
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_obj_crud(
        self, data: StorageWorkflowCreateSchema
    ) -> StorageWorkflowModel | None:
        """
        创建存储工作流。

        参数:
        - data (StorageWorkflowCreateSchema): 创建模型。

        返回:
        - StorageWorkflowModel | None: 新建实体或 None。
        """
        return await self.create(data=data)

    async def update_obj_crud(
        self, id: int, data: StorageWorkflowUpdateSchema
    ) -> StorageWorkflowModel | None:
        """
        更新存储工作流。

        参数:
        - id (int): 工作流 ID。
        - data (StorageWorkflowUpdateSchema): 更新模型。

        返回:
        - StorageWorkflowModel | None: 更新后实体或 None。
        """
        return await self.update(id=id, data=data)

    async def delete_obj_crud(self, ids: list[int]) -> None:
        """
        批量删除存储工作流。

        参数:
        - ids (list[int]): ID 列表。

        返回:
        - None
        """
        await self.delete(ids=ids)
