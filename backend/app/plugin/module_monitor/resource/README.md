# module_monitor/resource — 静态资源目录管理

## 模块定位

静态资源目录（`settings.STATIC_ROOT` 下的 upload 等目录）的文件/目录管理：列表、删、改、复制、
移动、重命名、建目录、上传、下载、导出。
边界：只操作磁盘目录，不建表；是否启用由 `settings.STATIC_ENABLE` 决定。

## 入口

| 入口类型  | 路径                                            | 说明                                  |
| --------- | ----------------------------------------------- | ------------------------------------- |
| HTTP 路由 | `controller.py` → `ResourceRouter`              | 容器前缀 `/monitor/resource`，共 9 条 |
| ORM 模型  | 无                                              | 无 `model.py`                         |
| 配置依赖  | `settings.STATIC_ROOT`/`STATIC_URL`/`ROOT_PATH` | 目录根与对外 URL 前缀由配置决定       |

路由（9 条）：`GET /monitor/resource/list`、`GET /monitor/resource/download`、
`POST /monitor/resource/upload`、`POST /monitor/resource/create-dir`、
`POST /monitor/resource/move`、`POST /monitor/resource/copy`、
`POST /monitor/resource/rename`、`POST /monitor/resource/export`、
`DELETE /monitor/resource/delete`。

## 依赖

- 内核槽位：无。
- 其它插件：无。

## 删除影响

删除本子模块后：

- `/monitor/resource/*` 9 条接口消失：无法通过后台浏览/维护静态资源目录。
- 无数据表、无种子；磁盘上的文件与 `module_common/file` 的上传下载不受影响。
