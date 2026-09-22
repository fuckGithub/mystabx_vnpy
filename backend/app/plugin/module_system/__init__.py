"""system 插件包（最小可运行集成员）。

**不得在本文件聚合子路由**：本包的路由由 ``app/core/discover.py`` 目录扫描挂载
（``module_system/**/controller.py`` → 容器前缀 ``/system``）。若在此再写
``system_router`` 聚合，会与目录扫描**重复挂载同一批路由**（同一「方法+路径」出现两次）。

模型由 ``plugin.py::setup()`` 声明，内核槽位由 ``plugin.py::start()`` 注入。
"""

from __future__ import annotations
