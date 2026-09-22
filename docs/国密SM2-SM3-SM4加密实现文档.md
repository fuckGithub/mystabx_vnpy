# 国密（SM2/SM3/SM4）加密实现文档

## 一、概述

本项目使用国家标准密码算法（国密）替代国际通用加密方案，覆盖**登录加密传输**、**密码哈希存储**、**数据签名验签**、**敏感字段加密**四个场景。

| 算法    | 用途                                 | 前端库                                           | 后端库                  |
| ------- | ------------------------------------ | ------------------------------------------------ | ----------------------- |
| **SM2** | 非对称加密（登录密码传输）、数据签名 | `sm-crypto` (Web/UniApp) / `gm_crypto` (Flutter) | `snowland-smx` (Python) |
| **SM3** | 密码加盐哈希（替代 bcrypt）          | —                                                | `snowland-smx`          |
| **SM4** | 对称加密（敏感字段如身份证）         | —                                                | `snowland-smx`          |

> 后端库为 `snowland-smx`（导入名 `pysmx`），纯 Python、BSD-3-Clause、跨平台无需编译。
> 2026-09 由 `gmssl` 迁移而来（后者末次发布 2023-02，已停更），**对外契约与存量数据完全不变**。

---

## 二、后端实现

### 2.1 文件结构

```
backend/app/utils/
├── sm_crypto.py                # SM2/SM3/SM4 算法实现层
├── sm_crypto_util.py           # 唯一入口：CommonCryptogramUtil + PwdUtil + Sm4CbcTypeHandler
backend/app/config/setting.py   # SM2/SM4 密钥配置
backend/env/.env                # 密钥值
```

### 2.2 配置项 (`setting.py`)

```python
SM2_PRIVATE_KEY: str = ""  # SM2 私钥（64 hex chars / 32 bytes）
SM2_PUBLIC_KEY: str = ""   # SM2 公钥（130 hex chars / 65 bytes，含 04 前缀）
SM4_KEY: str = ""          # SM4 密钥（32 hex chars / 16 bytes）
```

> 公钥生成/存储/返回统一带 `04` 前缀（130 字符），无需任何地方手动拼接。

### 2.3 核心类 `Sm2Cipher`

```python
class Sm2Cipher:
    _strip_04(public_key) -> str                   # 精确剥离 04 前缀，归一化为 128 字符
    generate_key_pair() -> (private_key, "04" + public_key)
    encrypt(public_key, data: bytes) -> bytes       # mode="C1C3C2"（裸格式）
    decrypt(private_key, ciphertext: bytes) -> bytes # 自动剥离 04 前缀
    sign(private_key, public_key, data: bytes) -> str
    verify(public_key, data: bytes, signature: str) -> bool
```

**关键设计：**

- 密文为**裸 C1C3C2**（`x(32)‖y(32)‖C3(32)‖C2(n)`，无 ASN.1 包装）— 兼容所有前端库
- 签名为**裸 r‖s**（64 字节 / 128 字符十六进制，无 ASN.1 包装）
- `decrypt()` 首字节检测 `0x04` 自动剥离 — 兼容 Flutter `gm_crypto` 的非压缩格式
- `generate_key_pair()` 返回 `f"04{public_key_hex}"` — 全局统一
- **签名摘要求自行计算**：`pysmx` 的 `Sign`/`Verify` 只接受算好的摘要，故本模块按 GM/T 0003 标准拼装 `ZA = SM3(ENTL‖ID‖a‖b‖xG‖yG‖xA‖yA)`（ID 取默认 `1234567812345678`）并派生 `E = SM3(ZA‖M)`。**这一步必须与历史实现逐位一致，否则磁盘上已存的日志签名将全部无法验证** — 已由 `tests/core/test_sm_crypto.py` 的 golden 签名用例锁定。

> **📌 迁移说明（2026-09：`gmssl` → `snowland-smx`）**
>
> 原依赖 `gmssl` 末次发布为 2023-02，已停更。已迁移到纯 Python 的 `snowland-smx`（BSD-3-Clause、跨平台无需编译）。
>
> 迁移后 `tests/core/test_sm_crypto.py`（39 条，含 golden 存量密文/签名/密码哈希）**原样全绿**，即存量数据无需任何转换。
>
> 历史附注：旧库 `CryptSM2.__init__` 曾用 `public_key.lstrip("04")` 去前缀，会把开头**所有** `0`/`4` 字符剥掉导致公钥长度异常（奇数）、签名抛 `Odd-length string`。`Sm2Cipher._strip_04()` 精确剥离两字符规避了该问题；迁移后该归一化保留，用于继续接受 130/128 两种输入。

### 2.4 核心类 `Sm3Cipher`

```python
class Sm3Cipher:
    hash(data: bytes) -> str
    generate_salt() -> str
    hash_password(password, salt) -> (salt, hash)
    verify_password(password, stored) -> bool
```

密码存储格式：`{salt_hex}${hash_hex}`（salt=32 hex chars, hash=64 hex chars）

### 2.5 核心类 `Sm4Cipher`

```python
class Sm4Cipher:
    encrypt(key, plaintext, iv=None) -> bytes  # SM4-CBC + PKCS7
    decrypt(key, data) -> bytes                # 自动提取 IV
    get_config_key() -> bytes
    generate_key() -> bytes
```

输出格式：`iv(16) + ciphertext` 拼接

### 2.6 统一门面 `CommonCryptogramUtil`

```python
class CommonCryptogramUtil:
    do_sm2_encrypt(str_data) -> str
    do_sm2_decrypt(str_data) -> str
    do_signature(str_data) -> str
    do_verify_signature(original, sig) -> bool
    do_hash_value(str_data) -> str
```

所有方法自动使用 `settings` 中配置的密钥。

### 2.7 密码工具 `PwdUtil` (位于 `sm_crypto_util.py`)

```python
class PwdUtil:
    set_password_hash(password) -> str        # SM3 加盐 → "salt$hash"
    verify_password(plain, stored) -> bool    # 验证密码
```

> bcrypt 已完全移除，仅使用 SM3。

### 2.8 加密字段处理器 `Sm4CbcTypeHandler` (位于 `sm_crypto_util.py`)

```python
class Sm4CbcTypeHandler(TypeDecorator):
    # SQLAlchemy 字段加密：写入加密，读取解密
```

用于模型字段：

```python
id_card: Mapped[str | None] = mapped_column(
    Sm4CbcTypeHandler(255), nullable=True, comment="身份证号(SM4加密)"
)
```

> `Sm4CbcTypeHandler` 的 `impl = String`，构造参数为**长度整数**（如 `255`），无需再套 `String()`。

---

> 所有功能统一通过 `sm_crypto_util.py` 导入，`hash_bcrpy_util.py` 和 `sm4_type_handler.py` 已删除。

---

## 三、登录加密流程

```
┌─────────┐         ┌───────────┐         ┌─────────┐
│ 前端     │         │ 后端 API  │         │ 数据库  │
│(Web/Uni )│         │(FastAPI)  │         │ (MySQL) │
└────┬────┘         └─────┬─────┘         └────┬────┘
     │                    │                    │
     │ ① GET /sm-public-key                    │
     │ ◄─── public_key (130 chars, 带04) ─────┤
     │                    │                    │
     │ ② sm2.doEncrypt(    │                    │
     │   password, key)    │                    │
     │                    │                    │
     │ ③ POST /login       │                    │
     │    password=encrypted                    │
     │ ──────────────────► │                    │
     │                    │                    │
     │                    │ ④ do_sm2_decrypt() │
     │                    │                    │
     │                    │ ⑤ 查用户密码 hash   │
     │                    │ ────────────────►  │
     │                    │ ◄── salt$hash ─────│
     │                    │                    │
     │                    │ ⑥ SM3 验证密码     │
     │                    │                    │
     │ ◄─── access_token ──┤                   │
```

### 3.1 公钥接口

```http
GET /api/v1/system/auth/sm-public-key
→ {"code": 0, "data": {"public_key": settings.SM2_PUBLIC_KEY}, "msg": "获取成功"}
```

后端直接返回 `settings.SM2_PUBLIC_KEY`（130 字符，含 04 前缀），无需拼接。

### 3.2 后端解密

```python
# auth/service.py
plain_password = CommonCryptogramUtil.do_sm2_decrypt(login_form.password)
```

- 解密失败抛 `CustomException`（HTTP 200，业务码非零），**无明文降级**
- 解密后明文传给 `PwdUtil.verify_password()` 做 SM3 哈希比对

---

## 四、前端实现

### 4.1 Web 管理后台 (Vue 3)

| 文件                              | 作用                             |
| --------------------------------- | -------------------------------- |
| `src/store/modules/user.store.ts` | 缓存公钥，`sm2.doEncrypt()` 加密 |
| 依赖                              | `sm-crypto@^0.4.0`               |

```typescript
import { sm2 } from 'sm-crypto'

// 公钥长度校验 >= 128（130 字符也满足）
if (key && key.length >= 128) { ... }

// 加密
return sm2.doEncrypt(password, publicKey)
```

### 4.2 UniApp 移动端

| 文件              | 作用                                     |
| ----------------- | ---------------------------------------- |
| `src/api/auth.ts` | `fetchSmPublicKey()` → `sm2.doEncrypt()` |

```typescript
import { sm2 } from "sm-crypto";
const password = sm2.doEncrypt(body.password, publicKey);
```

### 4.3 Flutter 移动端

| 文件                       | 作用                                       |
| -------------------------- | ------------------------------------------ |
| `lib/common/api/user.dart` | 直接导入 `gm_crypto`，`SM2.encrypt()` 加密 |

```dart
import 'package:gm_crypto/gm_crypto.dart';

return SM2.encrypt(password, publicKey);
```

> `sm_crypto.dart` 包装文件已删除，直接使用 `gm_crypto`。

### 4.4 各前端对比

| 前端    | 加密库      | 调用方式                  | 失败行为       |
| ------- | ----------- | ------------------------- | -------------- |
| Web     | `sm-crypto` | `sm2.doEncrypt(pwd, key)` | 抛 Error       |
| UniApp  | `sm-crypto` | `sm2.doEncrypt(pwd, key)` | Promise.reject |
| Flutter | `gm_crypto` | `SM2.encrypt(pwd, key)`   | 抛 Exception   |

**所有前端均无明文降级**，公钥获取失败直接抛异常。

---

## 五、跨平台兼容性

### 5.1 SM2 格式约定

| 环节                | 格式                       | 说明                         |
| ------------------- | -------------------------- | ---------------------------- |
| 生成/存储/返回公钥  | `04` + 128 hex = 130 chars | 统一带 04 前缀               |
| Web/UniApp 加密输出 | C1C3C2 (mode=1)            | `sm-crypto` 默认             |
| Flutter 加密输出    | C1C3C2 + C1 含 04 前缀     | `gm_crypto` 输出格式         |
| 后端解密输入        | 自动剥离 C1 的 04 字节     | `ciphertext[0]==0x04` 则截掉 |

### 5.2 三端登录加密兼容性（实测）

| 端      | 库          | 调用                                  | 输出格式           | 后端解密验证 |
| ------- | ----------- | ------------------------------------- | ------------------ | ------------ |
| UniApp  | `sm-crypto` | `sm2.doEncrypt(pw, pub, 1)`           | C1C3C2             | ✅ 还原明文  |
| Flutter | `gm_crypto` | `SM2.encrypt(pw, pub)`（默认 C1C3C2） | C1C3C2 + `04` 前缀 | ✅ 还原明文  |
| Web     | `sm-crypto` | `sm2.doEncrypt(pw, pub)`              | C1C3C2             | ✅ 还原明文  |

> 三端密文均可被后端 `do_sm2_decrypt()` 正确解密还原明文（实测 `Admin@12345`），无需额外改动。

### 5.3 密码哈希格式

```
存储格式: {salt_hex}${hash_hex}
示例: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6${hash}
 - salt: 32 hex chars (16 bytes)
 - hash: 64 hex chars (32 bytes)
```

---

## 六、环境变量配置

在 `backend/env/.env` 中：

```bash
# SM2 密钥对
SM2_PRIVATE_KEY="your_64_char_private_key_hex"
SM2_PUBLIC_KEY="04your_128_char_public_key_hex"    # 含 04 前缀

# SM4 密钥（用于敏感字段加密）
SM4_KEY="your_32_char_key_hex"
```

---

## 七、测试验证

```bash
# 测试加密登录
cd web && node -e "
const { sm2 } = require('sm-crypto');
const key = '${SM2_PUBLIC_KEY}';  # 130 chars
console.log(sm2.doEncrypt('123456', key));
" | curl -X POST "http://127.0.0.1:18080/api/v1/system/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=\$(cat)&login_type=account&captcha_key=&captcha="
```

---

## 八、重构历程

| 变更                     | 内容                                                                    |
| ------------------------ | ----------------------------------------------------------------------- |
| SM2 mode 统一            | `CryptSM2(mode=1)` 匹配 C1C3C2 格式                                     |
| 04 前缀统一              | 生成时添加，存储 130 字符，API 直接返回                                 |
| Flutter 兼容             | `decrypt()` 自动剥离 C1 的 04 前缀                                      |
| bcrypt 移除              | 全部替换为 SM3 加盐哈希                                                 |
| 开关移除                 | 去除 `SM_CRYPTO_ENABLE`，强制 SM 加密                                   |
| 明文降级移除             | 所有前端+后端，公钥失败直接抛异常                                       |
| Flutter 包装简化         | 删除 `sm_crypto.dart`，直接使用 `gm_crypto`                             |
| gmssl 公钥裁剪缺陷规避   | 新增 `Sm2Cipher._strip_04()` 精确剥离前缀，修复签名 `Odd-length string` |
| `Sm4CbcTypeHandler` 用法 | 构造参数用长度整数 `Sm4CbcTypeHandler(255)`，不再套 `String()`          |
| 三端登录兼容实测         | UniApp/Flutter/Web 密文均可被后端解密还原（验证 `Admin@12345`）         |
| CustomException 默认 200 | 登录失败业务层返回 200 而非 500                                         |
