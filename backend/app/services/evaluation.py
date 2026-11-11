from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.prompts import (
    EVALUATION_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    evaluation_prompt,
    followup_prompt,
    summary_prompt,
)
from app.core.logging import Logger
from app.infrastructure.llm import get_chat_model
from app.schemas.llm import AnswerEvaluation, FollowupDecision, InterviewSummary


logger = Logger.get_logger(__name__)


class EvaluationService:
    async def evaluate_answer(
        self,
        role_name: str,
        question: Dict[str, Any],
        answer_text: str,
        reference_context: List[str],
        expression_metrics: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        prompt = evaluation_prompt(
            role_name, question, answer_text, reference_context, expression_metrics
        )
        try:
            model = get_chat_model(thinking=True).with_structured_output(AnswerEvaluation)
            result = await model.ainvoke(
                [
                    SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            return result.model_dump()
        except Exception as exc:
            logger.warning("LLM 结构化评分失败，使用规则降级: %s", exc)
            return self._fallback(answer_text, expression_metrics)

    async def generate_dynamic_followup(
        self,
        role_name: str,
        question: Dict[str, Any],
        main_answer: str,
        followup_history: str,
        latest_answer: str,
        reference_context: List[str],
    ) -> str:
        prompt = followup_prompt(
            role_name,
            question,
            main_answer,
            followup_history,
            latest_answer,
            reference_context,
        )
        try:
            model = get_chat_model(thinking=False).with_structured_output(FollowupDecision)
            result = await model.ainvoke(
                [
                    SystemMessage(content=FOLLOWUP_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            return result.question.strip()
        except Exception as exc:
            logger.warning("动态追问失败: %s", exc)
            return ""

    async def generate_summary(
        self,
        role_name: str,
        rounds: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        prompt = summary_prompt(role_name, rounds, recommendations)
        try:
            model = get_chat_model(thinking=True).with_structured_output(InterviewSummary)
            result = await model.ainvoke(
                [
                    SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
            return result.summary.strip()
        except Exception as exc:
            logger.warning("LLM 总结失败，使用模板降级: %s", exc)
            return (
                "本次模拟面试已完成。建议继续围绕核心技术原理、项目细节和"
                "结构化表达进行针对性练习。"
            )

    @staticmethod
    def _fallback(
        answer_text: str,
        expression_metrics: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        length = len((answer_text or "").strip())
        base = 6 if length >= 80 else 4
        need_followup = length < 100
        speech = clarity = confidence = 5
        if expression_metrics and expression_metrics.get("input_mode") == "voice":
            duration = float(expression_metrics.get("duration_sec") or 0)
            recognized = int(expression_metrics.get("recognized_text_length") or 0)
            avg_confidence = float(expression_metrics.get("avg_confidence") or 0)
            pauses = int(expression_metrics.get("pause_count") or 0)
            if duration > 0:
                chars_per_minute = recognized / duration * 60
                speech = 8 if 80 <= chars_per_minute <= 220 else 5
            clarity = 8 if avg_confidence >= 0.85 else 6 if avg_confidence >= 0.70 else 4
            confidence = max(4, min(8, 8 - min(pauses, 4)))
        return AnswerEvaluation(
            technical_score=base,
            depth_score=max(base - 1, 0),
            logic_score=base,
            role_match_score=base,
            speech_rate_score=speech,
            clarity_score=clarity,
            confidence_score=confidence,
            strengths=["回答与题目相关，具备基础表达"],
            weaknesses=["关键原理和项目细节仍可补充"],
            suggestions=["先补齐核心概念，再使用 STAR 结构组织回答"],
            need_followup=need_followup,
            followup_question=(
                "你能结合一个具体项目，展开说明关键原理、实现细节和取舍吗？"
                if need_followup
                else ""
            ),
        ).model_dump()

