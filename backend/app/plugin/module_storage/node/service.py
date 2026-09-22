"""存储节点服务层。"""

from app.core.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import StorageNodeCRUD
from .schema import (
    StorageNodeCreateSchema,
    StorageNodeOutSchema,
    StorageNodeQueryParam,
    StorageNodeUpdateSchema,
)


class StorageNodeService:
    """存储节点管理服务层。"""

    @classmethod
    async def get_node_detail_service(cls, auth: AuthSchema, id: int) -> dict:
        """获取存储节点详情。"""
        obj = await StorageNodeCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="存储节点不存在")
        return StorageNodeOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def get_node_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: StorageNodeQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """分页查询存储节点。"""
        offset = (page_no - 1) * page_size
        return await StorageNodeCRUD(auth).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search.__dict__ if search else {},
            out_schema=StorageNodeOutSchema,
        )

    @classmethod
    async def create_node_service(cls, auth: AuthSchema, data: StorageNodeCreateSchema) -> dict:
        """创建存储节点。"""
        exist_obj = await StorageNodeCRUD(auth).get(name=data.name)
        if exist_obj:
            raise CustomException(msg="创建失败，该节点名称已存在")

        obj = await StorageNodeCRUD(auth).create_obj_crud(data=data)
        if not obj:
            raise CustomException(msg="创建失败")
        return StorageNodeOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_node_service(cls, auth: AuthSchema, id: int, data: StorageNodeUpdateSchema) -> dict:
        """更新存储节点。"""
        exist_obj = await StorageNodeCRUD(auth).get_obj_by_id_crud(id=id)
        if not exist_obj:
            raise CustomException(msg="更新失败，该节点不存在")

        obj = await StorageNodeCRUD(auth).update_obj_crud(id=id, data=data)
        if not obj:
            raise CustomException(msg="更新失败")
        return StorageNodeOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def delete_node_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除存储节点。"""
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        for id in ids:
            exist_obj = await StorageNodeCRUD(auth).get_obj_by_id_crud(id=id)
            if not exist_obj:
                raise CustomException(msg="删除失败，该节点不存在")
        await StorageNodeCRUD(auth).delete_obj_crud(ids=ids)
