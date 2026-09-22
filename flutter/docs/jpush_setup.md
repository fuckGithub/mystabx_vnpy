# JPush 极光推送配置文档

## 概览

本文档记录 Flutter 司机端 App 的 JPush 推送全链路配置，覆盖从 Apple 开发者账号配置到极光后台上线的完整流程，对齐 Android/iOS 原生实现。

**iOS 认证方式：Token Authentication（APNs Auth Key）**，替代旧的 .p12 证书方式。

---

## 1. 前置准备：Apple 开发者账号配置

### 1.1 App ID 推送权限开启

1. 登录 [Apple 开发者中心](https://developer.apple.com/account)，进入「Certificates, Identifiers & Profiles」
2. 选择 **Identifiers** 分类，找到与项目 Bundle ID 匹配的 App ID
3. 在权限列表中勾选 **Push Notifications**，保存配置

### 1.2 APNs Auth Key 生成（Token 认证）

1. 进入「Keys」→ 点击「+」创建新 Key
2. 填写 Key Name（如 `QiyunDriverAPNsKey`）
3. 勾选 **Apple Push Notifications service (APNs)**
4. 点击 Continue → Register，下载 `.p8` 文件（**仅可下载一次，请妥善保管**）
5. 记录 **Key ID**（10 位字符，如 `AB12CD34EF`）

> ⚠️ `.p8` 文件全局唯一，不可重新下载。丢失后需创建新 Key。

---

## 2. Xcode 工程配置

### 2.1 Capabilities 配置

1. 打开 `ios/Runner.xcworkspace`
2. 选择 **Runner** target → **Signing & Capabilities**
3. 点击 **+ Capability**，添加 **Push Notifications**
4. 额外添加 **Background Modes**，勾选 **Remote notifications**
5. 确认 Bundle ID 与开发者后台 App ID 完全一致

### 2.2 Entitlements

**开发环境** — `ios/Runner/Runner.entitlements`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>aps-environment</key>
	<string>development</string>
	<key>com.apple.developer.aps-environment</key>
	<string>development</string>
</dict>
</plist>
```

**生产环境** — `ios/Runner/RunnerProduction.entitlements`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>aps-environment</key>
	<string>production</string>
	<key>com.apple.developer.aps-environment</key>
	<string>production</string>
</dict>
</plist>
```

> 💡 `aps-environment` 为旧 key 名，`com.apple.developer.aps-environment` 为现代 key 名，两者共存确保兼容性。

**Xcode Build Settings 配置（`project.pbxproj`）：**

| 配置    | CODE_SIGN_ENTITLEMENTS                 |
| ------- | -------------------------------------- |
| Debug   | `Runner/Runner.entitlements`           |
| Release | `Runner/RunnerProduction.entitlements` |
| Profile | `Runner/RunnerProduction.entitlements` |

### 2.3 AppDelegate.swift

文件：`ios/Runner/AppDelegate.swift`

```swift
import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // 注册远程通知（Token 认证必须：确保 APNs device token 回调触发）
    if #available(iOS 10.0, *) {
      UNUserNotificationCenter.current().delegate = self as? UNUserNotificationCenterDelegate
    }
    application.registerForRemoteNotifications()

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }

  // MARK: - APNs Token 转发（JPush Token 认证依赖此回调）

  /// APNs 注册成功 → 转发 device token 给 JPush SDK
  override func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
  ) {
    super.application(application, didRegisterForRemoteNotificationsWithDeviceToken: deviceToken)
  }

  /// APNs 注册失败
  override func application(
    _ application: UIApplication,
    didFailToRegisterForRemoteNotificationsWithError error: Error
  ) {
    super.application(application, didFailToRegisterForRemoteNotificationsWithError: error)
    print("[JPush] APNs 注册失败: \(error.localizedDescription)")
  }
}
```

### 2.4 Info.plist

文件：`ios/Runner/Info.plist`

```xml
<!-- 后台模式 -->
<key>UIBackgroundModes</key>
<array>
    <string>location</string>
    <string>fetch</string>
    <string>remote-notification</string>
</array>

<!-- 网络安全配置：允许 jpush.cn 域名 -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
    <key>NSExceptionDomains</key>
    <dict>
        <key>jpush.cn</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
            <key>NSIncludesSubdomains</key>
            <true/>
        </dict>
    </dict>
</dict>
```

---

## 3. Android 配置

### 3.1 AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.VIBRATE" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

### 3.2 build.gradle

文件：`android/app/build.gradle`

```gradle
android {
    defaultConfig {
        manifestPlaceholders = [
            JPUSH_PKGNAME: applicationId,
            JPUSH_APPKEY : "25209e0932051b4ff7538447",
            JPUSH_CHANNEL: "developer-default",
        ]
    }
}
```

### 3.3 Flutter 3.29+ 厂商通道白屏修复

文件：`android/app/src/main/kotlin/.../MainActivity.kt`

```kotlin
class MainActivity : FlutterActivity() {
    // 禁用 Flutter 自动 deep link 处理，避免厂商通道推送点击时
    // intent.data 被误当成 Flutter 路由导致打开 App 白屏（Flutter 3.29+）
    override fun shouldHandleDeeplinking(): Boolean {
        return false
    }
    ...
}
```

> ⚠️ 若项目使用了 Flutter 官方深链接功能，则需在推送点击回调中自行处理路由跳转。

---

## 4. 极光后台配置

### 4.1 创建应用

1. 登录 [极光推送控制台](https://www.jiguang.cn/)
2. 创建应用，填写应用名称和图标
3. 获取 **AppKey**（本项目使用：`25209e0932051b4ff7538447`）

### 4.2 iOS Token Authentication 配置

1. 进入应用设置 → **推送设置** → **iOS**
2. 认证方式选择 **Token Authentication**
3. 填写以下信息：

| 字段      | 值                        | 说明                       |
| --------- | ------------------------- | -------------------------- |
| Key ID    | （.p8 文件的 Key ID）     | 10 位字符，如 `AB12CD34EF` |
| Team ID   | `36B34GA3TG`              | Apple 开发者团队 ID        |
| Bundle ID | `com.transcendtech.qiyun` | App 的 Bundle Identifier   |

4. 上传 `.p8` Auth Key 文件
5. 点击保存

> 💡 Token Authentication 优势：一个 .p8 Key 通用所有 App（同 Team ID），无需按环境（Dev/Prod）分别配置，不会过期。

### 4.3 AppKey 配置

| 平台    | AppKey                     | 来源                              |
| ------- | -------------------------- | --------------------------------- |
| Android | `25209e0932051b4ff7538447` | `android_driver/app/build.gradle` |
| iOS     | `25209e0932051b4ff7538447` | `driver-master/PrefixHeader.pch`  |

> ⚠️ 各端使用同一个 AppKey

配置位置：`lib/core/constants/app_constants.dart`

```dart
  /// JPush AppKey（各端统一）
  static const String jpushKeyProd = '25209e0932051b4ff7538447';
```

---

## 5. Flutter 代码实现

### 5.1 依赖配置

```yaml
# pubspec.yaml
dependencies:
  jpush_flutter: ^3.5.5
```

### 5.2 工具类

文件：`lib/core/utils/jpush_util.dart`

```dart
class JPushUtil {
  static final JPushUtil instance = JPushUtil._();

  // ---- 初始化 ----
  Future<void> init()                              // 应用启动时调用，重复调用自动跳过

  // ---- Alias 管理 ----
  Future<bool> setAlias(String userId)             // 登录/注册成功后绑定（`-` → `_`）
  Future<bool> deleteAlias()                       // 退出登录/注销时解绑（6022 视为成功）
  Future<String?> getAlias()                       // 查询当前 alias

  // ---- Tags 管理 ----
  Future<bool> setTags(List<String> tags)          // 设置标签（覆盖写入）

  // ---- 通知 & 角标 ----
  Future<void> clearAllNotifications()             // 清除所有通知
  Future<void> setBadge(int badge)                 // 设置角标数字（iOS）
  Future<void> clearBadge()                        // 清除角标（= setBadge(0)）
  Future<bool> isNotificationEnabled()             // 检查通知权限
  void openNotificationSettings()                  // 跳转系统通知设置

  // ---- Registration ID ----
  Future<String?> getRegistrationID()              // 获取设备 RID

  // ---- 外部回调 ----
  void Function(Map<String, dynamic>)? onReceiveMessage     // 收到透传消息
  void Function(Map<String, dynamic>)? onOpenNotification   // 用户点击通知（自动清除角标）
}
```

> 💡 所有写操作（setAlias / deleteAlias / setTags / clearAllNotifications / setBadge）统一通过 `_safeCall` 捕获异常并返回 `bool`，生产环境不输出日志。

### 5.3 初始化时机

文件：`lib/global.dart`

```dart
static Future<void> init() async {
  ...
  // 并行初始化（环境变量 + 本地存储预热）
  await Future.wait([
    AppConfig.init(),
    SpUtil.init(),
    JPushUtil.instance.init()  // JPush 初始化
  ]);
  ...
}
```

### 5.4 登录设置 Alias

文件：`lib/providers/auth_provider.dart`

```dart
Future<void> login({...}) async {
  ...
  // 设置 JPush alias（对齐 Android LoginActivity.setAlias）
  if (userId.isNotEmpty) {
    JPushUtil.instance.setAlias(userId);
  }
}
```

### 5.5 退出删除 Alias

文件：`lib/providers/auth_provider.dart`

```dart
Future<void> logout() async {
  ...
  // 删除 JPush alias（对齐 Android LoginActivity.deleteAlias）
  JPushUtil.instance.deleteAlias();
  JPushUtil.instance.clearAllNotifications();
  ...
}
```

---

## 6. 推送回调

### 6.1 消息接收

```dart
JPushUtil.instance.onReceiveMessage = (message) {
  // 处理透传消息（非通知，应用内自定义数据）
};
```

### 6.2 通知点击

```dart
JPushUtil.instance.onOpenNotification = (notification) {
  // 处理通知点击跳转
};
```

> ⚠️ `onOpenNotification` 回调内部**自动调用 `clearBadge()` 清除角标**，无需手动处理。

---

## 7. Alias 规则

对齐原生实现：

| 操作      | Alias 值                      | 返回值    | 说明                                            |
| --------- | ----------------------------- | --------- | ----------------------------------------------- |
| 登录/注册 | `userId.replaceAll('-', '_')` | `bool`    | 成功 `true`，userId 为空返回 `false`            |
| 退出登录  | 删除 alias                    | `bool`    | 成功 `true`；错误码 6022（不存在）也返回 `true` |
| 注销账号  | 删除 alias                    | `bool`    | 同上                                            |
| 查询      | `getAlias()`                  | `String?` | 当前 alias 或 `null`                            |

---

## 8. 调试命令

```dart
// 获取 RegistrationID
final rid = await JPushUtil.instance.getRegistrationID();

// 检查通知权限
final enabled = await JPushUtil.instance.isNotificationEnabled();

// 跳转通知设置
JPushUtil.instance.openNotificationSettings();
```

---

## 9. 常见问题排查

| 问题                         | 可能原因                        | 解决方案                                       |
| ---------------------------- | ------------------------------- | ---------------------------------------------- |
| iOS 收不到推送               | Token Auth 未配置或 Key ID 错误 | 极光后台检查 Key ID / Team ID / Bundle ID      |
| iOS 真机收不到               | 未申请通知权限                  | 调用 `applyPushAuthority()`                    |
| iOS device token 为空        | AppDelegate 未注册远程通知      | 确认 `registerForRemoteNotifications()` 已调用 |
| Android 厂商通道白屏         | Flutter 3.29+ 深链接冲突        | MainActivity 重写 `shouldHandleDeeplinking()`  |
| Alias 设置失败               | userId 为空                     | 检查登录流程是否正确传入 userId                |
| deleteAlias 报 6022          | alias 不存在                    | 正常现象，已视为成功处理                       |
| iOS 角标不减少               | 未在通知点击时清除              | `onOpenNotification` 已自动调用 `clearBadge()` |
| RegistrationID 为空          | SDK 未初始化完成                | 确保 `init()` 完成后再获取                     |
| 推送到达率低                 | 厂商通道未配置                  | 极光后台配置华为/小米/OPPO/vivo 通道           |
| Token Auth vs 证书 Auth 混淆 | 旧 .p12 证书仍上传              | 极光后台删除旧证书，仅保留 Token Auth          |

---

## 10. 注意事项

1. **iOS 真机测试**：必须使用真机，模拟器不支持推送
2. **Token Auth 优势**：一个 .p8 Key 通用所有 App（同 Team ID），无需按环境分别配置，不会过期
3. **AppKey 一致性**：Android 和 iOS 使用同一个 AppKey
4. **Alias 唯一性**：每个用户对应一个 alias，新登录会覆盖旧 alias
5. **Flutter 3.29+**：需在 MainActivity 中重写 `shouldHandleDeeplinking()` 返回 `false`
6. **`.p8` 文件安全**：仅可下载一次，丢失需创建新 Key；勿提交到公开仓库

---

## 11. 文件清单

| 文件                                              | 说明                   |
| ------------------------------------------------- | ---------------------- |
| `lib/core/utils/jpush_util.dart`                  | JPush 工具类           |
| `lib/core/constants/app_constants.dart`           | AppKey 配置            |
| `lib/global.dart`                                 | 初始化调用             |
| `lib/providers/auth_provider.dart`                | 登录/退出调用          |
| `ios/Runner/AppDelegate.swift`                    | APNs token 注册与转发  |
| `ios/Runner/Info.plist`                           | iOS 权限与后台模式配置 |
| `ios/Runner/Runner.entitlements`                  | 开发环境推送权限       |
| `ios/Runner/RunnerProduction.entitlements`        | 生产环境推送权限       |
| `ios/Runner.xcodeproj/project.pbxproj`            | Xcode 项目配置         |
| `android/app/src/main/kotlin/.../MainActivity.kt` | Android 深链接修复     |
| `android/app/build.gradle`                        | Android JPush 配置     |
