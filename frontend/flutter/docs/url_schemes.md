# URL Schemes 文档

> 最后更新：2026-09-03
>
> 本文档记录启运网司机端 App 所有 URL scheme 的声明、使用场景与平台差异。
> 修改 scheme 前必读此文档，确保三处同步：代码 → Info.plist → AndroidManifest.xml。

## 一、总览

| Scheme          | 用途                  | iOS Info.plist | Android Manifest | 代码位置                             |
| --------------- | --------------------- | :------------: | :--------------: | ------------------------------------ |
| `tel`           | 拨打电话              |       ✅       |        ✅        | `phone_util.dart` / 6 处页面         |
| `iosamap`       | 高德地图（iOS）       |       ✅       |        —         | `app_navigation_sheet.dart`          |
| `androidamap`   | 高德地图（Android）   |       —        |        ✅        | `app_navigation_sheet.dart`          |
| `amapuri`       | 高德地图（鸿蒙 NEXT） |       —        |        —         | `app_navigation_sheet.dart`          |
| `baidumap`      | 百度地图              |       ✅       |        ✅        | `app_navigation_sheet.dart`          |
| `qqmap`         | 腾讯地图              |       ✅       |        ✅        | `app_navigation_sheet.dart`          |
| `map`           | 花瓣地图（鸿蒙 NEXT） |       —        |        —         | `app_navigation_sheet.dart` fallback |
| `geo`           | 系统地图（Android）   |       ✅       |        ✅        | `app_navigation_sheet.dart` fallback |
| `https`         | Apple Maps（iOS）     |     不需要     |      不需要      | `app_navigation_sheet.dart` fallback |
| `mailto`        | 发送邮件              |       ✅       |        ✅        | 预声明（WebView 场景）               |
| `sms` / `smsto` | 发送短信              |       ✅       |        ✅        | 预声明                               |
| `mms` / `mmsto` | 发送彩信              |       ✅       |        ✅        | 预声明                               |
| `whatsapp`      | WhatsApp              |       ✅       |        ✅        | 预声明                               |
| `weixin`        | 微信                  |       ✅       |        ✅        | 预声明                               |
| `alipays`       | 支付宝                |       ✅       |        ✅        | 预声明                               |
| `facetime`      | FaceTime 视频通话     |       ✅       |        —         | 预声明（WebView 场景）               |
| `market`        | Google Play           |       —        |        ✅        | WebView 内跳转                       |
| `intent`        | Android Intent URI    |       —        |        ✅        | WebView 内跳转                       |

## 二、地图导航 Scheme 详解

### 2.1 高德地图

**平台差异（关键）：** iOS、Android、鸿蒙 NEXT 使用不同的 scheme，不可混用。

| 平台      | Scheme           | 说明                                                                                                    |
| --------- | ---------------- | ------------------------------------------------------------------------------------------------------- |
| iOS       | `iosamap://`     | 高德 iOS 版注册的唯一 scheme                                                                            |
| Android   | `androidamap://` | 高德 Android 版注册的 scheme                                                                            |
| 鸿蒙 NEXT | `amapuri://`     | 高德鸿蒙版注册的 scheme（[官方文档](https://lbs.amap.com/api/amap-mobile/guide/harmony-os/route-next)） |

> ⚠️ `amapuri://` 仅用于鸿蒙 NEXT（`Platform.operatingSystem == 'ohos'`），iOS 未注册此 scheme。
> 普通鸿蒙（HarmonyOS 4.x 及以下）基于 AOSP，`Platform.isAndroid == true`，使用 `androidamap://`。

**三平台统一精简格式（2026-09-03 简化）：**

```
{scheme}://route/plan?dlat={lat}&dlon={lng}&dname={目的地}&t=0
```

- `{scheme}` = `iosamap` / `androidamap` / `amapuri`（按平台选择）
- `dlat`/`dlon` = 目的坐标（GCJ-02 坐标系），无坐标时传 `0`
- `dname` = 目的地名称（原始中文，`Uri.parse` 自动编码）
- `t=0` = 驾车导航

> 已去掉 `sid`/`did`（纯展示用）、`sname`（起点名）、`dev`（坐标类型）、`sourceApplication`（统计用）等非必需参数。
> `Uri.parse` 自动处理中文编码，无需手动 `Uri.encodeComponent`。

### 2.2 百度地图

各平台统一使用原生 scheme（鸿蒙 NEXT 装了百度地图同样可拉起，失败回退系统地图）：

```
// 有坐标（BD-09 坐标系，需从 GCJ-02 转换）
baidumap://map/direction?destination={bdLat},{bdLng}&destination_name={目的地}&mode=driving
// 无坐标
baidumap://map/direction?destination_name={目的地}&mode=driving
```

- `destination` = BD-09 坐标（⚠️ 百度使用 BD-09 坐标系，需 `CoordUtil.gcj02ToBd09()` 转换，直接传 GCJ-02 偏差 300~500m）
- `destination_name` = 目的地名称
- `mode=driving` = 驾车模式
- 无坐标时省略 `destination`，仅传地址名搜索

### 2.3 腾讯地图

各平台统一使用原生 scheme（鸿蒙 NEXT 装了腾讯地图同样可拉起，失败回退系统地图）：

```
// 有坐标（GCJ-02 坐标系，与系统一致，无需转换）
qqmap://map/routeplan?type=drive&to={目的地}&tocoord={lat},{lng}
// 无坐标（省略 tocoord，避免传 0,0）
qqmap://map/routeplan?type=drive&to={目的地}
```

- `type=drive` = 驾车模式
- `to` = 目的地名称
- `tocoord` = GCJ-02 坐标（有坐标时传入，无坐标时省略）

### 2.4 系统地图

**iOS — Apple Maps：**

```
https://maps.apple.com/?ll={lat},{lng}&q={地址}     // 有坐标
https://maps.apple.com/?q={地址}                     // 无坐标
```

> ⚠️ iOS 不支持 `geo:` scheme（RFC 5870），必须用 `maps.apple.com`。

**Android — geo:（RFC 5870）：**

```
geo:{lat},{lng}?q={lat},{lng}({地址})    // 有坐标
geo:0,0?q={地址}                          // 无坐标
```

**鸿蒙 NEXT — 华为花瓣地图原生 scheme（`map://`）：**

```
map://navigation?lat={lat}&lng={lng}&name={地址}    // 有坐标
map://search?keyword={地址}                          // 无坐标
```

> 鸿蒙 NEXT 无 `geo:` scheme（无 Google Maps），用华为花瓣地图原生 `map://`。花瓣地图为鸿蒙系统内置地图，几乎必然已安装；未安装则 `launchUrl` 失败 → Toast。
> 注意：`map://` 无需在 Info.plist/AndroidManifest 声明（鸿蒙不读这两个文件），仅鸿蒙工程 `module.json5` 需要 `uris` 声明（接入鸿蒙工程时处理）。

### 2.5 回退逻辑

```
用户点击高德/百度/腾讯 → 打开成功 → 结束
                      → 打开失败 → 回退系统地图 → 成功 → 结束
                                          → 失败 → Toast "无法打开地图导航"
用户点击系统地图 → 打开成功 → 结束
                → 打开失败 → Toast "无法打开地图导航"（不再重复回退）
```

### 2.6 可用性预检测

弹出导航 sheet 前，通过 `canLaunchUrl` + **完整 URI**（非裸 scheme）预检测已安装的地图 App：

```dart
final checks = await Future.wait([
  canLaunchUrl(Uri.parse('$amapScheme://route/plan/?dname=test')),  // 高德
  canLaunchUrl(Uri.parse('baidumap://map/direction')),               // 百度
  canLaunchUrl(Uri.parse('qqmap://map/routeplan?type=drive')),       // 腾讯
]);
```

- 只显示已安装的地图选项
- 系统地图始终保留（兜底）
- **全部返回 false 时**（`canLaunchUrl` 在部分设备仍不可靠）：兜底显示所有选项
- `canLaunchUrl` 可靠性前提：scheme 已在 Info.plist `LSApplicationQueriesSchemes` / AndroidManifest `<queries>` 声明

## 三、电话拨打 Scheme

```dart
// 标准格式
LaunchUtil.open(Uri.parse('tel:$phone'));

// Uri 构造格式
LaunchUtil.open(Uri(scheme: 'tel', path: phone));
```

- 使用位置：`phone_util.dart`、`cargo_detail_screen.dart`、`bank_branch_query_screen.dart`、`feedback_screen.dart`、`help_screen.dart`、`customer_detail_screen.dart`
- `LaunchUtil.open` 直接调用 `launchUrl`，不依赖 `canLaunchUrl`，无需额外声明即可工作

## 四、声明文件位置

| 文件                                                     | 作用                                                           |
| -------------------------------------------------------- | -------------------------------------------------------------- |
| `ios/Runner/Info.plist` → `LSApplicationQueriesSchemes`  | iOS 9+ 要求声明才能用 `canLaunchUrl` 检测第三方 App            |
| `android/app/src/main/AndroidManifest.xml` → `<queries>` | Android 11+ (API 30+) 包可见性要求                             |
| 鸿蒙 `ohos/src/main/module.json5` → `module.uris`        | 鸿蒙 NEXT 检测/拉起第三方 App 的 scheme 声明（接入鸿蒙工程时） |

## 五、修改 Checklist

新增或修改 scheme 时，**平台声明同步**：

| 平台      | 声明位置                                         |
| --------- | ------------------------------------------------ |
| iOS       | `Info.plist` → `LSApplicationQueriesSchemes`     |
| Android   | `AndroidManifest.xml` → `<queries>`              |
| 鸿蒙 NEXT | `module.json5` → `module.uris`（接入鸿蒙工程时） |

**三方地图 scheme 三平台对照（实测 2026-09-03）：**

| 地图 | iOS                      | Android          | 鸿蒙 NEXT                   | 坐标系          |
| ---- | ------------------------ | ---------------- | --------------------------- | --------------- |
| 高德 | `iosamap://`             | `androidamap://` | `amapuri://`                | GCJ-02（直传）  |
| 腾讯 | `qqmap://`               | `qqmap://`       | `qqmap://`（装了可拉起）    | GCJ-02（直传）  |
| 百度 | `baidumap://`            | `baidumap://`    | `baidumap://`（装了可拉起） | BD-09（需转换） |
| 系统地图 | `https://maps.apple.com` | `geo:`           | `map://`（花瓣地图）        | WGS84（需转换） |

验证命令：

```bash
# 检查 Info.plist 中的 scheme 声明
grep -A 20 'LSApplicationQueriesSchemes' ios/Runner/Info.plist

# 检查 AndroidManifest 中的 scheme 声明
grep 'android:scheme' android/app/src/main/AndroidManifest.xml

# 静态分析
flutter analyze
```

## 六、坐标系与转换

中国地图三大坐标系：

| 坐标系 | 使用者            | 说明                     |
| ------ | ----------------- | ------------------------ |
| WGS84  | GPS / `geo:` 协议 | 国际标准，原始 GPS 坐标  |
| GCJ-02 | 高德 / 腾讯       | 国测局加密（火星坐标）   |
| BD-09  | 百度              | 在 GCJ-02 基础上二次加密 |

**本项目系统坐标为 GCJ-02**（`Geolocator` 返回的 WGS84 已自动转换为 GCJ-02）。

转换工具：坐标转换工具类（`CoordUtil` 或类似）提供以下方法：

| 方法           | 方向           | 用途                   |
| -------------- | -------------- | ---------------------- |
| `gcj02ToWgs84` | GCJ-02 → WGS84 | 鸿蒙 `geo:` / `map://` |
| `wgs84ToGcj02` | WGS84 → GCJ-02 | GPS 定位后转换         |
| `gcj02ToBd09`  | GCJ-02 → BD-09 | 百度地图               |
| `bd09ToGcj02`  | BD-09 → GCJ-02 | 百度坐标逆转换         |

**各地图坐标系对照：**

| 地图     | 坐标系 | 系统 GCJ-02 是否需要转换 |
| -------- | ------ | ------------------------ |
| 高德     | GCJ-02 | ❌ 不需要                |
| 腾讯     | GCJ-02 | ❌ 不需要                |
| 百度     | BD-09  | ⚠️ 需要 GCJ-02→BD-09     |
| 系统地图 | WGS84  | ⚠️ 需要 GCJ-02→WGS84     |
