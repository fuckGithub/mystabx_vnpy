from typing import Any

from agno.agent import Agent
from agno.team import Team

from app.core.logger import log


class AgnoFactory:
    """Agno 工厂类 - 统一管理 Agent、Team 创建逻辑。

    模型统一由 AiModelService.build_model_by_id() 基于数据库配置构建，
    不再从环境变量读取 OPENAI_* 配置。
    """

    # 配置常量
    AGENT_DESCRIPTION = "你是 FastapiAdmin 系统的AI助手，可以回答系统操作指南问题，也可以查询系统实时数据（用户、角色、菜单等）。"
    AGENT_INSTRUCTIONS = [
        "你是 FastapiAdmin 系统的AI助手",
        "优先从知识库中检索答案，如果知识库没有相关信息再尝试直接回答",
        "可以使用系统工具查询实时数据，如用户列表、角色列表、菜单结构等",
        "回答要简洁明了，使用中文",
        "如果不确定答案，请说明",
    ]
    AGENT_EXPECTED_OUTPUT = "中文回答"
    AGENT_TEMPERATURE = 0.7
    NUM_HISTORY_RUNS = 3

    def create_agent(
        self,
        user_id: str,
        dept_id: str,
        session_id: str,
        model: Any,
        db: Any | None = None,
        knowledge: Any | None = None,
        tools: list | None = None,
    ) -> Team:
        """
        创建带 Agent 的 Team 实例。

        参数:
        - user_id (str): 用户标识。
        - dept_id (str): 部门/团队标识。
        - session_id (str): 会话 ID。
        - model (Any): Agno 模型实例（由 AiModelService.build_model_by_id 构建，必传）。
        - db (Any | None): Agno 持久化数据库实例，可选。
        - knowledge (Any | None): 知识库实例（Knowledge），启用后 Agent 自动检索。
        - tools (list | None): 工具列表（@tool 装饰的 Function 对象）。

        返回:
        - Team: 配置好的 Team。
        """

        # 构建 Agent 参数
        agent_kwargs: dict[str, Any] = {
            "id": user_id,
            "name": "fastapiadmin_agent",
            "role": "You are a helpful AI assistant for FastapiAdmin system",
            "description": self.AGENT_DESCRIPTION,
            "tools": tools or [],
        }

        # 传入知识库时，Agent 启用 search_knowledge 自动检索
        if knowledge is not None:
            agent_kwargs["knowledge"] = knowledge
            agent_kwargs["search_knowledge"] = True
            log.debug("Agent 已启用知识库检索")

        fastapiadmin_agent = Agent(**agent_kwargs)

        # 构建 Team 参数
        team_kwargs: dict[str, Any] = {
            "id": dept_id,
            "user_id": user_id,
            "session_id": session_id,
            "model": model,
            "members": [fastapiadmin_agent],
            "instructions": self.AGENT_INSTRUCTIONS,
            "expected_output": self.AGENT_EXPECTED_OUTPUT,
            "add_datetime_to_context": True,
            "add_history_to_context": True,
            "markdown": True,
            "num_history_runs": self.NUM_HISTORY_RUNS,
            "input_schema": None,
            "output_schema": None,
            "parse_response": True,
            "read_chat_history": True,
            "db": db,
        }

        # Team 级别也设置知识库和工具（成员 Agent 与 Team 都能访问）
        if knowledge is not None:
            team_kwargs["knowledge"] = knowledge
            team_kwargs["search_knowledge"] = True
        if tools:
            team_kwargs["tools"] = tools

        return Team(**team_kwargs)
