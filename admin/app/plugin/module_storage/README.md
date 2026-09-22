# module_storage — 存储管理

## 模块定位

存储节点管理、文件传输任务、存储工作流编排。
提供统一的存储资源抽象层，支持多存储后端的接入与管理。

## 子模块

| 子模块     | 说明                         |
| ---------- | ---------------------------- |
| `browse`   | 存储浏览（目录/文件列表）    |
| `node`     | 存储节点管理（接入/配置）    |
| `transfer` | 传输任务（上传/下载/同步）   |
| `workflow` | 存储工作流（编排/调度）      |

## 入口

| 入口类型 | 路径        | 说明                                         |
| -------- | ----------- | -------------------------------------------- |
| 插件入口 | `plugin.py` | `class Plugin(PluginBase)`：声明 3 个模型模块 |

## 依赖

- 内核槽位：无消费、无提供。
- 其它插件：无（`plugin.toml` 未声明 `depends`）。
- 第三方：阿里云 OSS（`oss2`，经全局 `OSS_*` 环境变量；`OSS_READY` 时启动会种子节点「Aliyun OSS」）。

## OSS 对接

开启 `OSS_ENABLE=true` 并配置 `OSS_ACCESS_KEY` / `OSS_SECRET_KEY` / `OSS_BUCKET_NAME` 后：

- 「文件管理」（`module_monitor/resource`）浏览/上传/下载走 OSS；
- 本插件默认种子节点 `type=oss`，`config.use_settings=true`，浏览接口 `/storage/browse/list` 列举桶内 `OSS_PREFIX` 下对象。

## 删除影响

删除本目录后：

- `/storage/*` 下全部接口消失（浏览/节点/传输/工作流）。
- `storage_node`、`storage_transfer`、`storage_workflow` 表不再自动创建。
- 已配置的存储节点、传输任务、工作流定义将无法通过接口管理。

## ORM 模型

模型路径声明：

- `node.model`（表 `storage_node`）
- `transfer.model`（表 `storage_transfer`）
- `workflow.model`（表 `storage_workflow`）
