"""
国密（SM2/SM3/SM4）算法实现模块

提供 SM2 非对称加密、SM3 哈希、SM4 对称加密的底层算法实现。
外部应通过 sm_crypto_util 中的 CommonCryptogramUtil 调用。

依赖: ``snowland-smx``（导入名为 ``pysmx``），纯 Python 实现，跨平台无需编译。

⚠️ **对外契约不变**（已由 ``tests/core/test_sm_crypto.py`` 的 golden 向量锁定）：

* SM2 密文：裸 C1C3C2 = ``x(32) || y(32) || C3(32) || C2(n)``
* SM2 签名：裸 r‖s = ``r(32) || s(32)`` 的十六进制字符串
* SM4：CBC + PKCS7，输出 ``iv(16) || ciphertext``
* SM3：64 字符十六进制；密码存储为 ``salt$hash``

⚠️ **签名摘要求自行计算**：``pysmx`` 的 ``Sign`` / ``Verify`` 只接受已经算好的摘要 E，
因此本模块按 GM/T 0003 标准自行拼装 ZA 并派生 ``E = SM3(ZA || M)``：

    ZA = SM3(ENTL || ID || a || b || xG || yG || xA || yA)

其中 ID 取标准默认值 ``1234567812345678``（ENTL = 128 位）。
这一步必须与历史实现逐位一致，否则磁盘上已存的日志签名将全部无法验证。
"""

import os
import secrets

from pysmx.SM2 import Decrypt as _sm2_decrypt
from pysmx.SM2 import Encrypt as _sm2_encrypt
from pysmx.SM2 import Sign as _sm2_sign
from pysmx.SM2 import Verify as _sm2_verify
from pysmx.SM2 import generate_keypair as _sm2_generate_keypair
from pysmx.SM3 import SM3 as _SM3
from pysmx.SM4 import DECRYPT as _SM4_DECRYPT
from pysmx.SM4 import ENCRYPT as _SM4_ENCRYPT
from pysmx.SM4 import SM4 as _SM4

from app.config.setting import settings

# ============================================================
#   SM2 曲线参数与签名者标识（用于复刻标准摘要 E）
# ============================================================

_SM2_CURVE_A = "FFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC"
_SM2_CURVE_B = "28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93"
_SM2_CURVE_G = (
    "32c4ae2c1f1981195f9904466a39c9948fe30bbff2660be1715a4589334c74c7"
    "bc3736a2f4f6779c59bdcee36b692153d0a9877cc62a474002df32e52139f0a0"
)

_SM2_DEFAULT_ID = "1234567812345678"
"""SM2 签名者标识（GM/T 0003 默认值）"""

_SM2_ZA_PREFIX = (
    "0080"
    + _SM2_DEFAULT_ID.encode("utf-8").hex()
    + _SM2_CURVE_A
    + _SM2_CURVE_B
    + _SM2_CURVE_G
)
"""ZA 前缀：ENTL(128 位) || ID || a || b || xG || yG"""

_SM2_PARAM_LENGTH = 64
"""pysmx 的 ``len_para``：单个大数的十六进制字符数（32 字节）"""

_SM2_COORDINATE_SIZE = 32
"""SM2 坐标 / C3 的字节长度"""

_SM2_RAW_CIPHERTEXT_MIN_SIZE = 96
"""裸 C1C3C2 密文的最小长度（x + y + C3，不含变长 C2）"""

_SM2_RAW_SIGNATURE_SIZE = 64
"""裸 r‖s 签名长度"""

_SM2_SIGN_MAX_ATTEMPTS = 10
"""pysmx 在随机数 k 退化时会返回 None，需重试"""

_SM2_ENCRYPT_MAX_ATTEMPTS = 10
"""pysmx 的 Encrypt 在 KDF 输出全零时返回 None（国标要求重新选取 k），需重试"""

_SM4_BLOCK_SIZE = 16
"""SM4 分组长度（字节）"""


def _sm3_digest_hex(data: bytes) -> str:
    """
    SM3 摘要，返回十六进制字符串。

    Args:
        data: 待哈希的数据

    Returns:
        str: 64 字符小写十六进制摘要
    """
    hasher = _SM3()
    hasher.update(data)
    return hasher.hexdigest()


def _normalize_public_key(public_key: str) -> str:
    """
    归一化公钥为 pysmx 所需的 128 字符 ``x || y``（无 04 前缀）。

    Args:
        public_key: 130 字符（含 04）或 128 字符的十六进制公钥

    Returns:
        str: 128 字符公钥

    Raises:
        ValueError: 长度非法。
    """
    body = public_key[2:] if public_key.startswith("04") else public_key
    if len(body) != 128:
        raise ValueError(f"SM2 公钥长度非法：{len(public_key)} 字符（应为 130 或 128）")
    return body


def _compute_sm2_digest(public_key_128: str, data: bytes) -> str:
    """
    按 GM/T 0003 计算待签名摘要 ``E = SM3(ZA || M)``。

    Args:
        public_key_128: 128 字符公钥（x||y，无 04 前缀）
        data: 待签名的原始数据

    Returns:
        str: 64 字符十六进制摘要
    """
    za = _sm3_digest_hex(bytes.fromhex(_SM2_ZA_PREFIX + public_key_128))
    return _sm3_digest_hex(bytes.fromhex(za + data.hex()))


def _new_sm2_signature(digest_hex: str, private_key: str) -> bytes:
    """
    生成 SM2 签名（裸 r‖s）。

    Args:
        digest_hex: ``_compute_sm2_digest`` 得到的摘要
        private_key: 64 字符十六进制私钥

    Returns:
        bytes: 64 字节裸 r‖s

    Raises:
        ValueError: 连续多次都碰到退化的随机数。
    """
    for _ in range(_SM2_SIGN_MAX_ATTEMPTS):
        signature = _sm2_sign(
            digest_hex, private_key, secrets.token_hex(32), _SM2_PARAM_LENGTH, Hexstr=1
        )
        if signature:
            return bytes(signature)
    raise ValueError("SM2 签名失败：随机数连续退化")


# ============================================================
#   SM2 — 非对称加密 / 签名
# ============================================================


def _candidate_ciphertexts(ciphertext: bytes) -> list[bytes]:
    """返回密文的候选解释（首位为规范格式），供解密逐个尝试。

    规范格式是**裸 C1C3C2**：``x(32) || y(32) || C3(32) || C2(n)``，共 ``96 + n``
    字节，由本模块 ``encrypt`` 与前端 ``sm-crypto`` 产出。

    部分前端库（Flutter ``gm_crypto``）会在 C1 前追加 ``04`` 非压缩前缀。该前缀
    **无法由首字节判别** —— 裸格式 x 坐标的首字节本身就可能是 ``0x04``（概率
    1/256），旧实现据此剥离会让约 0.39% 的密文解密失败。故改为返回两个候选，
    由调用方逐个试解：SM2 的 C3 是完整性摘要，错误解释只会失败，绝不会解出
    错误明文。

    参数:
    - ciphertext (bytes): 待解密的密文。

    返回:
    - list[bytes]: 长度合法的候选密文（首个为原始输入）；均不合法时返回空列表。
    """
    candidates = [ciphertext]
    if ciphertext[:1] == b"\x04":
        candidates.append(ciphertext[1:])
    return [item for item in candidates if len(item) >= _SM2_RAW_CIPHERTEXT_MIN_SIZE]


class Sm2Cipher:
    """SM2 非对称加密/解密/签名/验签"""

    @staticmethod
    def _strip_04(public_key: str) -> str:
        """
        剥离公钥的 04 非压缩前缀（若存在）。

        历史上底层 ``gmssl`` 用 ``public_key.lstrip("04")`` 去前缀，会把开头
        **所有** ``0``/``4`` 字符全部剥掉而导致公钥长度异常（奇数），
        进而使签名/验签时 Z 值拼接为奇数长度，``binascii.a2b_hex`` 抛
        ``Odd-length string``。这里改为精确去掉开头的 ``04`` 两个字符。

        现用 ``pysmx`` 后不再依赖该行为，保留此归一是为了继续接受 130/128
        两种输入形式，并供 ``_normalize_public_key`` 复用。

        Args:
            public_key: 公钥十六进制字符串（130 字符含 04，或 128 字符不含）

        Returns:
            str: 无 04 前缀的公钥（128 字符 x||y）
        """
        if public_key.startswith("04"):
            return public_key[2:]
        return public_key

    @staticmethod
    def generate_key_pair() -> tuple[str, str]:
        """
        生成 SM2 密钥对。

        Returns:
            tuple[str, str]: (private_key_hex, public_key_hex)
                私钥为 64 字符（32 字节）十六进制字符串
                公钥为 130 字符（65 字节）十六进制字符串（含 04 前缀）
        """
        public_key_bytes, private_key_bytes = _sm2_generate_keypair(_SM2_PARAM_LENGTH)
        return private_key_bytes.hex(), f"04{public_key_bytes.hex()}"

    @staticmethod
    def encrypt(public_key: str, data: bytes) -> bytes:
        """
        SM2 公钥加密。

        Args:
            public_key: 公钥十六进制字符串（130 字符，含 04 前缀）
            data: 待加密的明文数据

        Returns:
            bytes: 加密后的密文
        """
        if not data:
            raise ValueError("SM2 加密失败：明文不能为空")
        public_key_body = _normalize_public_key(public_key)
        # pysmx 的 Encrypt 在 ``KDF(xy, klen)`` 全零时直接 ``return None``，
        # 而国标（GM/T 0003）要求此时「重新选取 k」再算一次。短明文命中概率
        # 不可忽略：实测**单字节明文 0.35%**（≈ 理论值 1/256），多字节/长文本为 0。
        # 因此必须重试，不能首次失败就抛 —— 否则会间歇性报错。
        for _ in range(_SM2_ENCRYPT_MAX_ATTEMPTS):
            try:
                ciphertext = _sm2_encrypt(
                    data, public_key_body, _SM2_PARAM_LENGTH, mode="C1C3C2"
                )
            except Exception as exc:
                raise ValueError(f"SM2 加密失败：{exc}") from exc
            if ciphertext:
                return bytes(ciphertext)
        raise ValueError("SM2 加密失败：随机数连续退化（KDF 输出全零）")

    @staticmethod
    def decrypt(private_key: str, ciphertext: bytes) -> bytes:
        """
        SM2 私钥解密。

        Args:
            private_key: 私钥十六进制字符串
            ciphertext: 待解密的密文数据

        Returns:
            bytes: 解密后的明文

        Raises:
            ValueError: 密文长度不足，或 C3 完整性校验不通过（密钥不匹配/密文损坏）。
        """
        candidates = _candidate_ciphertexts(ciphertext)
        if not candidates:
            raise ValueError(
                f"SM2 解密失败：密文长度不足（{len(ciphertext)} 字节，"
                f"裸 C1C3C2 至少需要 {_SM2_RAW_CIPHERTEXT_MIN_SIZE} 字节）"
            )

        failure = "返回空值"
        for candidate in candidates:
            try:
                plaintext = _sm2_decrypt(
                    candidate, private_key, _SM2_PARAM_LENGTH, mode="C1C3C2"
                )
            except Exception as exc:
                failure = str(exc)
                continue
            if plaintext is not None:
                return bytes(plaintext)
            failure = "C3 完整性校验不通过（密钥不匹配或密文损坏）"
        raise ValueError(f"SM2 解密失败：{failure}")

    @staticmethod
    def sign(private_key: str, public_key: str, data: bytes) -> str:
        """
        SM2 私钥签名（使用 SM3 杂凑）。

        Args:
            private_key: 私钥十六进制字符串
            public_key:  公钥十六进制字符串（130 字符含 04，或 128 字符不含）
            data: 待签名的数据

        Returns:
            str: 签名值（十六进制字符串，通常 128 字符）
        """
        public_key_body = _normalize_public_key(public_key)
        digest = _compute_sm2_digest(public_key_body, data)
        return _new_sm2_signature(digest, private_key).hex()

    @staticmethod
    def verify(public_key: str, data: bytes, signature: str) -> bool:
        """
        SM2 公钥验签。

        Args:
            public_key: 公钥十六进制字符串（130 字符含 04，或 128 字符不含）
            data: 原始数据
            signature: 待验证的签名值

        Returns:
            bool: 签名是否有效
        """
        public_key_body = _normalize_public_key(public_key)
        digest = _compute_sm2_digest(public_key_body, data)
        return bool(
            _sm2_verify(
                bytes.fromhex(signature),
                digest,
                public_key_body,
                _SM2_PARAM_LENGTH,
                Hexstr=1,
            )
        )


# ============================================================
#   SM3 — 哈希（密码加盐）
# ============================================================

class Sm3Cipher:
    """SM3 哈希工具（含密码加盐）"""

    SALT_LENGTH = 16  # 盐值长度（字节）

    @staticmethod
    def hash(data: bytes) -> str:
        """
        SM3 哈希计算。

        Args:
            data: 待哈希的数据

        Returns:
            str: 64 字符十六进制哈希值
        """
        return _sm3_digest_hex(data)

    @staticmethod
    def generate_salt() -> str:
        """
        生成随机盐值。

        Returns:
            str: 十六进制盐值字符串
        """
        return secrets.token_hex(Sm3Cipher.SALT_LENGTH)

    @classmethod
    def hash_password(cls, password: str, salt: str | None = None) -> tuple[str, str]:
        """
        对密码进行 SM3 加盐哈希。

        存储格式: salt$hash
        - salt: 十六进制盐值（32 字符）
        - hash: SM3(password + salt)（64 字符）

        Args:
            password: 明文密码
            salt: 可选盐值，不传则自动生成

        Returns:
            tuple[str, str]: (salt, hash_value)
        """
        if salt is None:
            salt = cls.generate_salt()
        hash_value = cls.hash((password + salt).encode("utf-8"))
        return salt, hash_value

    @classmethod
    def verify_password(cls, password: str, stored_value: str) -> bool:
        """
        验证密码是否匹配存储值。

        Args:
            password: 待验证的明文密码
            stored_value: 存储值（salt$hash）

        Returns:
            bool: 密码是否匹配
        """
        if "$" not in stored_value:
            return False
        salt, expected_hash = stored_value.split("$", 1)
        _, actual_hash = cls.hash_password(password, salt=salt)
        return actual_hash == expected_hash


# ============================================================
#   SM4 — 对称加密
# ============================================================

class Sm4Cipher:
    """SM4-CBC 对称加密工具"""

    @staticmethod
    def get_config_key() -> bytes:
        """
        从配置中获取 SM4 密钥。

        Returns:
            bytes: 16 字节密钥

        Raises:
            ValueError: 密钥未配置时抛出
        """
        key_hex = settings.SM4_KEY
        if not key_hex:
            raise ValueError("SM4_KEY 未配置，请在 .env 中设置")
        return bytes.fromhex(key_hex)

    @staticmethod
    def generate_key() -> bytes:
        """
        生成 SM4 密钥（16 字节 / 128 位）。

        Returns:
            bytes: 16 字节随机密钥
        """
        return os.urandom(16)

    @staticmethod
    def encrypt(key: bytes, plaintext: bytes, iv: bytes | None = None) -> bytes:
        """
        SM4-CBC 加密（PKCS7 填充）。

        Args:
            key: 16 字节密钥
            plaintext: 明文数据
            iv: 可选 IV（16 字节），不传则自动生成

        Returns:
            bytes: iv(16) + ciphertext 拼接结果
        """
        if iv is None:
            iv = os.urandom(16)
        cipher = _SM4()
        cipher.set_key(key, _SM4_ENCRYPT)
        encrypted = bytes(cipher.crypt_cbc(iv, plaintext))
        if not encrypted:
            raise ValueError("SM4 加密失败：返回空值")
        return iv + encrypted

    @staticmethod
    def decrypt(key: bytes, data: bytes) -> bytes:
        """
        SM4-CBC 解密。

        Args:
            key: 16 字节密钥
            data: iv(16) + ciphertext 拼接数据

        Returns:
            bytes: 解密后的明文
        """
        if len(data) <= _SM4_BLOCK_SIZE:
            raise ValueError("SM4 解密失败：数据长度不足（缺 IV 或密文）")
        iv = data[:_SM4_BLOCK_SIZE]
        ciphertext = data[_SM4_BLOCK_SIZE:]
        cipher = _SM4()
        cipher.set_key(key, _SM4_DECRYPT)
        return bytes(cipher.crypt_cbc(iv, ciphertext))
