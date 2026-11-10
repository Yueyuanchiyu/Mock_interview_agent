from __future__ import annotations

import json
from typing import Any, Dict, List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.repositories.interview import InterviewRepository
from app.services.context import ContextService
from app.services.question import QuestionService


class FindResourcesArgs(BaseModel):
    role_code: str = Field(description="岗位编码，例如 java_backend")
    keywords: List[str] = Field(default_factory=list, description="薄弱点关键词")
    limit: int = Field(default=8, ge=1, le=20)


class InterviewRoundsArgs(BaseModel):
    session_id: int = Field(ge=1)
    user_key: str = Field(description="当前登录用户标识")


class KnowledgeContextArgs(BaseModel):
    role_code: str = Field(description="岗位编码")
    question_title: str = Field(description="当前面试题目")
    answer_text: str = Field(description="候选人回答")


class AgentToolFactory:
    def __init__(
        self,
        question_service: QuestionService,
        interview_repository: InterviewRepository,
        context_service: ContextService,
    ) -> None:
        self.question_service = question_service
        self.interview_repository = interview_repository
        self.context_service = context_service

    def build(self) -> List[StructuredTool]:
        def find_resources(
            role_code: str,
            keywords: List[str],
            limit: int = 8,
        ) -> str:
            rows = self.question_service.search_learning_resources(
                role_code, keywords, limit
            )
            return json.dumps(rows, ensure_ascii=False, default=str)

        def get_interview_rounds(session_id: int, user_key: str) -> str:
            session = self.interview_repository.get_session(session_id)
            if not session or str(session.get("user_key")) != str(user_key):
                return json.dumps({"error": "会话不存在或无权限"}, ensure_ascii=False)
            rounds = self.interview_repository.list_rounds(session_id)
            return json.dumps(rounds, ensure_ascii=False, default=str)

        def retrieve_knowledge(
            role_code: str,
            question_title: str,
            answer_text: str,
        ) -> str:
            question = {
                "title": question_title,
                "question_type": "",
                "scoring_points": "",
                "followup_points": "",
                "tags": "",
            }
            result = self.context_service.build_reference_context(
                role_code, question, answer_text
            )
            return json.dumps(result, ensure_ascii=False)

        return [
            StructuredTool.from_function(
                func=find_resources,
                name="find_learning_resources",
                description="按岗位和薄弱点查询学习资源。只读。",
                args_schema=FindResourcesArgs,
            ),
            StructuredTool.from_function(
                func=get_interview_rounds,
                name="get_interview_rounds",
                description="读取当前用户的面试逐题记录。只读。",
                args_schema=InterviewRoundsArgs,
            ),
            StructuredTool.from_function(
                func=retrieve_knowledge,
                name="retrieve_interview_knowledge",
                description="检索岗位知识上下文。只读。",
                args_schema=KnowledgeContextArgs,
            ),
        ]

