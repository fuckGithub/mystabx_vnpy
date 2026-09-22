"""common 插件包：文件管理与健康检查。

本包内的 ``**/controller.py`` 由 ``app/core/discover.py`` 的目录扫描自动挂载，
容器前缀由目录名推导（``module_common`` → ``/common``）。

注意：本包**不得**再聚合 ``APIRouter`` 并导出（历史上曾导出 ``common_router``）——
目录扫描已挂载全部顶层 router，显式聚合会让同一批路由被挂载两次，产生重复路由。
"""
