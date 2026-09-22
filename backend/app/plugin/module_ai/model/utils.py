"""
Agno 模型工厂 - 按 API 协议（api_type）多厂商模型创建
========================================================

核心设计（对应参考配置）：
    - 一级：供应商（Provider）
        {
            "name": "mimo-tp",
            "vendor": "customendpoint",
            "apiKey": "${input:chat.lm.secret.-452cc05c}",
            "apiType": "messages",          ← API 协议类型
            "models": [...]
        }
    - 二级：模型（Model）
        {
            "id": "mimo-v2.5",
            "name": "mimo-v2.5-tp",
            "url": "https://token-plan-cn.xiaomimimo.com/anthropic",   ← 端点
            "toolCalling": true,
            "vision": true,
            "maxInputTokens": 1024000,
            "maxOutputTokens": 128000,
            "thinking": true                 ← 思考模式
        }

关键结论：
    - 协议（协议类型）由 **apiType** 决定，而不是 vendor。
      例：vendor=customendpoint + apiType=messages → 用 Anthropic 协议（Claude）；
          vendor=deepseek + apiType=chat-completions → 用 OpenAI 协议（OpenAILike）。
    - 供应商与模型都可提供 url/baseUrl；模型级覆盖供应商级。
    - 不同供应商可以有相同模型 id，通过 provider 归属区分。
    - agno 原生模型类封装协议差异，因此这里只做「模型类选择 + 参数注入」。
"""

import importlib
from typing import Any

from app.core.logger import log


class AgnoModelFactory:
    """Agno 模型工厂：根据供应商+模型两级配置创建 Agno 模型实例。"""

    # ==================================================== #
    # API 协议（apiType） → agno 模型类（延迟导入避免 SDK 崩溃）
    # ==================================================== #
    API_TYPE_MODEL_MAP: dict[str, str] = {
        # OpenAI 兼容协议（chat-completions）
        "chat-completions": "agno.models.openai.like:OpenAILike",
        "chat": "agno.models.openai.like:OpenAILike",
        "openai": "agno.models.openai.like:OpenAILike",
        # Anthropic 协议（messages）
        "messages": "agno.models.anthropic.claude:Claude",
        "anthropic": "agno.models.anthropic.claude:Claude",
        # Google Gemini 协议
        "gemini": "agno.models.google.gemini:Gemini",
        "google": "agno.models.google.gemini:Gemini",
        # Ollama 本地协议
        "ollama": "agno.models.ollama.chat:Ollama",
        # Azure OpenAI
        "azure": "agno.models.azure.openai:AzureOpenAI",
    }

    # 需要额外 SDK 的 api_type（未安装时友好提示）
    SDK_REQUIREMENT: dict[str, str] = {
        "messages": "pip install anthropic",
        "anthropic": "pip install anthropic",
        "gemini": "pip install google-genai",
        "google": "pip install google-genai",
        "ollama": "pip install ollama",
        "azure": "pip install openai[azure]",
    }

    # 供应商 vendor → 默认 api_type（api_type 为空时的兜底推测）
    VENDOR_DEFAULT_API_TYPE: dict[str, str] = {
        "openai": "chat-completions",
        "openrouter": "chat-completions",
        "deepseek": "chat-completions",
        "moonshot": "chat-completions",
        "dashscope": "chat-completions",
        "siliconflow": "chat-completions",
        "internlm": "chat-completions",
        "xai": "chat-completions",
        "zhipu": "chat-completions",
        "anthropic": "messages",
        "google": "gemini",
        "ollama": "ollama",
        "azure": "azure",
        "customendpoint": "",  # 需由模型级 url/api_type 决定
    }

    # vendor → agno 模型类（api_type 为空/无法判断时的最终兜底，按 vendor 推测协议）
    VENDOR_MODEL_MAP: dict[str, str] = {
        "openai": "agno.models.openai.like:OpenAILike",
        "openrouter": "agno.models.openai.like:OpenAILike",
        "deepseek": "agno.models.openai.like:OpenAILike",
        "moonshot": "agno.models.openai.like:OpenAILike",
        "dashscope": "agno.models.openai.like:OpenAILike",
        "siliconflow": "agno.models.openai.like:OpenAILike",
        "internlm": "agno.models.openai.like:OpenAILike",
        "xai": "agno.models.openai.like:OpenAILike",
        "zhipu": "agno.models.openai.like:OpenAILike",
        # customendpoint 无法仅凭 vendor 确定协议——依赖 api_type/model url
        "customendpoint": "agno.models.openai.like:OpenAILike",  # 默认 OpenAILike，可被 api_type 覆盖
        "anthropic": "agno.models.anthropic.claude:Claude",
        "google": "agno.models.google.gemini:Gemini",
        "ollama": "agno.models.ollama.chat:Ollama",
        "azure": "agno.models.azure.openai:AzureOpenAI",
    }

    @classmethod
    def _resolve_model_path(cls, api_type: str, vendor: str) -> str:
        """
        确定模型类路径：api_type 优先，vendor 兜底。

        参数:
        - api_type (str): API 协议类型（可能为空）。
        - vendor (str): 供应商/厂商类型。

        返回:
        - str: agno 模型类路径（module:Class）。

        异常:
        - ValueError: 两者都无法确定协议时抛出。
        """
        key = (api_type or "").strip().lower()
        if key and key in cls.API_TYPE_MODEL_MAP:
            return cls.API_TYPE_MODEL_MAP[key]

        # api_type 为空 → 用 vendor 推测默认协议
        vendor_key = (vendor or "").strip().lower()
        if vendor_key in cls.VENDOR_MODEL_MAP:
            return cls.VENDOR_MODEL_MAP[vendor_key]

        raise ValueError(
            f"无法确定模型协议: api_type={api_type!r} vendor={vendor!r}。"
            f"支持 api_type: {sorted(cls.API_TYPE_MODEL_MAP.keys())}；"
            f"支持 vendor: {sorted(cls.VENDOR_MODEL_MAP.keys())}"
        )

    @classmethod
    def get_model_class(
        cls, api_type: str | None = None, vendor: str | None = None
    ) -> type:
        """
        根据 api_type / vendor 获取 agno 模型类（延迟导入）。

        参数:
        - api_type (str | None): API 协议类型（如 messages / chat-completions）。
        - vendor (str | None): 厂商类型（如 customendpoint / deepseek）。

        返回:
        - type: agno 模型类。

        异常:
        - ImportError: 对应 SDK 未安装。
        - ValueError: 无法确定协议。
        """
        model_path = cls._resolve_model_path(api_type or "", vendor or "")
        module_name, class_name = model_path.split(":")
        try:
            module = importlib.import_module(module_name)
            return getattr(module, class_name)
        except ImportError as e:
            # 给出 SDK 安装提示
            api_key = (api_type or "").lower()
            sdk_hint = cls.SDK_REQUIREMENT.get(api_key, "")
            hint = f"请先安装依赖: {sdk_hint}" if sdk_hint else str(e)
            log.error(f"模型 SDK 未安装: api_type={api_type} vendor={vendor}: {e}")
            raise ImportError(f"模型 SDK 未安装。{hint}") from e

    @classmethod
    def build_model(cls, config: dict[str, Any]) -> Any:
        """
        根据「供应商+模型」配置构建 Agno 模型实例。

        参数:
        - config (dict[str, Any]): 合并后的配置，必含：
            - provider_id (int): 所属供应商ID
            - api_type (str): 供应商API协议
            - vendor (str): 厂商类型
            - api_key (str | None): 供应商密钥
            - provider_base_url (str | None): 供应商默认地址
            - model_key (str): 模型id
            - name (str): 模型显示名
            - url (str | None): 模型端点地址（覆盖供应商默认）
            - tool_calling / vision / thinking / max_input_tokens / max_output_tokens / temperature

        返回:
        - Any: Agno 模型实例（OpenAILike / Claude / Gemini / Ollama / AzureOpenAI）。
        """
        api_type = (config.get("api_type") or "").strip().lower()
        vendor = (config.get("vendor") or "openai").strip().lower()
        model_key = config.get("model_key") or config.get("name") or ""

        # 模型端点优先，其次供应商默认
        model_url = config.get("url") or config.get("provider_base_url") or ""

        model_cls = cls.get_model_class(api_type=api_type, vendor=vendor)

        # 通用参数（所有协议基本都用）
        common_kwargs: dict[str, Any] = {}
        if model_url:
            common_kwargs["base_url"] = model_url
        if config.get("api_key"):
            common_kwargs["api_key"] = config["api_key"]
        if config.get("temperature") is not None:
            common_kwargs["temperature"] = config["temperature"]
        if config.get("max_output_tokens") is not None:
            common_kwargs["max_tokens"] = config["max_output_tokens"]

        # 思考模式：调用方可显式覆盖（enable_thinking），否则用模型配置 thinking
        thinking_enabled = config.get("enable_thinking")
        if thinking_enabled is None:
            thinking_enabled = config.get("thinking", False)

        # 协议特殊处理
        resolved = cls._resolve_model_path(api_type, vendor)  # 判断实际协议
        if resolved.endswith(":Claude"):
            # Anthropic messages 协议：thinking 原生支持
            if thinking_enabled:
                common_kwargs["thinking"] = {"type": "enabled"}
            # Anthropic 官方使用 x-api-key 头（由 SDK 处理），api_key 正常传
        elif resolved.endswith(":Gemini"):
            # Gemini 不需要 base_url（官方用 SDK 端点），但兼容自建
            if thinking_enabled:
                common_kwargs["thinking"] = {"type": "enabled"}
        elif resolved.endswith(":Ollama"):
            # Ollama 本地：不需要 api_key；host 由 base_url 提供
            common_kwargs.pop("api_key", None)
            if config.get("url"):
                common_kwargs["host"] = config["url"]
            elif config.get("provider_base_url"):
                common_kwargs["host"] = config["provider_base_url"]
            common_kwargs.pop("base_url", None)
        elif resolved.endswith(":AzureOpenAI"):
            # Azure：使用 azure_deployment 而非 model_key
            common_kwargs.pop("base_url", None)
            azure_endpoint = config.get("url") or config.get("provider_base_url") or ""
            if azure_endpoint:
                common_kwargs["azure_endpoint"] = azure_endpoint
            common_kwargs["azure_deployment"] = model_key
        else:
            # OpenAI 兼容协议（OpenAILike / DeepSeek 等）
            if vendor == "deepseek":
                # DeepSeek 推理模型（v4-flash/pro）：思考模式默认开启，必须显式控制开关。
                # 官方文档：开关用顶层 thinking 字段（OpenAI 格式），经 extra_body 透传；
                # reasoning_effort 仅控制思考强度（low/medium/high/max）。
                if thinking_enabled:
                    common_kwargs["reasoning_effort"] = "medium"
                    common_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                else:
                    common_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
            elif thinking_enabled:
                # 其他 OpenAI 兼容模型：用 reasoning_effort 控制（OpenAI o 系列等）
                common_kwargs["reasoning_effort"] = "medium"

        log.debug(
            f"构建模型: vendor={vendor} api_type={api_type} model={model_key} url={model_url or '-'}"
        )

        # 实例化（OpenAILike/Claude/Gemini/Ollama 均以 id 作为模型名）
        return model_cls(id=model_key, **common_kwargs)
