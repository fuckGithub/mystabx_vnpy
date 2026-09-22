"""
国密（SM2/SM3/SM4）加密入口模块

提供 CommonCryptogramUtil 统一门面，外部通过此入口调用国密功能。
密码工具 PwdUtil 和数据库字段加密 Sm4CbcTypeHandler 也集中于此。

算法实现位于 sm_crypto.py。
"""

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

from app.config.setting import settings
from app.utils.sm_crypto import Sm2Cipher, Sm3Cipher, Sm4Cipher


class CommonCryptogramUtil:

    @staticmethod
    def do_sm2_encrypt(str_data: str) -> str:
        """
        SM2 公钥加密（使用配置中的 SM2 公钥）。

        Args:
            str_data: 待加密的明文字符串

        Returns:
            str: 加密后的十六进制字符串
        """
        encrypted = Sm2Cipher.encrypt(
            settings.SM2_PUBLIC_KEY, str_data.encode("utf-8")
        )
        return encrypted.hex()

    @staticmethod
    def do_sm2_decrypt(str_data: str) -> str:
        """
        SM2 私钥解密（使用配置中的 SM2 私钥）。

        Args:
            str_data: 待解密的十六进制密文字符串

        Returns:
            str: 解密后的明文字符串

        Raises:
            ValueError: 解密失败时抛出
        """
        decrypted = Sm2Cipher.decrypt(
            settings.SM2_PRIVATE_KEY, bytes.fromhex(str_data)
        )
        return decrypted.decode("utf-8")

    @staticmethod
    def do_signature(str_data: str) -> str:
        """
        SM2 私钥签名。

        Args:
            str_data: 待签名的数据

        Returns:
            str: 签名值十六进制字符串
        """
        return Sm2Cipher.sign(
            settings.SM2_PRIVATE_KEY,
            settings.SM2_PUBLIC_KEY,
            str_data.encode("utf-8"),
        )

    @staticmethod
    def do_verify_signature(original_str: str, signature_str: str) -> bool:
        """
        验证 SM2 签名。

        Args:
            original_str: 原始数据
            signature_str: 签名值

        Returns:
            bool: 签名是否有效
        """
        return Sm2Cipher.verify(
            settings.SM2_PUBLIC_KEY,
            original_str.encode("utf-8"),
            signature_str,
        )

    @staticmethod
    def do_hash_value(str_data: str) -> str:
        """
        SM3 哈希计算（用于数据完整性保护）。

        Args:
            str_data: 待哈希的数据

        Returns:
            str: 64 字符十六进制哈希值
        """
        return Sm3Cipher.hash(str_data.encode("utf-8"))


class PwdUtil:
    """
    密码工具类，仅使用国密 SM3 加盐哈希。

    密码存储格式: salt$hash
    - salt: 十六进制盐值（32 字符）
    - hash: SM3(password + salt)（64 字符）
    """

    @classmethod
    def verify_password(cls, plain_password: str, password_hash: str) -> bool:
        """校验密码是否匹配。"""
        return Sm3Cipher.verify_password(plain_password, password_hash)

    @classmethod
    def set_password_hash(cls, password: str) -> str:
        """对密码进行 SM3 加盐哈希。"""
        salt, hash_value = Sm3Cipher.hash_password(password)
        return f"{salt}${hash_value}"

    @classmethod
    def check_password_strength(cls, password: str) -> str | None:
        """检查密码强度。"""
        if len(password) < 6:
            return "密码长度至少6位"
        if not any(c.islower() for c in password):
            return "密码需要包含小写字母"
        if not any(c.isdigit() for c in password):
            return "密码需要包含数字"
        return None


class Sm4CbcTypeHandler(TypeDecorator):
    """
    SM4-CBC 加密字段类型处理器（SQLAlchemy TypeDecorator）。

    用法:
        id_card: Mapped[str | None] = mapped_column(
            Sm4CbcTypeHandler(255), nullable=True, comment="身份证号(SM4加密)"
        )
    """

    impl = String

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        """写入数据库时加密。"""
        if value is None:
            return None
        key = Sm4Cipher.get_config_key()
        encrypted = Sm4Cipher.encrypt(key, value.encode("utf-8"))
        return encrypted.hex()

    def process_result_value(self, value: str | None, dialect) -> str | None:
        """从数据库读取时解密。"""
        if value is None:
            return None
        try:
            key = Sm4Cipher.get_config_key()
            decrypted = Sm4Cipher.decrypt(key, bytes.fromhex(value))
            return decrypted.decode("utf-8")
        except Exception:
            return value
