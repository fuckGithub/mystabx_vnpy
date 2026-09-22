"""存储节点 CRUD。"""

from collections.abc import Sequence
from typing import Any

from app.core.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import StorageNodeModel
from .schema import StorageNodeCreateSchema, StorageNodeUpdateSchema


class StorageNodeCRUD(CRUDBase[StorageNodeModel, StorageNodeCreateSchema, StorageNodeUpdateSchema]):
    """存储节点数据层。"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=StorageNodeModel, auth=auth)

    async def get_obj_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> StorageNodeModel | None:
        """获取存储节点详情。"""
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[StorageNodeModel]:
        """获取存储节点列表。"""
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_obj_crud(self, data: StorageNodeCreateSchema) -> StorageNodeModel | None:
        """创建存储节点。"""
        return await self.create(data=data)

    async def update_obj_crud(self, id: int, data: StorageNodeUpdateSchema) -> StorageNodeModel | None:
        """更新存储节点。"""
        return await self.update(id=id, data=data)

    async def delete_obj_crud(self, ids: list[int]) -> None:
        """删除存储节点。"""
        return await self.delete(ids=ids)
