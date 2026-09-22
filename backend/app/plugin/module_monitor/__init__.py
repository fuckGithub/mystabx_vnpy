"""monitor 插件包：在线用户、缓存、服务器与资源监控。

本包内的 ``**/controller.py`` 由 ``app/core/discover.py`` 的目录扫描自动挂载，
容器前缀由目录名推导（``module_monitor`` → ``/monitor``）；``cache`` / ``online``
/ ``resource`` / ``server`` 各自的子前缀由 controller 内 ``APIRouter(prefix=...)``
提供。

注意：本包**不得**再聚合 ``APIRouter`` 并导出（历史上曾导出 ``monitor_router``）——
目录扫描已挂载全部顶层 router，显式聚合会让同一批路由被挂载两次，产生重复路由。
"""
