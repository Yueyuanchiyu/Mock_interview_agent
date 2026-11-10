from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict


AgentAction = Literal["start", "answer", "followup", "next", "finish"]


class InterviewState(TypedDict, total=False):
    action: AgentAction
    user_key: str
    session_id: int
    role_code: str
    role_name: str
    question_count: int
    question_no: int
    answer_text: str
    expression_metrics: Dict[str, Any]
    followup_no: int
    followup_answer: str
    question: Dict[str, Any]
    context_items: List[str]
    retrieval_trace: List[Dict[str, Any]]
    analysis: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    result: Dict[str, Any]

