# module_common/health — 健康检查

## 模块定位

存活探针（liveness）与就绪探针（readiness）。
边界：只做探针判断，不缓存、不写库；就绪探针按需 ping 数据库（`SELECT 1`）与
`app.state.redis`。

## 入口

| 入口类型  | 路径                             | 说明                                    |
| --------- | -------------------------------- | --------------------------------------- |
| HTTP 路由 | `controller.py` → `HealthRouter` | 容器前缀 `/common/health`，共 2 条      |
| ORM 模型  | 无                               | 无 `model.py`（只执行 `SELECT 1` 探活） |

路由（2 条）：

- `GET /common/health/` — 存活探针：进程在即 200，不探测外部依赖（供 K8s livenessProbe）。
- `GET /common/health/ready/` — 就绪探针：探测数据库与 Redis，任一失败返回 503
  （供 K8s readinessProbe 摘除流量）。

## 依赖

- 内核槽位：无。直接读 `settings.SQL_DB_ENABLE`/`settings.REDIS_ENABLE` 与
  `request.app.state.redis`。
- 其它插件：无。

## 删除影响

删除本子模块后：

- `/common/health/*` 2 条接口消失；容器编排的 liveness/readiness 探针会收到 404，
  进而可能触发重启或摘流（运维面影响，非功能面）。
- 无数据表、无种子受影响。
