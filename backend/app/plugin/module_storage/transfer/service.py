"""传输任务服务层。"""

from app.core.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import StorageTransferCRUD
from .schema import (
    StorageTransferCreateSchema,
    StorageTransferOutSchema,
    StorageTransferQueryParam,
    StorageTransferUpdateSchema,
)


class StorageTransferService:
    """传输任务管理服务层。"""

    @classmethod
    async def get_transfer_detail_service(cls, auth: AuthSchema, id: int) -> dict:
        """获取传输任务详情。"""
        obj = await StorageTransferCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="传输任务不存在")
        return StorageTransferOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def get_transfer_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: StorageTransferQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """分页查询传输任务。"""
        offset = (page_no - 1) * page_size
        return await StorageTransferCRUD(auth).page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "asc"}],
            search=search.__dict__ if search else {},
            out_schema=StorageTransferOutSchema,
        )

    @classmethod
    async def create_transfer_service(
        cls, auth: AuthSchema, data: StorageTransferCreateSchema
    ) -> dict:
        """创建传输任务。"""
        obj = await StorageTransferCRUD(auth).create_obj_crud(data=data)
        if not obj:
            raise CustomException(msg="创建失败")
        return StorageTransferOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def update_transfer_service(
        cls, auth: AuthSchema, id: int, data: StorageTransferUpdateSchema
    ) -> dict:
        """更新传输任务。"""
        exist_obj = await StorageTransferCRUD(auth).get_obj_by_id_crud(id=id)
        if not exist_obj:
            raise CustomException(msg="更新失败，该传输任务不存在")

        obj = await StorageTransferCRUD(auth).update_obj_crud(id=id, data=data)
        if not obj:
            raise CustomException(msg="更新失败")
        return StorageTransferOutSchema.model_validate(obj).model_dump()

    @classmethod
    async def delete_transfer_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除传输任务。"""
        if len(ids) < 1:
            raise CustomException(msg="删除失败，删除对象不能为空")
        for id in ids:
            exist_obj = await StorageTransferCRUD(auth).get_obj_by_id_crud(id=id)
            if not exist_obj:
                raise CustomException(msg="删除失败，该传输任务不存在")
        await StorageTransferCRUD(auth).delete_obj_crud(ids=ids)
