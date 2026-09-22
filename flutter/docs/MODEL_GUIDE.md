# Flutter 模型解析规范

> 基于 `json_serializable` 的模型代码生成方案。

---

## 一、依赖配置

```yaml
# pubspec.yaml
dependencies:
  json_annotation: ^4.9.0

dev_dependencies:
  build_runner: ^2.4.12
  json_serializable: ^6.8.0
```

## 二、模型定义规范

### 2.1 基本结构

```dart
import 'package:json_annotation/json_annotation.dart';

part 'user.g.dart';          // ← 文件名.g.dart，由 build_runner 生成

@JsonSerializable()
class User {
  final int id;
  final String name;

  User({required this.id, required this.name});

  // 以下两个方法由 build_runner 自动生成
  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
  Map<String, dynamic> toJson() => _$UserToJson(this);
}
```

### 2.2 字段别名

当 JSON key 与 Dart 字段名不一致时：

```dart
@JsonSerializable()
class UserProfile {
  @JsonKey(name: 'is_superuser')
  bool? isSuperuser;

  @JsonKey(name: 'mobile_button_code_list')
  List<String>? mobileButtonCodeList;
}
```

### 2.3 忽略字段

```dart
@JsonSerializable()
class User {
  @JsonKey(includeFromJson: false, includeToJson: false)
  String? tempField;
}
```

## 三、代码生成

```bash
# 首次生成
dart run build_runner build

# 持续监听（自动重新生成）
dart run build_runner watch

# 强制覆盖冲突
dart run build_runner build --delete-conflicting-outputs
```

## 四、API 调用模式

### 4.1 数据流

```
后端响应: { "code": 0, "msg": "成功", "data": { ... } }
                          │
     RequestInterceptors.onResponse  ← 统一校验 code
                          │
          ┌ code != 0 ──→ EasyLoading.showError(msg) + reject
          │
          └ code == 0 ──→ response.data = body['data']  ← 解包
                          │
         FactoryHttpUtil.getApi<T>(fromJson: T.fromJson)  ← 泛型解析
                          │
                        T 实例
```

### 4.2 API 层示例

```dart
class UserApi {
  /// 获取用户信息 — 直接传入 UserProfile.fromJson 引用
  static Future<UserProfile> profile() async {
    return FactoryHttpUtil().getApi<UserProfile>(
      '/auth/b/getLoginUser',
      fromJson: UserProfile.fromJson,
    );
  }

  /// 登录 — 返回 access_token
  static Future<String> login({
    required String account,
    required String password,
  }) async {
    final data = await FactoryHttpUtil().postApi<Map<String, dynamic>>(
      '/auth/b/doLogin',
      data: {'account': account, 'password': password},
      fromJson: (d) => d,
    );
    return data['access_token'] as String;
  }
}
```

### 4.3 泛型签名说明

```dart
Future<T> getApi<T>(
  String url, {
  required T Function(Map<String, dynamic>) fromJson,
}) async;
```

- `T` — 目标类型，由 json_serializable 模型提供
- `fromJson` — 模型类的 `fromJson` 工厂构造函数引用（如 `UserProfile.fromJson`）
- 返回值 — 已反序列化的类型安全实例

- `onResponse`: 校验 `code` 字段，非零时 toast 错误并 reject；成功时解包 `data`
- `onError`: 仅处理网络层异常（超时/断网），业务错误已在 `onResponse` 中处理

### API 层示例

```dart
class UserApi {
  /// 获取用户信息 — 返回类型安全的 UserProfile
  static Future<UserProfile> profile() async {
    return FactoryHttpUtil().getApi<UserProfile>(
      '/auth/b/getLoginUser',
      fromJsonT: (d) => UserProfile.fromJson(d as Map<String, dynamic>),
    );
  }
}
```

## 五、现有模型清单

| 模型            | 文件                       | 状态                                         |
| --------------- | -------------------------- | -------------------------------------------- |
| `UserProfile`   | `models/user_profile.dart` | ✅ json_serializable + `user_profile.g.dart` |
| `LoginResponse` | 已废弃                     | 拦截器统一处理                               |

### 新增模型步骤

1. 在 `lib/services/models/` 下创建 `xxx.dart`
2. 添加 `@JsonSerializable()` 注解和 `part 'xxx.g.dart'`
3. 实现 `fromJson` / `toJson` 委托给 `_$XxxFromJson` / `_$XxxToJson`
4. 运行 `dart run build_runner build` 生成 `.g.dart`
5. 在 `common/api/` 中定义对应的 API 方法
