# module_common/file — 文件上传下载

## 模块定位

通用文件上传与下载（`POST /common/file/upload`、`POST /common/file/download`）。
边界：只处理「随请求收发的文件字节」；磁盘目录的浏览/管理在 `module_monitor/resource`。

## 入口

| 入口类型  | 路径                           | 说明                                     |
| --------- | ------------------------------ | ---------------------------------------- |
| HTTP 路由 | `controller.py` → `FileRouter` | 容器前缀 `/common/file`，共 2 条         |
| ORM 模型  | 无                             | 无 `model.py`                            |
| 业务实现  | `service.py`、`schema.py`      | 落盘目录来自 `app/config` 的静态目录配置 |

路由（2 条）：`POST /common/file/upload`、`POST /common/file/download`。

## 依赖

- 内核槽位：无。
- 其它插件：无。

## 删除影响

删除本子模块后：

- `/common/file/*` 2 条接口消失；其它模块（如 `module_system/user` 头像上传）若复用本
  子模块的 service 将无法导入。
- 无数据表、无种子受影响；已上传的磁盘文件保留。
