import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.config.setting import settings
from app.core.base_schema import DownloadFileSchema, UploadResponseSchema
from app.core.exceptions import CustomException
from app.core.logger import log
from app.utils.upload_util import UploadUtil


class FileService:
    """
    文件管理服务层
    """

    @classmethod
    async def upload_service(
        cls, base_url: str, file: UploadFile, upload_type: str = "local"
    ) -> dict:
        """
        上传文件。

        参数:
        - base_url (str): 基础访问 URL。
        - file (UploadFile): 上传文件对象。
        - upload_type (str): 上传类型，'local' 或 'oss'；全局 OSS_READY 时默认走对象存储。

        返回:
        - Dict: 上传响应字典。

        异常:
        - CustomException: 当未选择文件或上传类型错误时抛出。
        """
        use_oss = settings.OSS_READY
        if upload_type == "oss":
            if not settings.OSS_READY:
                raise CustomException(msg="OSS 未配置或未启用")
            use_oss = True
        elif upload_type == "local":
            # 显式 local：仅当全局未就绪时走磁盘；就绪时仍走 OSS（文件管理统一后端）
            use_oss = settings.OSS_READY
        else:
            raise CustomException(msg="上传类型错误")

        if use_oss:
            from app.utils.oss_util import OssUtil

            if not file or not file.filename:
                raise CustomException(msg="请选择要上传的文件")
            content = await file.read()
            ext = UploadUtil.get_extension_from_filename(file.filename)
            if not ext:
                raise CustomException(msg="无法识别文件类型")
            UploadUtil.validate_file_extension(ext)
            safe_name = UploadUtil.generate_safe_filename(file.filename, ext)
            rel = f"{datetime.now().strftime('%Y/%m/%d')}/{safe_name}"
            key = await OssUtil.put_bytes(rel, content)
            file_url = OssUtil.public_or_signed_url(key)
            return UploadResponseSchema(
                file_path=key,
                file_name=safe_name,
                origin_name=file.filename,
                file_url=file_url,
            ).model_dump()

        filename, filepath, file_url = await UploadUtil.upload_file(
            file=file, base_url=base_url
        )
        return UploadResponseSchema(
            file_path=f"{filepath}",
            file_name=filename,
            origin_name=file.filename,
            file_url=f"{file_url}",
        ).model_dump()

    @staticmethod
    def _validate_download_path(file_path: str) -> str:
        """
        验证下载路径是否安全。

        参数:
        - file_path (str): 文件路径。

        返回:
        - str: 安全的绝对路径。

        异常:
        - CustomException: 当路径不安全时抛出。
        """
        if not file_path:
            raise CustomException(msg="请选择要下载的文件")

        dangerous_patterns = ["../", "..\\", "\0"]
        for pattern in dangerous_patterns:
            if pattern in file_path:
                log.error(f"检测到路径穿越攻击: {file_path}")
                raise CustomException(msg="非法的文件路径")

        upload_root = settings.UPLOAD_FILE_PATH.resolve()
        abs_path = os.path.normpath(os.path.abspath(file_path))

        if not abs_path.startswith(str(upload_root)):
            log.error(f"路径不在上传目录内: {file_path}")
            raise CustomException(msg="非法的文件路径")

        return abs_path

    @classmethod
    async def download_service(cls, file_path: str) -> DownloadFileSchema:
        """
        下载文件。

        参数:
        - file_path (str): 文件路径。

        返回:
        - DownloadFileSchema: 下载文件响应对象。

        异常:
        - CustomException: 当未选择文件或文件不存在时抛出。
        """
        # OSS 对象键：非绝对本地路径时尝试从 OSS 拉取
        if settings.OSS_READY and not os.path.isabs(file_path):
            from app.utils.oss_util import OssUtil

            data = await OssUtil.get_bytes(file_path)
            name = Path(file_path).name
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{name}")
            try:
                tmp.write(data)
            finally:
                tmp.close()
            return DownloadFileSchema(file_path=tmp.name, file_name=name)

        safe_path = cls._validate_download_path(file_path)

        if not UploadUtil.check_file_exists(safe_path):
            raise CustomException(msg="文件不存在")

        file_name = await UploadUtil.download_file(safe_path)

        return DownloadFileSchema(
            file_path=safe_path,
            file_name=str(file_name),
        )
