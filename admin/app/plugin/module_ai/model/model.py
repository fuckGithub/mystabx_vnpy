from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin


class AiProviderModel(ModelMixin):
    """
    AI 供应商表（一级）

    对应参考配置的 Provider 层级：
    {
        "name": "mimo-tp",
        "vendor": "customendpoint",
        "apiKey": "${input:chat.lm.secret.-452cc05c}",
        "apiType": "messages",
        "models": [ ... ]
    }

    一个供应商（vendor）可包含多个模型；不同供应商可以有同名模型，
    通过 provider_id 归属区分。
    """

    __tablename__: str = "ai_provider"
    __table_args__: dict[str, str] = {"comment": "AI供应商表"}
    __loader_options__: list[str] = ["created_by", "updated_by"]

    # 基本信息（对应参考配置顶层字段）
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="供应商名称（如 mimo-tp / DeepSeek）")
    vendor: Mapped[str] = mapped_column(String(32), nullable=False, comment="厂商类型(openai/anthropic/google/ollama/deepseek/customendpoint等)")
    api_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="chat-completions", comment="API协议类型(chat-completions/messages/ollama/gemini等)"
    )
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="供应商API密钥（模型级可覆盖）")
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="供应商默认API地址（模型可覆盖）")

    # 状态与排序
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False, comment="是否为默认供应商")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0, comment="排序号（越大越靠前）")

    # 关系：一个供应商下多个模型
    models: Mapped[list[AiModelModel]] = relationship(
        "AiModelModel",
        back_populates="provider_obj",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AiModelModel(ModelMixin):
    """
    AI 模型表（二级）

    对应参考配置 models[] 数组元素：
    {
        "id": "mimo-v2.5",
        "name": "mimo-v2.5-tp",
        "url": "https://.../anthropic",
        "toolCalling": true,
        "vision": true,
        "maxInputTokens": 1024000,
        "maxOutputTokens": 128000,
        "thinking": true
    }

    不同供应商可以有相同模型 id；通过 provider_id 归属区分。
    """

    __tablename__: str = "ai_model"
    __table_args__: dict[str, str] = {"comment": "AI模型表"}
    __loader_options__: list[str] = ["created_by", "updated_by"]

    # 归属供应商（FK）
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("ai_provider.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属供应商ID",
    )

    # 模型标识（对应参考配置 id/name）
    model_key: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型id（如 mimo-v2.5）")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型显示名（如 mimo-v2.5-tp）")
    url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="模型端点地址（覆盖供应商默认，可空）")

    # 能力元数据（对应参考配置 toolCalling/vision/maxInputTokens/maxOutputTokens/thinking）
    tool_calling: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False, comment="是否支持工具调用")
    vision: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False, comment="是否支持视觉/图片输入")
    max_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=131072, comment="最大输入token数")
    max_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=4096, comment="最大输出token数")
    thinking: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False, comment="是否启用思考模式（推理模型）")

    # 模型参数
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.7, comment="温度（默认0.7）")

    # 状态与排序
    is_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=False, comment="是否为默认模型")
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0, comment="排序号（越大越靠前）")

    # 关系：归属供应商
    provider_obj: Mapped[AiProviderModel] = relationship(
        "AiProviderModel",
        back_populates="models",
        lazy="joined",
    )
