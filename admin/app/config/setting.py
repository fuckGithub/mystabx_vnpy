import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.common.enums import EnvironmentEnum
from app.config.path_conf import BASE_DIR, ENV_DIR


class Settings(BaseSettings):
    """系统配置类"""

    model_config = SettingsConfigDict(
        env_file=[
            ENV_DIR / ".env",
            *([ENV_DIR / f".env.{os.getenv('ENVIRONMENT')}"] if os.getenv("ENVIRONMENT") else []),
        ],
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        env_parse_none_str="null",
    )

    # ================================================= #
    # ******************* 项目环境 ****************** #
    # ================================================= #
    # 注意：ENVIRONMENT 决定加载哪个 .env.{ENVIRONMENT} 文件，保留代码默认值作为引导
    ENVIRONMENT: EnvironmentEnum = EnvironmentEnum.DEV
    """应用运行环境（dev/prod），决定加载对应的 .env.{ENVIRONMENT} 文件"""

    # ================================================= #
    # ******************* 服务器配置 ****************** #
    # ================================================= #
    SERVER_HOST: str = "0.0.0.0"
    """服务器绑定地址"""
    SERVER_PORT: int = 18080
    """服务监听端口"""

    # ================================================= #
    # ******************* API文档配置 ****************** #
    # ================================================= #
    DEBUG: bool = True
    """调试模式开关"""
    TITLE: str = "🎉 Mystabx Admin 🎉 "
    """Swagger 文档标题"""
    VERSION: str = "0.1.0"
    """API 版本号"""
    DESCRIPTION: str = "该项目是一个基于python的web服务框架，基于fastapi和sqlalchemy实现。"
    """API 文档描述"""
    SUMMARY: str = "接口汇总"
    """API 文档概述"""
    DOCS_URL: str = "/docs"
    """Swagger UI 路径"""
    REDOC_URL: str = "/redoc"
    """ReDoc 路径"""
    LJDOC_URL: str = "/ljdoc"
    """LangJin UI 路径"""
    ROOT_PATH: str = "/api/v1"
    """API 路由前缀"""

    # ================================================= #
    # ******************** 日志级别 ******************** #
    # ================================================= #
    LOGGER_LEVEL: str = "DEBUG"
    """日志级别 (DEBUG/INFO/WARNING/ERROR)"""

    # ================================================= #
    # ******************** 跨域配置 ******************** #
    # ================================================= #
    CORS_ORIGIN_ENABLE: bool = False
    """是否启用跨域"""
    ALLOW_ORIGINS: list[str] = ["*"]
    """允许的跨域来源域名列表"""
    ALLOW_METHODS: list[str] = ["*"]
    """允许的 HTTP 方法"""
    ALLOW_HEADERS: list[str] = ["*"]
    """允许的请求头"""
    ALLOW_CREDENTIALS: bool = True
    """是否允许携带凭据 (cookie)"""
    CORS_EXPOSE_HEADERS: list[str] = ["X-Request-ID"]
    """暴露给客户端的响应头"""

    # ================================================= #
    # ******************* 登录认证配置 ****************** #
    # ================================================= #
    SECRET_KEY: str = "change-me-to-a-secure-random-key"
    """JWT 签名密钥"""
    ALGORITHM: str = "HS256"
    """JWT 加密算法 (如 HS256)"""
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 30
    """access_token 过期时间（秒）；直接用于 JWT exp 与 Redis EXPIRE（均按秒解释）"""
    REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 30
    """refresh_token 过期时间（秒）；直接用于 Redis EXPIRE（按秒解释）"""
    TOKEN_TYPE: str = "bearer"
    """Token 类型 (bearer)"""
    TOKEN_REQUEST_PATH_EXCLUDE: list[str] = [
        "/api/v1/system/auth/sm-public-key",
    ]
    """JWT/RBAC 白名单路由"""
    TOKEN_SLIDING_EXPIRE: bool = True
    """是否启用滑动过期（操作时自动续期）"""

    # 多租户
    TENANT_HOST_ENFORCE: bool = False
    """是否启用多租户子域名解析"""
    TENANT_HOST_BASE_DOMAIN: str = ""
    """多租户基础域名"""
    TENANT_HOST_IGNORE_PREFIXES: list[str] = ["www", "api", "admin"]
    """多租户忽略的前缀"""

    # ================================================= #
    # ******************** 数据库配置 ******************* #
    # ================================================= #
    SQL_DB_ENABLE: bool = True
    """是否启用数据库"""
    DATABASE_ECHO: bool | Literal["debug"] = False
    """是否打印 SQL 日志"""
    ECHO_POOL: bool | Literal["debug"] = False
    """是否打印连接池日志"""
    POOL_SIZE: int = 10
    """数据库连接池大小"""
    MAX_OVERFLOW: int = 20
    """最大溢出连接数"""
    POOL_TIMEOUT: int = 30
    """连接超时时间（秒）"""
    POOL_RECYCLE: int = 1800
    """连接回收时间（秒）"""
    POOL_USE_LIFO: bool = True
    """是否使用 LIFO 连接池策略"""
    POOL_PRE_PING: bool = True
    """是否启用连接预检"""
    FUTURE: bool = True
    """是否使用 SQLAlchemy 2.0 特性"""
    AUTOCOMMIT: bool = False
    """是否自动提交事务"""
    AUTOFETCH: bool = False
    """是否自动刷新"""
    EXPIRE_ON_COMMIT: bool = False
    """是否在提交时过期"""

    DATABASE_TYPE: Literal["mysql", "postgres", "sqlite"] = "mysql"
    """数据库类型"""
    DATABASE_HOST: str = ""
    """数据库主机地址"""
    DATABASE_PORT: int = 3306
    """数据库端口
      - MySQL默认端口3306
      - PostgreSQL默认端口5432
    """
    DATABASE_USER: str = ""
    """数据库用户名"""
    DATABASE_PASSWORD: str = ""
    """数据库密码"""
    DATABASE_NAME: str = ""
    """数据库名称"""

    # ================================================= #
    # ******************** Redis配置 ******************* #
    # ================================================= #
    REDIS_ENABLE: bool = True
    """是否启用 Redis"""
    REDIS_HOST: str = "localhost"
    """Redis 主机地址"""
    REDIS_PORT: int = 6379
    """Redis 端口"""
    REDIS_DB_NAME: int = 1
    """Redis 数据库编号"""
    REDIS_USER: str | None = None
    """Redis 用户名（可选）"""
    REDIS_PASSWORD: str | None = None
    """Redis 密码（可选）"""

    # ================================================= #
    # ******************** 国密加密配置 ******************* #
    # ================================================= #
    SM2_PRIVATE_KEY: str = ""
    """SM2 私钥（十六进制字符串，64 字符 / 32 字节）"""
    SM2_PUBLIC_KEY: str = ""
    """SM2 公钥（十六进制字符串，130 字符 / 65 字节，含 04 前缀）"""
    SM4_KEY: str = ""
    """SM4 密钥（十六进制字符串，32 字符 / 16 字节），用于敏感字段加密"""

    # ================================================= #
    # ******************** 验证码配置 ******************* #
    # ================================================= #
    CAPTCHA_ENABLE: bool = False
    """是否启用验证码（登录页算术/图片验证；默认关闭）"""
    CAPTCHA_EXPIRE_SECONDS: int = 60
    """验证码过期时间（秒）"""
    CAPTCHA_FONT_SIZE: int = 32
    """验证码字体大小"""
    CAPTCHA_FONT_PATH: str = "static/assets/font/Arial.ttf"
    """验证码字体文件路径"""

    # ================================================= #
    # ***************** 第三方 OAuth 登录 **************** #
    # ================================================= #
    OAUTH_DEFAULT_ROLE_IDS: list[int] = [2]
    """OAuth 自动注册用户的默认角色 ID 列表"""
    OAUTH_FRONTEND_FALLBACK: str = "http://127.0.0.1:5173/login"
    """OAuth 回调异常时回跳的前端地址"""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    """GitHub OAuth Client ID（可选）"""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    """GitHub OAuth Client Secret（可选）"""
    OAUTH_GITEE_CLIENT_ID: str = ""
    """Gitee OAuth Client ID（可选）"""
    OAUTH_GITEE_CLIENT_SECRET: str = ""
    """Gitee OAuth Client Secret（可选）"""
    OAUTH_WECHAT_OPEN_APP_ID: str = ""
    """微信开放平台 App ID（可选）"""
    OAUTH_WECHAT_OPEN_APP_SECRET: str = ""
    """微信开放平台 App Secret（可选）"""
    OAUTH_QQ_APP_ID: str = ""
    """QQ OAuth App ID（可选）"""
    OAUTH_QQ_APP_SECRET: str = ""
    """QQ OAuth App Secret（可选）"""

    # ================================================= #
    # ******************* 外部 HTTP ******************* #
    # ================================================= #
    HTTPX_DEFAULT_TIMEOUT: float = 10.0
    """对外 HTTP 请求默认超时（秒）"""
    IP_LOCATION_ENABLE: bool = True
    """是否启用 IP 归属地查询（登录时）"""

    # ================================================= #
    # ********************* 操作日志 ******************* #
    # ================================================= #
    OPERATION_LOG_RECORD: bool = True
    """是否记录操作日志"""
    IGNORE_OPERATION_FUNCTION: list[str] = [
        "get_captcha_for_login",
        "get_sm2_public_key_controller",
        "list_tenants_for_login_controller",
    ]
    """忽略记录操作日志的函数名列表"""
    OPERATION_RECORD_METHOD: list[str] = ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
    """需要记录操作日志的 HTTP 方法"""
    OPERATION_LOG_SIGN_ENABLE: bool = True
    """是否为操作日志附加 SM2 签名（国密完整性保护）"""

    # ================================================= #
    # ******************* JSON 日志 ******************* #
    # ================================================= #
    LOG_JSON_FILE_ENABLE: bool = False
    """是否额外写入 JSON Lines 日志文件"""
    LOG_JSON_FILE_NAME: str = "app.jsonl"
    """JSON 日志文件名"""
    LOG_JSON_RETENTION_DAYS: int = 7
    """JSON 日志文件保留天数"""

    # ================================================= #
    # ******************* Gzip压缩 ******************* #
    # ================================================= #
    GZIP_ENABLE: bool = True
    """是否启用 Gzip 压缩"""
    GZIP_MIN_SIZE: int = 1000
    """Gzip 最小压缩大小（字节）"""
    GZIP_COMPRESS_LEVEL: int = 9
    """Gzip 压缩级别 (1-9)"""

    # ================================================= #
    # ***************** 静态文件 ***************** #
    # ================================================= #
    STATIC_ENABLE: bool = True
    """是否启用静态文件服务"""
    STATIC_URL: str = "/static"
    """静态文件访问路由"""
    STATIC_DIR: str = "static"
    """静态文件目录名"""

    # ================================================= #
    # ***************** 文件上传 ***************** #
    # ================================================= #
    UPLOAD_FILE_PATH: Path = Path("static/upload")
    """文件上传存储目录"""
    UPLOAD_MACHINE: str = "A"
    """上传机器标识"""
    ALLOWED_EXTENSIONS: list[str] = [".gif", ".jpg", ".jpeg", ".png", ".ico", ".svg", ".xls", ".xlsx"]
    """允许上传的文件扩展名列表"""
    MAX_FILE_SIZE: int = 10 * 1024 * 1024
    """最大上传文件大小（字节）"""

    # ================================================= #
    # ***************** 阿里云 OSS ***************** #
    # ================================================= #
    # 与 mystabx UPMS 对齐：OSS_ACCESS_KEY / OSS_SECRET_KEY；开启后「文件管理」走对象存储。
    OSS_ENABLE: bool = False
    """是否启用阿里云 OSS（True 且凭证齐全时，文件管理/上传走 OSS）"""
    OSS_ACCESS_KEY: str = ""
    """阿里云 AccessKey ID（勿提交真实值）"""
    OSS_SECRET_KEY: str = ""
    """阿里云 AccessKey Secret（勿提交真实值）"""
    OSS_ENDPOINT: str = "https://oss-cn-beijing.aliyuncs.com"
    """OSS Endpoint（含协议，如 https://oss-cn-beijing.aliyuncs.com）"""
    OSS_BUCKET_NAME: str = ""
    """Bucket 名称"""
    OSS_REGION: str = "cn-beijing"
    """区域（如 cn-beijing）"""
    OSS_CUSTOM_DOMAIN: str = ""
    """自定义域名 / CDN（可选；公有读时作直链主机，私有桶签名 URL 也会改写到此域名）"""
    OSS_PUBLIC_READ: bool = False
    """桶/前缀是否允许匿名读。False（默认）时始终返回签名 URL，避免私有桶 + 自定义域名直链 403"""
    OSS_PREFIX: str = "upload/"
    """对象键前缀（默认 upload/，与本地 static/upload 语义对齐）"""
    OSS_SIGN_URL_EXPIRE_SECONDS: int = 3600
    """私有桶签名 URL 有效期（秒）"""

    # ================================================= #
    # ***************** Swagger资源 ***************** #
    # ================================================= #
    SWAGGER_CSS_URL: str = "static/swagger/swagger-ui/swagger-ui.css"
    """Swagger UI 样式文件路径"""
    SWAGGER_JS_URL: str = "static/swagger/swagger-ui/swagger-ui-bundle.js"
    """Swagger UI JS 文件路径"""
    REDOC_JS_URL: str = "static/swagger/redoc/bundles/redoc.standalone.js"
    """ReDoc JS 文件路径"""
    CUSTOM_CSS_URL: str = "static/swagger/custom-ui/styles.css"
    """自定义 UI 样式文件路径"""
    CUSTOM_JS_URL: str = "static/swagger/custom-ui/scripts.js"
    """自定义 UI JS 文件路径"""
    FAVICON_URL: str = "static/swagger/favicon.png"
    """Favicon 图标路径"""

    # ================================================= #
    # ******************* ChromaDB ****************** #
    # ================================================= #
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")
    """ChromaDB 持久化存储目录"""
    CHROMA_COLLECTION_NAME: str = "knowledge_base"
    """ChromaDB 集合名称"""

    # ================================================= #
    # ******************* RAG Embedder ****************** #
    # ================================================= #
    RAG_EMBEDDER_TYPE: str = "fastembed"
    """Embedder 类型: fastembed(默认,本地) / openai / openai-like / ollama / sentence-transformer"""
    RAG_EMBEDDER_MODEL: str = ""
    """Embedder 模型（空则按类型使用默认，如 fastembed→BAAI/bge-small-en-v1.5）"""
    RAG_EMBEDDER_BASE_URL: str = ""
    """OpenAI 兼容 Embedder 的 API 地址（也可通过 ai_provider 供应商复用）"""
    RAG_EMBEDDER_API_KEY: str = ""
    """OpenAI 兼容 Embedder 的 API 密钥"""
    RAG_EMBEDDER_PROVIDER_ID: int | None = None
    """指定 ai_provider 表中用于 embedding 的供应商 ID（复用其 base_url/api_key/model）"""

    # ================================================= #
    # ******************* 请求限制 ****************** #
    # ================================================= #
    REQUEST_LIMITER_REDIS_PREFIX: str = "fastapiadmin:request_limiter:"
    """请求限制器 Redis 键前缀"""

    # ================================================= #
    # ******************* 派生属性 ******************* #
    # ================================================= #
    @property
    def STATIC_ROOT(self) -> Path:
        """静态文件绝对路径（由 STATIC_DIR + BASE_DIR 派生）。"""
        return BASE_DIR.joinpath(self.STATIC_DIR)

    @property
    def OSS_READY(self) -> bool:
        """OSS 已开启且 AccessKey / Secret / Bucket 均已配置。"""
        return bool(
            self.OSS_ENABLE
            and self.OSS_ACCESS_KEY.strip()
            and self.OSS_SECRET_KEY.strip()
            and self.OSS_BUCKET_NAME.strip()
            and self.OSS_ENDPOINT.strip()
        )

    # ================================================= #
    # ******************* 重构配置 ******************* #
    # ================================================= #
    @property
    def MIDDLEWARE_LIST(self) -> list[str | None]:
        """
        根据开关组装的中间件类路径列表（未启用的项为 None）。

        返回:
        - list[str | None]: 中间件 import 路径或 None。
        """
        # 中间件列表（注册时逆序叠加：下列第一项在列表中最前，最终位于最外层，优先生效）
        MIDDLEWARES: list[str | None] = [
            "app.core.middlewares.CustomCORSMiddleware" if self.CORS_ORIGIN_ENABLE else None,
            "app.core.middlewares.RequestLogMiddleware" if self.OPERATION_LOG_RECORD else None,
            "app.core.middlewares.CustomGZipMiddleware" if self.GZIP_ENABLE else None,
        ]
        return MIDDLEWARES

    @property
    def EVENT_LIST(self) -> list[str | None]:
        """
        应用启动时加载的全局异步事件模块路径列表。

        返回:
        - list[str | None]: 事件模块路径或 None。
        """
        EVENTS: list[str | None] = [
            "app.core.database.redis_connect" if self.REDIS_ENABLE else None,
        ]
        return EVENTS

    @property
    def ASYNC_DB_URI(self) -> str:
        """
        异步 SQLAlchemy 数据库 URL。

        返回:
        - str: 异步驱动连接串。

        异常:
        - ValueError: 数据库类型不支持时抛出。
        """
        if self.DATABASE_TYPE not in ("mysql", "postgres", "sqlite"):
            raise ValueError(
                f"数据库驱动不支持: {self.DATABASE_TYPE}, 异步数据库请选择 mysql、postgres、sqlite"
            )
        db_connect: str = ""
        if self.DATABASE_TYPE == "mysql":
            db_connect = f"mysql+asyncmy://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        elif self.DATABASE_TYPE == "postgres":
            db_connect = f"postgresql+asyncpg://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        else:
            db_connect = f"sqlite+aiosqlite:///{self.DATABASE_NAME}.db"
        return db_connect

    @property
    def DB_URI(self) -> str:
        """
        同步 SQLAlchemy 数据库 URL。

        返回:
        - str: 同步驱动连接串。

        异常:
        - ValueError: 数据库类型不支持时抛出。
        """
        if self.DATABASE_TYPE not in ("mysql", "postgres", "sqlite"):
            raise ValueError(
                f"数据库驱动不支持: {self.DATABASE_TYPE}, 同步数据库请选择 mysql、postgres、sqlite"
            )
        db_connect: str = ""
        if self.DATABASE_TYPE == "mysql":
            db_connect = f"mysql+pymysql://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        elif self.DATABASE_TYPE == "postgres":
            db_connect = f"postgresql+psycopg://{self.DATABASE_USER}:{quote_plus(self.DATABASE_PASSWORD)}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        else:
            db_connect = f"sqlite:///{self.DATABASE_NAME}.db"
        return db_connect

    @property
    def REDIS_URI(self) -> str:
        """Redis 连接 URL"""
        pw = self.REDIS_PASSWORD or ""
        user = f"{self.REDIS_USER}:" if self.REDIS_USER else ":"
        return f"redis://{user}{pw}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB_NAME}"

    @property
    def FASTAPI_CONFIG(self) -> dict[str, Any]:
        """
        创建 FastAPI 应用实例时使用的关键字参数子集。

        返回:
        - dict[str, Any]: debug、title、responses 等配置。
        """
        return {
            "debug": self.DEBUG,
            "title": self.TITLE,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "summary": self.SUMMARY,
            "docs_url": None,
            "redoc_url": None,
            "root_path": self.ROOT_PATH,
            "responses": {
                200: {"description": "成功"},
                400: {"description": "请求参数错误"},
                401: {"description": "未认证"},
                403: {"description": "未授权"},
                404: {"description": "资源不存在"},
                422: {"description": "请求参数验证错误"},
                500: {"description": "服务器内部错误"},
            },
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    获取全局 Settings 单例（lru_cache 缓存）。
    字段值来自 .env 文件 / OS 环境变量，不由构造参数传入。

    返回:
    - Settings: 配置实例。
    """
    return Settings()


settings = get_settings()
