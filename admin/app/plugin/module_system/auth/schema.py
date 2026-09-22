from pydantic import BaseModel, ConfigDict, Field


class JWTOutSchema(BaseModel):
    """JWT响应模型"""

    model_config = ConfigDict(from_attributes=True)

    access_token: str = Field(..., min_length=1, description="访问token")
    refresh_token: str = Field(..., min_length=1, description="刷新token")
    token_type: str = Field(default="Bearer", description="token类型")
    expires_in: int = Field(..., gt=0, description="过期时间(秒)")


class RefreshTokenPayloadSchema(BaseModel):
    """刷新Token载荷模型"""

    refresh_token: str = Field(..., min_length=1, description="刷新token")


class CaptchaOutSchema(BaseModel):
    """验证码响应模型"""

    model_config = ConfigDict(from_attributes=True)

    enable: bool = Field(default=True, description="是否启用验证码")
    key: str = Field(..., min_length=1, description="验证码唯一标识")
    img_base: str = Field(..., min_length=1, description="Base64编码的验证码图片")


class LoginTenantOptionSchema(BaseModel):
    """登录页可选租户"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="租户ID")
    name: str = Field(..., description="租户名称")
    code: str = Field(..., description="租户编码")


class AutoLoginUserSchema(BaseModel):
    """免登录用户信息模型"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    name: str = Field(..., description="用户姓名")
    avatar: str | None = Field(default=None, description="头像")


class AutoLoginTokenSchema(BaseModel):
    """免登录Token响应模型"""

    model_config = ConfigDict(from_attributes=True)

    token: str = Field(..., description="免登录Token")
    user: AutoLoginUserSchema = Field(..., description="用户信息")
