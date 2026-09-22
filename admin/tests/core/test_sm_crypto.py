"""国密（SM2/SM3/SM4）加密契约测试。

本文件锁定的是**对外契约**而非实现细节，用于在更换底层国密库时充当安全网
（2026-09 已据此完成 ``gmssl`` → ``snowland-smx`` 迁移，迁移后本文件原样全绿）：

1. **算法正确性** —— SM3/SM4 对齐国标已知向量，换库后必须仍然一致。
2. **字节格式** —— SM2 密文为 C1C3C2 且无 ASN.1 包装、签名为裸 r||s。
   这是与前端 ``sm-crypto``（Web/UniApp）和 ``gm_crypto``（Flutter）互通的前提，
   格式一变前端就全部解不开。
3. **存量数据** —— 磁盘上已有的密文与 ``salt$hash`` 密码哈希必须仍可解、可验，
   否则升级即等于毁掉全部用户密码与加密字段。

任何换库改动都必须先让本文件全绿。
"""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy.engine import Dialect

from app.config.setting import settings
from app.utils.sm_crypto import Sm2Cipher, Sm3Cipher, Sm4Cipher
from app.utils.sm_crypto_util import CommonCryptogramUtil, PwdUtil, Sm4CbcTypeHandler

# ------------------------------------------------------------------
#  golden 向量（冻结的存量数据，不得随实现变更而失效）
# ------------------------------------------------------------------

GOLDEN_SM2_PRIV = "fef1cd14d44d8a57afa854312a2fb11155638a9d6444d8a35db0e75cf4949246"
GOLDEN_SM2_PUB = (
    "046574bf3f968a9fc217ce48f65543c64be1a6a8dc8325ffed3125e425fb09626"
    "b3996ca6e16bc109c3e43a1133a2c16485f4f67dd0d8dded6b837f4e9dca2ea21"
)
GOLDEN_SM2_MSG = "fastapiadmin-国密契约"
GOLDEN_SM2_CT = (
    "5e2ad5aa14c202bcb8653d1edcb4c13a89a7c959a50d6056679ccc8229b69ce0"
    "4cd1df4597e9bdfb05007785a514af83a70f09a66767784522b18da00fe9a75a"
    "f2262f8d9d6b18a303953eb121947f8540dbeef01003e6dc09f9aa6850929245"
    "a6b8b306e770b524180f61aebfb1e2c151918747d7a401c8a6"
)
GOLDEN_SM2_SIG = (
    "6512c757cb3e105aac6e6d9ca66f9d9b9badaba2eb45ec04768df6be2ed37e0e"
    "45619e22909951cc909fbe8e5ca2acc47b22a44b35e99856e8e4f3daf947e6ce"
)
# 首字节恰为 0x04 的**合法裸** C1C3C2 密文：x 坐标首字节本身就是 0x04。
# 用于锁定「按首字节剥离 04 前缀」启发式的回归 —— 该做法会把真正的 x 坐标首字节
# 吃掉，使约 1/256（≈0.39%）的密文解密随机失败。明文同 GOLDEN_SM2_MSG。
GOLDEN_SM2_CT_LEADING_04 = (
    "044a6aab51879c22a823c7e9c305978679fbe222f37f8492c25b61fd295e7621"
    "0274dadbe2d1585ab5266e54661c02fd5f839e90b1f74e16ff7c369059417052"
    "d7d3498ea4527a2ccb9772694461a9c1778df1948e9f95b27af0942997c58446"
    "d5ca11a5bcfcbc29b4a7ffe4483cc3373f5928198b3bd9b0e0"
)
# salt 固定为 32 个 'a'，便于验证 hash 的确定性（真实场景由 secrets 生成）
GOLDEN_PWD = (
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa$"
    "d213b154ddba7eda7f38786f4675d1e3b926d32192a7306e7bcb8d2ea62c68fc"
)
GOLDEN_PWD_PLAIN = "admin123"

GOLDEN_SM4_KEY_HEX = "0123456789abcdeffedcba9876543210"
GOLDEN_SM4_IV_HEX = "00000000000000000000000000000000"
# CBC 使用全零 IV 时，第一块密文恒等于 ECB(明文块)，故以下为与实现无关的已知答案
GOLDEN_SM4_BLOCK_CIPHER = "99ce75c0ca2949d3eb87bd2d831f3510"

# 国标 SM3 标准测试向量：SM3("abc")
SM3_ABC_VECTOR = "66c7f0f462eeedd9d1f2d46bdc10e4e24167c4875cf2f7a2297da02b8f4ba8e0"


# ------------------------------------------------------------------
#  SM3 — 哈希
# ------------------------------------------------------------------

def test_sm3_matches_standard_vector() -> None:
    """SM3("abc") 必须等于国标标准测试向量（锁死算法正确性）。"""
    assert Sm3Cipher.hash(b"abc") == SM3_ABC_VECTOR


def test_sm3_hash_is_stable_and_hex64() -> None:
    """SM3 输出为 64 字符小写十六进制，且同输入恒等。"""
    first = Sm3Cipher.hash(b"fastapiadmin")
    assert first == Sm3Cipher.hash(b"fastapiadmin")
    assert len(first) == 64
    assert first == first.lower()
    int(first, 16)  # 可解析为十六进制


def test_sm3_password_hash_format_and_verify() -> None:
    """密码哈希格式为 ``salt$hash``，编码正确，且正误密码判定正确。"""
    salt, hash_value = Sm3Cipher.hash_password(GOLDEN_PWD_PLAIN)

    assert len(salt) == 32, "盐值应为 16 字节（32 字符十六进制）"
    assert len(hash_value) == 64, "SM3 摘要应为 32 字节（64 字符十六进制）"
    int(salt, 16)
    int(hash_value, 16)

    stored = f"{salt}${hash_value}"
    assert Sm3Cipher.verify_password(GOLDEN_PWD_PLAIN, stored) is True
    assert Sm3Cipher.verify_password("wrong-password", stored) is False


def test_sm3_password_uses_unique_salt() -> None:
    """相同密码两次哈希必须得到不同结果（盐值随机）。"""
    first = Sm3Cipher.hash_password(GOLDEN_PWD_PLAIN)
    second = Sm3Cipher.hash_password(GOLDEN_PWD_PLAIN)
    assert first != second
    assert Sm3Cipher.verify_password(GOLDEN_PWD_PLAIN, f"{first[0]}${first[1]}")


def test_sm3_verify_password_rejects_malformed_stored_value() -> None:
    """库中存量值若不含 ``$`` 分隔符则应判定失败，而不是抛异常。"""
    assert Sm3Cipher.verify_password(GOLDEN_PWD_PLAIN, "not-a-valid-hash") is False


def test_golden_password_hash_still_verifies() -> None:
    """存量密码哈希必须仍可校验（换库后旧用户不能全部无法登录）。"""
    assert Sm3Cipher.verify_password(GOLDEN_PWD_PLAIN, GOLDEN_PWD) is True


def test_golden_hash_value_is_unchanged() -> None:
    """固定盐值下的哈希值必须逐字节复现（锁定 SM3 实现，不受换库影响）。"""
    _, hash_value = Sm3Cipher.hash_password(GOLDEN_PWD_PLAIN, salt="a" * 32)
    assert f"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa${hash_value}" == GOLDEN_PWD


# ------------------------------------------------------------------
#  SM2 — 密钥 / 格式契约
# ------------------------------------------------------------------

def test_sm2_generate_key_pair_is_consistent() -> None:
    """生成的密钥对必须自洽：公钥为 130 字符且带 04 前缀，可加解密与签名验签。"""
    private_key, public_key = Sm2Cipher.generate_key_pair()

    assert len(private_key) == 64, "私钥应为 32 字节（64 字符十六进制）"
    assert public_key.startswith("04"), "公钥应为非压缩格式，带 04 前缀"
    assert len(public_key) == 130, "非压缩公钥应为 65 字节（130 字符十六进制）"

    ciphertext = Sm2Cipher.encrypt(public_key, b"round-trip")
    assert Sm2Cipher.decrypt(private_key, ciphertext) == b"round-trip"

    signature = Sm2Cipher.sign(private_key, public_key, b"round-trip")
    assert Sm2Cipher.verify(public_key, b"round-trip", signature) is True


def test_sm2_ciphertext_is_c1c3c2_without_asn1() -> None:
    """SM2 密文必须为裸 C1C3C2（64 + 32 + len），不得含 ASN.1 包装。

    前端 ``sm-crypto`` / ``gm_crypto`` 依赖此格式，若底层库改用
    ``C1C3C2_ASN1``（首字节 0x30）则前端全部解密失败。
    """
    plaintext = GOLDEN_SM2_MSG.encode("utf-8")
    ciphertext = Sm2Cipher.encrypt(GOLDEN_SM2_PUB, plaintext)

    assert len(ciphertext) == 64 + 32 + len(plaintext)
    assert ciphertext[0] != 0x30, "首字节为 0x30 说明密文被 ASN.1 包装"


def test_sm2_signature_is_raw_rs_without_asn1() -> None:
    """SM2 签名必须为裸 r||s（64 字节 / 128 字符十六进制），不得含 ASN.1 包装。"""
    signature = Sm2Cipher.sign(GOLDEN_SM2_PRIV, GOLDEN_SM2_PUB, GOLDEN_SM2_MSG.encode())

    assert len(signature) == 128, "签名应为 64 字节（128 字符十六进制）"
    assert signature[0] != "30", "以 '30' 开头说明签名被 ASN.1 包装"
    int(signature, 16)


def test_sm2_decrypt_golden_ciphertext() -> None:
    """存量 SM2 密文必须仍可解（换库后历史数据不能作废）。"""
    decrypted = Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, bytes.fromhex(GOLDEN_SM2_CT))
    assert decrypted.decode("utf-8") == GOLDEN_SM2_MSG


def test_sm2_golden_signature_still_verifies() -> None:
    """存量 SM2 签名必须仍可验（换库后历史操作日志的完整性保护不能失效）。"""
    assert Sm2Cipher.verify(GOLDEN_SM2_PUB, GOLDEN_SM2_MSG.encode(), GOLDEN_SM2_SIG) is True


def test_sm2_decrypt_accepts_c1_with_04_prefix() -> None:
    """C1 带 04 前缀的密文必须可解（Flutter 侧 ``gm_crypto`` 的输出格式）。"""
    prefixed = b"\x04" + bytes.fromhex(GOLDEN_SM2_CT)
    assert Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, prefixed).decode("utf-8") == GOLDEN_SM2_MSG


def test_sm2_decrypt_handles_raw_ciphertext_whose_x_starts_with_04() -> None:
    """x 坐标首字节恰为 0x04 的**裸**密文必须可解。

    回归（旧实现 0.39% 概率随机失败）：旧实现用「首字节 == 0x04 就去掉一个字节」
    来兼容带非压缩前缀的密文，但裸 C1C3C2 的 x 坐标首字节本身就可能是 0x04
    （概率 1/256），此时会误删一个有效字节，导致解密失败。

    本用例用**静态**样本锁定该回归，不受随机性影响。
    """
    ciphertext = bytes.fromhex(GOLDEN_SM2_CT_LEADING_04)

    assert ciphertext[:1] == b"\x04", "样本前提：首字节为 0x04"
    assert len(ciphertext) == 96 + len(GOLDEN_SM2_MSG.encode("utf-8")), "样本应为裸格式"
    assert Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, ciphertext).decode("utf-8") == GOLDEN_SM2_MSG


def test_sm2_decrypt_rejects_tampered_ciphertext() -> None:
    """篡改密文必须报错，绝不能静默返回错误明文。

    这是「按完整性校验回退」方案的安全前提：错误解释只能失败，不会产出假明文。
    """
    tampered = bytearray(bytes.fromhex(GOLDEN_SM2_CT))
    tampered[100] ^= 0xFF  # 改动 C2 区域一个字节
    with pytest.raises(ValueError):
        Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, bytes(tampered))


@pytest.mark.parametrize(
    "payload",
    [b"a", "中文密码与 emoji 🔐".encode(), b"x" * 512],
    ids=["单字节", "多字节字符", "长文本"],
)
def test_sm2_encrypt_decrypt_roundtrip(payload: bytes) -> None:
    """各种长度/编码的明文加解密往返一致。"""
    ciphertext = Sm2Cipher.encrypt(GOLDEN_SM2_PUB, payload)
    assert Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, ciphertext) == payload


def test_sm2_encrypt_retries_when_kdf_outputs_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``t = KDF(xy, klen)`` 全零导致 pysmx 返回 None 时必须重试，而非直接报错。

    回归：pysmx 的 ``Encrypt`` 在 ``t`` 全零时直接 ``return None``，而国标
    （GM/T 0003）要求此时「重新选取 k」再算。**单字节明文命中概率 ≈1/256**
    （实测 0.35%，多字节/长文本为 0）；原实现首次失败即抛 ``ValueError``，
    既让约 0.35% 的加密直接失败，也让上面的往返用例间歇性 flaky。

    本用例用打桩**确定性**地模拟「首次全零、次次正常」，不受随机性影响。
    """
    from app.utils import sm_crypto

    real_encrypt = sm_crypto._sm2_encrypt
    calls = {"n": 0}

    def flaky_encrypt(data, public_key, len_param, **kwargs):
        """首次返回 None（模拟 KDF 全零），之后走真实实现。"""
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return real_encrypt(data, public_key, len_param, **kwargs)

    monkeypatch.setattr(sm_crypto, "_sm2_encrypt", flaky_encrypt)
    ciphertext = Sm2Cipher.encrypt(GOLDEN_SM2_PUB, b"a")

    assert calls["n"] == 2, "首次返回 None 后必须换随机数重试，而不是直接抛错"
    monkeypatch.undo()
    assert Sm2Cipher.decrypt(GOLDEN_SM2_PRIV, ciphertext) == b"a"


def test_sm2_encrypt_raises_after_repeated_kdf_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """连续退化时必须抛错，不得返回空密文、也不得无限重试。"""
    from app.utils import sm_crypto

    monkeypatch.setattr(sm_crypto, "_sm2_encrypt", lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="随机数连续退化"):
        Sm2Cipher.encrypt(GOLDEN_SM2_PUB, b"a")


def test_sm2_encrypt_rejects_empty_plaintext_known_limitation() -> None:
    """记录已知局限：SM2 空明文无法加密。

    KDF 输入长度为 0 时无法派生密钥（历史库与当前 ``pysmx`` 均抛 ``ValueError``，
    只是内部触发点不同）；``Sm2Cipher.encrypt`` 在入口显式抛出，消息更明确。
    生产调用方（登录密码解密、字段加密）不会传空串，故无需规避。
    """
    with pytest.raises(ValueError):
        Sm2Cipher.encrypt(GOLDEN_SM2_PUB, b"")


def test_sm2_verify_rejects_tampered_data() -> None:
    """篡改原文后验签必须失败。"""
    signature = Sm2Cipher.sign(GOLDEN_SM2_PRIV, GOLDEN_SM2_PUB, b"original")
    assert Sm2Cipher.verify(GOLDEN_SM2_PUB, b"tampered", signature) is False


def test_sm2_verify_rejects_tampered_signature() -> None:
    """篡改签名后验签必须失败。"""
    signature = Sm2Cipher.sign(GOLDEN_SM2_PRIV, GOLDEN_SM2_PUB, b"original")
    flipped = ("0" if signature[0] != "0" else "1") + signature[1:]
    assert Sm2Cipher.verify(GOLDEN_SM2_PUB, b"original", flipped) is False


def test_strip_04_only_removes_two_chars() -> None:
    """回归防护：精确剥离 04 前缀，而非 ``str.lstrip("04")``。

    历史背景：旧库 ``gmssl`` 的 ``CryptSM2.__init__`` 使用
    ``public_key.lstrip("04")``，会剥掉开头**所有** ``0``/``4`` 字符，
    使公钥变成奇数长度，签名时 ``binascii.a2b_hex`` 抛 ``Odd-length string``。
    现用 ``pysmx`` 后不再触发该缺陷，但该归一化仍需精确语义（现用于统一接受
    130/128 两种输入），故用全 ``0`` 的公钥体把行为钉住。
    """
    body = "0" * 126
    assert Sm2Cipher._strip_04("04" + body) == body

    # 不含 04 前缀时原样返回
    assert Sm2Cipher._strip_04(body) == body

    # 仅当恰好以 "04" 开头才剥离两个字符
    assert Sm2Cipher._strip_04("0400") == "00"


# ------------------------------------------------------------------
#  SM4 — 对称加密
# ------------------------------------------------------------------

def test_sm4_cbc_known_answer_with_zero_iv() -> None:
    """全零 IV 下 CBC 第一块密文等于 ECB 已知答案（锁死 SM4 算法正确性）。"""
    key = bytes.fromhex(GOLDEN_SM4_KEY_HEX)
    iv = bytes.fromhex(GOLDEN_SM4_IV_HEX)

    encrypted = Sm4Cipher.encrypt(key, b"A" * 16, iv=iv)
    assert encrypted[:16] == iv, "输出必须以 IV 开头"
    assert encrypted[16:32].hex() == GOLDEN_SM4_BLOCK_CIPHER


def test_sm4_cbc_roundtrip_and_lengths() -> None:
    """SM4-CBC 采用 PKCS7 填充：输出为 iv(16) + 整块密文。"""
    key = bytes.fromhex(GOLDEN_SM4_KEY_HEX)

    for length in (1, 15, 16, 17, 32):
        plaintext = b"A" * length
        encrypted = Sm4Cipher.encrypt(key, plaintext)

        assert len(encrypted) % 16 == 0, "输出长度应为 16 的整数倍"
        assert len(encrypted) == 16 + ((length // 16) + 1) * 16, "应为 iv + PKCS7 整块"
        assert Sm4Cipher.decrypt(key, encrypted) == plaintext


def test_sm4_ciphertext_is_not_plaintext() -> None:
    """密文不得泄漏明文，且相同明文两次加密结果不同（IV 随机）。"""
    key = bytes.fromhex(GOLDEN_SM4_KEY_HEX)
    plaintext = b"idcard-1234567890"

    first = Sm4Cipher.encrypt(key, plaintext)
    second = Sm4Cipher.encrypt(key, plaintext)

    assert plaintext not in first
    assert first != second, "IV 应随机生成"
    assert Sm4Cipher.decrypt(key, first) == Sm4Cipher.decrypt(key, second) == plaintext


def test_sm4_decrypt_tampered_ciphertext_does_not_return_plaintext() -> None:
    """密文被篡改后不得还原出原文（可能抛异常，也可能解密出乱码）。"""
    key = bytes.fromhex(GOLDEN_SM4_KEY_HEX)
    plaintext = b"idcard-1234567890"
    encrypted = bytearray(Sm4Cipher.encrypt(key, plaintext))

    encrypted[20] ^= 0xFF  # 翻转密文块中的一位
    try:
        result = Sm4Cipher.decrypt(key, bytes(encrypted))
    except Exception:
        return
    assert result != plaintext


def test_sm4_generate_key_is_16_bytes() -> None:
    """生成的 SM4 密钥为 16 字节且随机。"""
    first = Sm4Cipher.generate_key()
    assert len(first) == 16
    assert first != Sm4Cipher.generate_key()


def test_sm4_get_config_key_requires_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置 ``SM4_KEY`` 时必须显式报错，不得静默使用空密钥。"""
    monkeypatch.setattr(settings, "SM4_KEY", "")
    with pytest.raises(ValueError, match="SM4_KEY 未配置"):
        Sm4Cipher.get_config_key()


def test_sm4_get_config_key_reads_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """配置正确时返回 16 字节密钥。"""
    monkeypatch.setattr(settings, "SM4_KEY", GOLDEN_SM4_KEY_HEX)
    assert Sm4Cipher.get_config_key() == bytes.fromhex(GOLDEN_SM4_KEY_HEX)


# ------------------------------------------------------------------
#  门面与 TypeDecorator
# ------------------------------------------------------------------

@pytest.fixture
def sm_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """把 golden 密钥对与 SM4 密钥注入配置，供门面层测试使用。"""
    monkeypatch.setattr(settings, "SM2_PRIVATE_KEY", GOLDEN_SM2_PRIV)
    monkeypatch.setattr(settings, "SM2_PUBLIC_KEY", GOLDEN_SM2_PUB)
    monkeypatch.setattr(settings, "SM4_KEY", GOLDEN_SM4_KEY_HEX)


def test_common_cryptogram_util_sm2_roundtrip(sm_settings: None) -> None:
    """门面层 SM2 加解密往返一致，密文为十六进制字符串。"""
    encrypted = CommonCryptogramUtil.do_sm2_encrypt(GOLDEN_SM2_MSG)

    assert isinstance(encrypted, str)
    bytes.fromhex(encrypted)  # 必须是合法十六进制
    assert CommonCryptogramUtil.do_sm2_decrypt(encrypted) == GOLDEN_SM2_MSG


def test_common_cryptogram_util_signature_roundtrip(sm_settings: None) -> None:
    """门面层签名/验签往返一致（操作日志完整性保护走此路径）。"""
    signature = CommonCryptogramUtil.do_signature(GOLDEN_SM2_MSG)

    assert CommonCryptogramUtil.do_verify_signature(GOLDEN_SM2_MSG, signature) is True
    assert CommonCryptogramUtil.do_verify_signature("被篡改", signature) is False


def test_common_cryptogram_util_hash_value(sm_settings: None) -> None:
    """门面层 SM3 哈希与标准向量一致。"""
    assert CommonCryptogramUtil.do_hash_value("abc") == SM3_ABC_VECTOR


def test_pwd_util_roundtrip() -> None:
    """``PwdUtil`` 存储格式为 ``salt$hash``，且正误密码判定正确。"""
    stored = PwdUtil.set_password_hash(GOLDEN_PWD_PLAIN)

    assert stored.count("$") == 1
    salt, hash_value = stored.split("$")
    assert len(salt) == 32
    assert len(hash_value) == 64
    assert PwdUtil.verify_password(GOLDEN_PWD_PLAIN, stored) is True
    assert PwdUtil.verify_password("wrong-password", stored) is False


def test_pwd_util_verifies_golden_hash() -> None:
    """``PwdUtil`` 必须能校验存量密码哈希。"""
    assert PwdUtil.verify_password(GOLDEN_PWD_PLAIN, GOLDEN_PWD) is True


@pytest.mark.parametrize(
    ("password", "expected_reason"),
    [
        ("abc12", "密码长度至少6位"),
        ("abcdef", "密码需要包含数字"),
        ("123456", "密码需要包含小写字母"),
    ],
)
def test_pwd_util_check_password_strength(password: str, expected_reason: str) -> None:
    """弱密码必须返回具体原因。"""
    assert PwdUtil.check_password_strength(password) == expected_reason


def test_pwd_util_accepts_strong_password() -> None:
    """满足全部规则的密码返回 None。"""
    assert PwdUtil.check_password_strength("admin123") is None


def _no_dialect() -> Dialect:
    """``TypeDecorator`` 的 ``dialect`` 参数在本组用例中不被使用。

    该处理器只做纯文本加解密，不依赖方言；但 ``dialect`` 是位置必填参数，
    故用 ``None`` 占位并显式声明返回类型，避免类型检查报 None 不可赋值。

    返回:
    - Dialect: 占位值（实际为 ``None``）。
    """
    return cast("Dialect", None)


def test_sm4_type_handler_roundtrip(sm_settings: None) -> None:
    """``Sm4CbcTypeHandler`` 写入加密、读取解密，且存库值为十六进制。"""
    handler = Sm4CbcTypeHandler(255)
    id_card = "110101199003071234"

    stored = handler.process_bind_param(id_card, _no_dialect())

    assert stored is not None
    assert id_card not in stored, "存库值不得含明文"
    bytes.fromhex(stored)
    assert handler.process_result_value(stored, _no_dialect()) == id_card


def test_sm4_type_handler_passes_through_none(sm_settings: None) -> None:
    """``None`` 应原样透传（可空字段）。"""
    handler = Sm4CbcTypeHandler(255)
    assert handler.process_bind_param(None, _no_dialect()) is None
    assert handler.process_result_value(None, _no_dialect()) is None


def test_sm4_type_handler_returns_raw_value_on_failure(sm_settings: None) -> None:
    """解密失败时回退为原值，不得抛异常阻塞查询（历史明文数据兼容）。"""
    handler = Sm4CbcTypeHandler(255)
    assert handler.process_result_value("not-encrypted-legacy-value", _no_dialect()) == (
        "not-encrypted-legacy-value"
    )
