# module_system/notice — 公告通知

## 模块定位

系统公告（`sys_notice`）的增删改查、启用停用、导出，以及面向已登录用户的可用公告列表。
边界：只维护公告数据，不含站内推送/消息中心。

## 入口

| 入口类型  | 路径                            | 说明                                  |
| --------- | ------------------------------- | ------------------------------------- |
| HTTP 路由 | `controller.py` → `NoticeRouter` | 容器前缀 `/system/notice`，共 8 条    |
| ORM 模型  | `model.py`                      | `sys_notice`                          |
| 种子数据  | 无                              | 不写入公告                            |

路由（8 条）：`list`、`create`、`update/{id}`、`delete`、`detail/{id}`、`export`、
`available`、`available/setting`。

## 依赖

- 内核槽位：无。
- 其它插件：`system`（无跨子模块强依赖）。

## 删除影响

删除本子模块后：

- `/system/notice/*` 8 条接口消失，公告功能不可用（前端公告页/首页公告接口 404）。
- `sys_notice` 不再自动创建；已存在的公告行与菜单行保留。
