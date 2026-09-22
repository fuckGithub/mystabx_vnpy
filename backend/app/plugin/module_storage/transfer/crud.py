"""传输任务 CRUD。"""

from collections.abc import Sequence
from typing import Any

from app.core.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import StorageTransferModel
from .schema import StorageTransferCreateSchema, StorageTransferUpdateSchema


class StorageTransferCRUD(
    CRUDBase[StorageTransferModel, StorageTransferCreateSchema, StorageTransferUpdateSchema]
):
    """传输任务数据层。"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=StorageTransferModel, auth=auth)

    async def get_obj_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> StorageTransferModel | None:
        """获取传输任务详情。"""
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[StorageTransferModel]:
        """获取传输任务列表。"""
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_obj_crud(
        self, data: StorageTransferCreateSchema
    ) -> StorageTransferModel | None:
        """创建传输任务。"""
        return await self.create(data=data)

    async def update_obj_crud(
        self, id: int, data: StorageTransferUpdateSchema
    ) -> StorageTransferModel | None:
        """更新传输任务。"""
        return await self.update(id=id, data=data)

    async def delete_obj_crud(self, ids: list[int]) -> None:
        """删除传输任务。"""
        return await self.delete(ids=ids)
