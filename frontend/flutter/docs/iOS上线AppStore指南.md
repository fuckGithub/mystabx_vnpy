# Flutter iOS 上线 App Store 完整指南

> 最后更新：2026-09-18
>
> 本文档覆盖从证书配置到审核上架的完整流程，适配本项目 Makefile、`.env` 版本机制与 Swift Package Manager 依赖管理。
> 前置阅读：[环境与版本控制.md](环境与版本控制.md)（版本号单一来源）、[jpush_setup.md](jpush_setup.md)（推送配置）。

## 一、前置条件

| 项目 | 要求 |
|------|------|
| 硬件 | macOS 14 Sonoma 及以上 |
| Xcode | 16+（2025 年起 App Store 强制要求） |
| Flutter | 3.44+（`flutter doctor` 无报错） |
| Apple Developer | 年费 $99，个人/企业账号均可 |
| 依赖管理 | **Swift Package Manager**（本项目无 Podfile，无需 `pod install`） |

## 二、证书与描述文件

### 2.1 创建 App ID

1. 登录 [Apple Developer](https://developer.apple.com/account/) → Identifiers → `+`
2. 选 Explicit App ID，Bundle ID = `com.transcendtech.qiyun`（与 Xcode 一致）
3. 勾选 Push Notifications（推送需要，详见 [jpush_setup.md](jpush_setup.md)）

### 2.2 生成发布证书

1. 钥匙串访问 → 证书助理 → 从 CA 请求证书 → 保存 `.certSigningRequest`
2. Developer 后端 → Certificates → `+` → Production → App Store and Ad Hoc
3. 上传 CSR → 下载 `.cer` → 双击导入钥匙串

### 2.3 创建描述文件

1. Profiles → `+` → App Store → 关联 App ID + 发布证书
2. 下载 `.mobileprovision` → 双击导入 Xcode

### 2.4 Xcode 签名配置

1. 打开 `ios/Runner.xcworkspace`
2. Runner target → Signing & Capabilities → 选择开发者团队
3. 确认 Bundle ID、证书、描述文件自动匹配

## 三、构建 IPA

### 3.1 使用 Makefile（推荐）

```bash
# 生产 IPA（默认 ENV=prod，development 导出）
make build-ipa
# → 产物：build/ios/ipa/启运网-3.0.0-300.ipa

# dev 测试 IPA
make build-ipa ENV=dev
# → 产物：build/ios/ipa/启运网-3.0.0-alpha-301.ipa

# App Store 导出（需 App Store 分发证书）
make build-ipa EXPORT_METHOD=app-store
```

版本号从 `lib/env/.env.prod` 的 `APP_VERSION` / `APP_BUILD` 自动推导，无需手动指定 `--build-name` / `--build-number`。详见 [环境与版本控制.md](环境与版本控制.md)。

### 3.2 手动构建

```bash
flutter clean
flutter pub get
flutter build ipa --release --obfuscate --split-debug-info=build/ios/debug-info --dart-define=ENV=prod
```

产物：`build/ios/ipa/` 目录。

> ⚠️ 本项目 iOS 依赖用 **Swift Package Manager**，无 Podfile，**不需要 `pod install`**。

## 四、上传到 App Store Connect

### 4.1 Transporter（推荐）

1. 从 App Store 下载 [Transporter](https://apps.apple.com/app/transporter/id1450874784)
2. 登录 Apple ID → 拖入 IPA → 点击交付
3. 等待 10-30 分钟，App Store Connect「构建版本」出现

### 4.2 Xcode Organizer

1. Xcode → Window → Organizer → Archives → Distribute App → App Store Connect

### 4.3 命令行（xcrun）

```bash
xcrun altool --upload-app --type ios \
  --file build/ios/ipa/启运网-3.0.0-300.ipa \
  --apiKey YOUR_KEY_ID --apiIssuer YOUR_ISSUER_ID
```

## 五、App Store Connect 配置

登录 [App Store Connect](https://appstoreconnect.apple.com/) → 新建 App：

| 项目 | 要求 |
|------|------|
| 平台 | iOS |
| 名称 | 2-30 字符，未被占用 |
| Bundle ID | 关联 `com.transcendtech.qiyun` |
| SKU | 自定义标识 |
| 图标 | 1024×1024，无圆角无透明通道 |
| 截图 | 6.5" / 5.5" 真实界面截图 |
| 描述 | 1-4000 字符 |
| 关键词 | ≤100 字符 |
| 隐私政策 URL | 必填 |
| 技术支持 URL | 必填 |

## 六、提交审核

### 6.1 审核问卷

- 加密：本项目仅用标准 HTTPS/TLS，在 `Info.plist` 已声明 `ITSAppUsesNonExemptEncryption=false`，可跳过加密合规确认
- 广告标识符：如实填写
- 测试账号：填入审核备注栏

### 6.2 审核周期

常规 1-3 个工作日。审核通过后可选自动发布或手动发布。

## 七、2026 年避坑要点

| 要点 | 说明 |
|------|------|
| **Privacy Manifest** | 必须添加 `PrivacyInfo.xcprivacy`，声明所有隐私 API 用途，否则直接打回 |
| **权限描述** | Info.plist 中所有 `*UsageDescription` 必须有清晰中文说明，禁止空描述 |
| **Xcode 版本** | 2025 年起必须 Xcode 16+ 构建提交，旧版本直接拒绝 |
| **出口合规** | `ITSAppUsesNonExemptEncryption=false` 跳过每次提交的加密确认弹窗 |
| **IAP 内购** | 虚拟数字商品必须接入苹果 IAP，禁止引导第三方支付 |
| **dSYM** | Xcode Organizer 确认符号文件完整，缺失会导致崩溃日志无法解析 |
| **UGC 审核** | 用户生成内容入口需有基础内容审核机制 |

## 八、提审前快速自检

### 基础构建

- [ ] `flutter clean` + `flutter pub get` 完成（无 `pod install`，本项目用 SPM）
- [ ] 签名证书是 Apple Distribution（非 Development）
- [ ] 版本号 + 构建号大于所有已提交版本（`APP_BUILD` 递增）
- [ ] 1024×1024 App 图标无 Alpha 通道、无圆角

### 隐私合规

- [ ] `PrivacyInfo.xcprivacy` 已添加
- [ ] Info.plist 所有权限有中文描述
- [ ] App Store Connect 隐私问卷与实际数据收集一致
- [ ] `ITSAppUsesNonExemptEncryption=false` 已声明

### 功能验证

- [ ] 真机 Release 模式跑通全流程，无崩溃/白屏/接口报错
- [ ] 审核测试账号已准备并填入备注
- [ ] 截图尺寸合规，展示内容与实际一致
- [ ] 所有必填元数据已补全

### 收尾

- [ ] 虚拟商品已接入 IAP
- [ ] dSYM 符号文件完整
- [ ] UGC 内容有审核机制

## 九、相关文档

| 文档 | 内容 |
|------|------|
| [环境与版本控制.md](环境与版本控制.md) | `.env` 版本机制、Makefile 构建命令 |
| [jpush_setup.md](jpush_setup.md) | JPush 推送配置（含 APNs Token Auth） |
| [权限管理说明.md](权限管理说明.md) | 相机/定位/相册权限声明与引导 |
