from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.core.config import settings


class InterviewStartRequest(BaseModel):
    role_code: str = Field(..., min_length=1, max_length=50)
    question_count: int = Field(3, ge=1, le=10)


class InterviewAnswerRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    question_no: int = Field(..., ge=1)
    answer_text: str = Field(..., min_length=1, max_length=settings.answer_max_length)
    expression_metrics: Optional[Dict[str, Any]] = None


class FollowupAnswerRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    question_no: int = Field(..., ge=1)
    followup_no: int = Field(..., ge=1)
    followup_answer: str = Field(..., min_length=1, max_length=settings.answer_max_length)


class FinishInterviewRequest(BaseModel):
    session_id: int = Field(..., ge=1)


class AgentAdviceRequest(BaseModel):
    session_id: int = Field(..., ge=1)
    instruction: str = Field(
        "请根据本次面试表现，使用工具查询学习资源并给出下一轮练习建议。",
        min_length=1,
        max_length=1000,
    )

