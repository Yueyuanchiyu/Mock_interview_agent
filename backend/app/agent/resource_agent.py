from __future__ import annotations

from typing import List

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from app.agent.prompts import TOOL_AGENT_SYSTEM_PROMPT
from app.agent.tools import AgentToolFactory
from app.core.logging import Logger
from app.infrastructure.llm import get_chat_model


logger = Logger.get_logger(__name__)


class ResourceAdvisorAgent:
    """Actual LangChain Tool Calling agent for read-only retrieval and advice."""

    def __init__(self, tool_factory: AgentToolFactory) -> None:
        self.tools = tool_factory.build()
        self._agent = None

    def _build(self):
        if self._agent is None:
            self._agent = create_agent(
                model=get_chat_model(thinking=False),
                tools=self.tools,
                system_prompt=TOOL_AGENT_SYSTEM_PROMPT,
            )
        return self._agent

    async def advise(self, instruction: str) -> str:
        try:
            agent = self._build()
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=instruction)]}
            )
            messages = result.get("messages", [])
            return str(messages[-1].content) if messages else "暂无建议。"
        except Exception as exc:
            logger.warning("工具型资源顾问执行失败: %s", exc)
            return "资源顾问暂时不可用，请使用报告中的确定性推荐结果。"

