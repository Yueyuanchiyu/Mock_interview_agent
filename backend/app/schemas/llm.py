from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class AnswerEvaluation(BaseModel):
    technical_score: int = Field(ge=0, le=10)
    depth_score: int = Field(ge=0, le=10)
    logic_score: int = Field(ge=0, le=10)
    role_match_score: int = Field(ge=0, le=10)
    speech_rate_score: int = Field(default=5, ge=0, le=10)
    clarity_score: int = Field(default=5, ge=0, le=10)
    confidence_score: int = Field(default=5, ge=0, le=10)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    need_followup: bool = False
    followup_question: str = ""


class FollowupDecision(BaseModel):
    question: str = ""


class ResourceChoice(BaseModel):
    id: int
    reason: str
    priority: int = Field(default=99, ge=1)


class ResourceSelection(BaseModel):
    resources: List[ResourceChoice] = Field(default_factory=list)


class InterviewSummary(BaseModel):
    summary: str

