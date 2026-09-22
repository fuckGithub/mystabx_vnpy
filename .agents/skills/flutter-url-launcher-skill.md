---
name: flutter-url-launcher-best-practices
description: Use when FastapiAdmin Flutter 移动端使用 url_launcher 打开链接/拨号/地图导航，出现 canLaunchUrl+launchUrl 反模式，或需要配置 iOS LSApplicationQueriesSchemes / Android <queries> 平台白名单
---

# Flutter url_launcher 最佳实践

> 适用项目：fastapiadmin_mobile（FastapiAdmin Flutter 移动端）

## Overview

url_launcher 使用有 2 个常见坑：`canLaunchUrl` 反模式（TOCTOU 竞态 + iOS 误判）、平台白名单未配置导致第三方 scheme 解析失败。

> ⚠️ 本项目目前**未引入** `url_launcher` 依赖；需要打开 `tel:` / `geo:` / `http(s)` 等链接时，先 `flutter pub add url_launcher`，再按本 skill 落地。

## When to Use

- 打开 `tel:` / `geo:` / `http(s)` / 第三方地图（高德 `amapuri://`、百度 `baidumap://`）等链接
- 页面散落 `if (await canLaunchUrl(uri)) { await launchUrl(uri); }` 组合
- 需要新增一个能打开的 URL scheme，但 Android 11+/iOS 9+ 上打不开

## Core Pattern

**反模式（禁止）**：

```dart
if (await canLaunchUrl(uri)) {          // ❌ 竞态 + iOS 未配白名单时误判 false
  await launchUrl(uri);
}
```

**正确（官方推荐）**：直接 `launchUrl` + try/catch，返回是否成功。统一封装到工具类：

```dart
class LaunchUtil {
  static Future<bool> open(
    Uri uri, {
    LaunchMode mode = LaunchMode.externalApplication,
  }) async {
    try {
      return await launchUrl(uri, mode: mode);
    } catch (_) {
      return false;
    }
  }
}
```

调用：`final ok = await LaunchUtil.open(Uri.parse('tel:$phone'));` 失败时按 ok 分支提示/回退。

## 平台白名单（Quick Reference）

只影响 `canLaunchUrl`（Android `resolveActivity` / iOS `canOpenURL`），**不影响 `launchUrl`**。但第三方自定义 scheme 建议声明，Android 11+ 部分系统会拦截 `launchUrl` 解析。

| 平台        | 配置位置                                               | 内容                                                                  |
| ----------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| Android 11+ | `android/app/src/main/AndroidManifest.xml` `<queries>` | `<intent><action VIEW/><data scheme="xxx"/></intent>` 每条一个 scheme |
| iOS 9+      | `ios/Runner/Info.plist` `LSApplicationQueriesSchemes`  | `<string>xxx</string>` 数组                                           |

按需声明 scheme（如 `tel`、`mailto`、`geo`、`amapuri`、`baidumap` 等）。

## Common Mistakes

1. **用 `canLaunchUrl` 做前置判断** → 竞态；iOS 未配 `LSApplicationQueriesSchemes` 时对 `tel:` 误返回 false 静默失败。改 `launchUrl`+catch。
2. **只配一个平台白名单** → Android/iOS 行为不一致。两处都要配。
3. **地图导航 fallback 依赖 canLaunchUrl** → 高德/百度未装时无法区分"未装"与"权限未配"。用 `launchUrl` 返回值做 fallback 判断。

## 验证

- 修改后跑 `flutter analyze`（无 error）+ `flutter build apk --debug`（成功）
- 改 plist/xml 后做语法校验（`plistlib` / `ElementTree` 解析）
