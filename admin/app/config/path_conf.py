from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
"""项目根目录"""

ALEMBIC_VERSION_DIR = BASE_DIR / "app" / "alembic" / "versions"
"""alembic 迁移文件存放路径"""

LOG_DIR = BASE_DIR / "logs"
"""日志文件路径"""

STATIC_DIR = BASE_DIR / "static"
"""静态资源根目录"""

UPLOAD_DIR = STATIC_DIR / "upload"
"""上传文件目录"""

DOWNLOAD_DIR = STATIC_DIR / "download"
"""下载文件目录"""

ENV_DIR = BASE_DIR / "env"
"""环境配置目录"""


TEMPLATE_DIR: Path = BASE_DIR / "app" / "plugin" / "module_generator" / "gencode" / "templates"
"""模版文件配置"""

BANNER_FILE = BASE_DIR / "banner.txt"
"""banner.txt 文件路径"""
