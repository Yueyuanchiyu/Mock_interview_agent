from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.repositories.interview import InterviewRepository
from app.services.context import ContextService
from app.services.question import QuestionService


class FindResourcesArgs(BaseModel):
    role_code: str = Field(description="岗位编码，例如 java_backend")
    keywords: List[str] = Field(default_factory=list, description="薄弱点关键词")
    limit: int = Field(default=8, ge=1, le=20, description="最多返回的资源数量")


class InterviewRoundsArgs(BaseModel):
    session_id: int = Field(ge=1, description="面试会话 ID")
    user_key: str = Field(description="当前登录用户标识")


class KnowledgeContextArgs(BaseModel):
    role_code: str = Field(description="岗位编码")
    question_id: int = Field(ge=1, description="当前面试题目 ID")
    answer_text: str = Field(description="候选人回答")


class RoundAnalysisArgs(BaseModel):
    session_id: int = Field(ge=1, description="面试会话 ID")
    question_no: int = Field(ge=1, description="题目序号（从 1 开始）")
    user_key: str = Field(description="当前登录用户标识")


class GrowthArgs(BaseModel):
    user_key: str = Field(description="当前登录用户标识")
    role_code: Optional[str] = Field(default=None, description="可选，按岗位过滤")


class HistoryArgs(BaseModel):
    user_key: str = Field(description="当前登录用户标识")


def readonly_tool(
    name: str,
    description: str,
    args_schema: type[BaseModel],
    func: Callable[..., Any],
) -> StructuredTool:
    """构建一个只读工具，统一封装为同步函数形式。"""
    return StructuredTool.from_function(
        func=func,
        name=name,
        description=description,
        args_schema=args_schema,
    )


class AgentToolFactory:
    _MAX_ROWS = 10

    def __init__(
        self,
        question_service: QuestionService,
        interview_repository: InterviewRepository,
        context_service: ContextService,
    ) -> None:
        self.question_service = question_service
        self.interview_repository = interview_repository
        self.context_service = context_service

    @staticmethod
    def _serialize(payload: Any) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _last(rows: List[Dict[str, Any]], limit: int | None = None) -> List[Dict[str, Any]]:
        return list(rows)[-(limit or AgentToolFactory._MAX_ROWS):]

    @staticmethod
    def _denied() -> str:
        return json.dumps({"error": "会话不存在或无权限"}, ensure_ascii=False)

    def _check_session(self, session_id: int, user_key: str) -> Optional[Dict[str, Any]]:
        session = self.interview_repository.get_session(session_id)
        if not session or str(session.get("user_key")) != str(user_key):
            return None
        return session

    def build(self) -> List[StructuredTool]:
        def find_resources(role_code: str, keywords: List[str], limit: int = 8) -> str:
            rows = self.question_service.search_learning_resources(role_code, keywords, limit)
            return self._serialize(rows)

        def get_interview_rounds(session_id: int, user_key: str) -> str:
            if self._check_session(session_id, user_key) is None:
                return self._denied()
            rounds = self.interview_repository.list_rounds(session_id)
            return self._serialize(self._last(rounds))

        def retrieve_knowledge(role_code: str, question_id: int, answer_text: str) -> str:
            question = self.question_service.require_question(question_id)
            result = self.context_service.build_reference_context(role_code, question, answer_text)
            return self._serialize(result)

        def get_round_analysis(session_id: int, question_no: int, user_key: str) -> str:
            if self._check_session(session_id, user_key) is None:
                return self._denied()
            round_ = self.interview_repository.get_round(session_id, question_no)
            if not round_:
                return json.dumps({"error": "题目不存在"}, ensure_ascii=False)
            return self._serialize(round_)

        def get_growth_trend(user_key: str, role_code: Optional[str] = None) -> str:
            rows = self.interview_repository.get_growth(user_key, role_code)
            return self._serialize(self._last(rows))

        def list_interview_history(user_key: str) -> str:
            rows = self.interview_repository.list_history(user_key)
            return self._serialize(self._last(rows))

        return [
            readonly_tool(
                name="find_learning_resources",
                description="按岗位和薄弱点关键词查询学习资源。用于候选人需要补齐薄弱点、获取学习材料时调用。只读。",
                args_schema=FindResourcesArgs,
                func=find_resources,
            ),
            readonly_tool(
                name="get_interview_rounds",
                description="读取某次面试的逐题记录（题目、回答、评分）。用于回顾本次面试表现时调用。只读。",
                args_schema=InterviewRoundsArgs,
                func=get_interview_rounds,
            ),
            readonly_tool(
                name="retrieve_interview_knowledge",
                description="按题目 ID 检索岗位知识上下文（知识点、评分要点、追问要点）。用于需要某道题的背景知识时调用。只读。",
                args_schema=KnowledgeContextArgs,
                func=retrieve_knowledge,
            ),
            readonly_tool(
                name="get_round_analysis",
                description="读取某次面试某道题的七维评分、strengths、weaknesses、suggestions。用于针对某道题给出改进建议时调用。只读。",
                args_schema=RoundAnalysisArgs,
                func=get_round_analysis,
            ),
            readonly_tool(
                name="get_growth_trend",
                description="读取用户历史成长趋势（各维度平均分随时间变化）。用于回答进步情况、趋势问题时调用。只读。",
                args_schema=GrowthArgs,
                func=get_growth_trend,
            ),
            readonly_tool(
                name="list_interview_history",
                description="读取用户历史面试记录（时间、岗位、总分、报告链接）。用于回顾历史面试时调用。只读。",
                args_schema=HistoryArgs,
                func=list_interview_history,
            ),
        ]

