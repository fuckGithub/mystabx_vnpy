# module_system/dict — 字典管理

## 模块定位

字典类型（`sys_dict_type`）与字典数据（`sys_dict_data`）两级维护，支持下拉选项查询与导出。
边界：只维护这两张表；字典到 Redis 的预热由父插件 `plugin.py::start()` 调用本子模块
`service.py::DictDataService.init_dict_service` 完成。

## 入口

| 入口类型     | 路径                            | 说明                                                     |
| ------------ | ------------------------------- | -------------------------------------------------------- |
| HTTP 路由    | `controller.py` → `DictRouter`  | 容器前缀 `/system/dict`，共 16 条（type 7 条 + data 9 条） |
| ORM 模型     | `model.py`                      | `sys_dict_type`、`sys_dict_data`                          |
| Redis 预热   | `service.py::DictDataService`   | `init_dict_service(redis)` 由父插件 `start()` 调用        |
| 种子数据     | 由父插件声明                    | `sys_dict_type`(dict_type)、`sys_dict_data`(dict_type+dict_value) |

路由（16 条）：`/system/dict/type/{list,create,update/{id},delete,detail/{id},export,optionselect}`、
`/system/dict/data/{list,create,update/{id},delete,detail/{id},export,info/{dict_type},available/setting}`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（无跨子模块强依赖，仅共用父插件的 DB 会话）。

## 删除影响

删除本子模块后：

- `/system/dict/*` 16 条接口消失，字典维护与下拉选项接口不可用。
- `sys_dict_type`、`sys_dict_data` 不再自动创建，两批字典种子不再写入。
- Redis 字典缓存不再预热；依赖字典缓存的业务读取将拿不到数据（键缺失）。
