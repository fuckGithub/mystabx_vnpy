
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.base_schema import BaseSchema

# ============================================================ #
# 一级：AI 供应商（Provider）Schema
# 对应参考配置顶层 { name, vendor, apiKey, apiType, models[] }
# ============================================================ #


class AiModelItemSchema(BaseModel):
    """二级：模型条目（嵌套在供应商内）——对应参考配置 models[] 元素"""

    model_config = ConfigDict(from_attributes=True)

    model_key: str = Field(..., min_length=1, max_length=128, description="模型id（如 mimo-v2.5）")
    name: str = Field(..., min_length=1, max_length=128, description="模型显示名（如 mimo-v2.5-tp）")
    url: str | None = Field(default=None, max_length=255, description="模型端点地址（可覆盖供应商默认）")
    tool_calling: bool | None = Field(default=False, description="是否支持工具调用（toolCalling）")
    vision: bool | None = Field(default=False, description="是否支持视觉/图片输入")
    max_input_tokens: int | None = Field(default=131072, ge=1, description="最大输入token数（maxInputTokens）")
    max_output_tokens: int | None = Field(default=4096, ge=1, description="最大输出token数（maxOutputTokens）")
    thinking: bool | None = Field(default=False, description="是否启用思考模式（推理模型）")
    temperature: float | None = Field(default=0.7, ge=0, le=2, description="温度（默认0.7）")
    is_default: bool | None = Field(default=False, description="是否为默认模型")
    sort_order: int | None = Field(default=0, description="排序号（越大越靠前）")

    @field_validator("model_key", "name")
    def validate_not_blank(cls, value: str) -> str:
        """校验非空白字符串。"""
        if not value or value.strip() == "":
            raise ValueError("不能为空字符串")
        return value.strip()


class AiProviderCreateSchema(BaseModel):
    """一级：新增供应商——对应参考配置 Provider 顶层"""

    name: str = Field(..., min_length=1, max_length=64, description="供应商名称（如 mimo-tp / DeepSeek）")
    vendor: str = Field(..., min_length=1, max_length=32, description="厂商类型(openai/anthropic/google/ollama/deepseek/customendpoint等)")
    api_type: str = Field(default="chat-completions", min_length=1, max_length=32, description="API协议类型(chat-completions/messages/gemini/ollama等)")
    api_key: str | None = Field(default=None, max_length=255, description="供应商API密钥（模型级可覆盖）")
    base_url: str | None = Field(default=None, max_length=255, description="供应商默认API地址（模型可覆盖）")
    is_default: bool | None = Field(default=False, description="是否为默认供应商")
    sort_order: int | None = Field(default=0, description="排序号（越大越靠前）")
    description: str | None = Field(default=None, max_length=255, description="供应商描述/备注")

    @field_validator("name", "vendor")
    def validate_not_blank(cls, value: str) -> str:
        """校验非空白字符串。"""
        if not value or value.strip() == "":
            raise ValueError("不能为空字符串")
        return value.strip()


class AiProviderUpdateSchema(AiProviderCreateSchema):
    """一级：更新供应商（全量更新，字段同创建）"""


class AiProviderTestConnectivitySchema(AiProviderCreateSchema):
    """测试供应商连通性（额外要求传入 model_key）"""

    model_key: str = Field(..., min_length=1, max_length=128, description="用于测试连通性的模型Key")


class AiProviderOutSchema(BaseSchema):
    """一级：供应商响应模型"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., description="供应商名称")
    vendor: str = Field(..., description="厂商类型")
    api_type: str = Field(..., description="API协议类型")
    api_key: str | None = Field(None, description="供应商API密钥")
    base_url: str | None = Field(None, description="供应商默认API地址")
    is_default: bool | None = Field(None, description="是否为默认供应商")
    sort_order: int | None = Field(None, description="排序号")


class AiProviderDetailOutSchema(AiProviderOutSchema):
    """一级：供应商详情（含嵌套模型列表）"""

    models: list[AiModelItemSchema] | None = Field(None, description="该供应商下的模型列表")


class AiProviderQueryParam(BaseModel):
    """一级：供应商查询参数（分页/列表通用）"""

    name: str | None = Field(default=None, description="供应商名称（模糊匹配）")
    vendor: str | None = Field(default=None, description="厂商类型（精确匹配）")
    api_type: str | None = Field(default=None, description="API协议类型（精确匹配）")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")


# ============================================================ #
# 二级：AI 模型（Model）Schema
# 对应参考配置 models[] 元素字段
# ============================================================ #


class AiModelCreateSchema(BaseModel):
    """二级：新增模型（需指定归属供应商 provider_id）"""

    provider_id: int = Field(..., ge=1, description="归属供应商ID")
    model_key: str = Field(..., min_length=1, max_length=128, description="模型id（如 mimo-v2.5）")
    name: str = Field(..., min_length=1, max_length=128, description="模型显示名（如 mimo-v2.5-tp）")
    url: str | None = Field(default=None, max_length=255, description="模型端点地址（可覆盖供应商默认）")
    tool_calling: bool | None = Field(default=False, description="是否支持工具调用（toolCalling）")
    vision: bool | None = Field(default=False, description="是否支持视觉/图片输入")
    max_input_tokens: int | None = Field(default=131072, ge=1, description="最大输入token数")
    max_output_tokens: int | None = Field(default=4096, ge=1, description="最大输出token数")
    thinking: bool | None = Field(default=False, description="是否启用思考模式（推理模型）")
    temperature: float | None = Field(default=0.7, ge=0, le=2, description="温度（默认0.7）")
    is_default: bool | None = Field(default=False, description="是否为默认模型")
    sort_order: int | None = Field(default=0, description="排序号（越大越靠前）")
    description: str | None = Field(default=None, max_length=255, description="供应商描述/备注")

    @field_validator("model_key", "name")
    def validate_not_blank(cls, value: str) -> str:
        """校验非空白字符串。"""
        if not value or value.strip() == "":
            raise ValueError("不能为空字符串")
        return value.strip()


class AiModelUpdateSchema(AiModelCreateSchema):
    """二级：更新模型（全量更新，字段同创建）"""


class AiModelOutSchema(BaseSchema):
    """二级：模型响应模型"""

    model_config = ConfigDict(from_attributes=True)

    provider_id: int = Field(..., description="归属供应商ID")
    model_key: str = Field(..., description="模型id")
    name: str = Field(..., description="模型显示名")
    url: str | None = Field(None, description="模型端点地址")
    tool_calling: bool | None = Field(None, description="是否支持工具调用")
    vision: bool | None = Field(None, description="是否支持视觉/图片输入")
    max_input_tokens: int | None = Field(None, description="最大输入token数")
    max_output_tokens: int | None = Field(None, description="最大输出token数")
    thinking: bool | None = Field(None, description="是否启用思考模式")
    temperature: float | None = Field(None, description="温度")
    is_default: bool | None = Field(None, description="是否为默认模型")
    sort_order: int | None = Field(None, description="排序号")


class AiModelOutWithProviderSchema(AiModelOutSchema):
    """二级：模型响应（含所属供应商摘要信息）"""

    provider_name: str | None = Field(None, description="所属供应商名称")
    vendor: str | None = Field(None, description="所属供应商厂商类型")
    api_type: str | None = Field(None, description="所属供应商API协议类型")


class AiModelQueryParam(BaseModel):
    """二级：模型查询参数（分页/列表通用）"""

    provider_id: int | None = Field(default=None, description="按供应商ID过滤（精确匹配）")
    model_key: str | None = Field(default=None, description="模型id（精确匹配）")
    name: str | None = Field(default=None, description="模型显示名（模糊匹配）")
    status: str | None = Field(default=None, description="状态（0正常 1停用）")


class AiModelListOutSchema(BaseModel):
    """前端模型下拉列表响应模型（不暴露密钥）"""

    id: int = Field(..., description="模型ID")
    provider_id: int = Field(..., description="所属供应商ID")
    provider_name: str | None = Field(None, description="所属供应商名称")
    vendor: str | None = Field(None, description="厂商类型")
    api_type: str | None = Field(None, description="API协议类型")
    model_key: str = Field(..., description="模型id")
    name: str = Field(..., description="模型显示名")
    thinking: bool | None = Field(None, description="是否启用思考模式")
    tool_calling: bool | None = Field(None, description="是否支持工具调用")
    vision: bool | None = Field(None, description="是否支持视觉/图片输入")
    is_default: bool | None = Field(None, description="是否为默认模型")

    model_config = ConfigDict(from_attributes=True)
