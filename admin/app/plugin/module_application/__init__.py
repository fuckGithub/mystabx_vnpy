"""application 插件包：门户应用管理与插件清单查询。

本包内的 ``**/controller.py`` 由 ``app/core/discover.py`` 的目录扫描自动挂载，
容器前缀由目录名推导（``module_application`` → ``/application``）；``portal`` 子前缀
由 controller 内 ``APIRouter(prefix="/portal")`` 提供。

注意：本包**不得**再聚合 ``APIRouter`` 并导出（历史上曾导出 ``application_router``）——
目录扫描已挂载全部顶层 router，显式聚合会让同一批路由被挂载两次，产生重复路由。
"""
