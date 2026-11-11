from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from app.agent.llm_guard import prepare_context
from app.agent.memory import AgentMemoryStore
from app.agent.resource_agent import ResourceAdvisorAgent
from app.agent.state import InterviewState
from app.agent.tools import AgentToolFactory
from app.core.config import settings
from app.core.exceptions import DomainError
from app.repositories.interview import InterviewRepository
from app.repositories.resource import ResourceRepository
from app.services.context import ContextService
from app.services.evaluation import EvaluationService
from app.services.question import QuestionService
from app.services.recommendation import RecommendationService
from app.services.report import ReportService


class InterviewAgentWorkflow:
    def __init__(self, checkpointer: BaseCheckpointSaver) -> None:
        self.interview_repository = InterviewRepository()
        self.resource_repository = ResourceRepository()
        self.question_service = QuestionService(
            resource_repository=self.resource_repository
        )
        self.context_service = ContextService(question_service=self.question_service)
        self.evaluator = EvaluationService()
        self.recommendation_service = RecommendationService(
            question_service=self.question_service,
            resource_repository=self.resource_repository,
        )
        self.report_service = ReportService(self.evaluator)
        self.memory_store = AgentMemoryStore()
        tool_factory = AgentToolFactory(
            self.question_service,
            self.interview_repository,
            self.context_service,
        )
        self.resource_agent = ResourceAdvisorAgent(tool_factory)
        self.graph = self._compile(checkpointer)

    def _compile(self, checkpointer: BaseCheckpointSaver):
        graph = StateGraph(InterviewState)
        graph.add_node("start", self._start)
        graph.add_node("answer", self._answer)
        graph.add_node("followup", self._followup)
        graph.add_node("next", self._next)
        graph.add_node("finish", self._finish)
        graph.add_conditional_edges(
            START,
            self._route,
            {
                "start": "start",
                "answer": "answer",
                "followup": "followup",
                "next": "next",
                "finish": "finish",
            },
        )
        for node in ("start", "answer", "followup", "next", "finish"):
            graph.add_edge(node, END)
        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def _route(state: InterviewState) -> str:
        action = state.get("action")
        if action not in {"start", "answer", "followup", "next", "finish"}:
            raise DomainError("未知 Agent 动作", status_code=400)
        return action

    async def start(
        self,
        user_key: str,
        role_code: str,
        question_count: int,
    ) -> Dict[str, Any]:
        return await self._invoke(
            {
                "action": "start",
                "user_key": user_key,
                "role_code": role_code,
                "question_count": question_count,
            },
            thread_id=f"start:{user_key}:{uuid.uuid4().hex}",
        )

    async def answer(
        self,
        user_key: str,
        session_id: int,
        question_no: int,
        answer_text: str,
        expression_metrics: Dict[str, Any] | None,
    ) -> Dict[str, Any]:
        return await self._invoke(
            {
                "action": "answer",
                "user_key": user_key,
                "session_id": session_id,
                "question_no": question_no,
                "answer_text": answer_text,
                "expression_metrics": expression_metrics or {"input_mode": "text"},
            },
            thread_id=self._thread_id(session_id),
        )

    async def followup(
        self,
        user_key: str,
        session_id: int,
        question_no: int,
        followup_no: int,
        followup_answer: str,
    ) -> Dict[str, Any]:
        return await self._invoke(
            {
                "action": "followup",
                "user_key": user_key,
                "session_id": session_id,
                "question_no": question_no,
                "followup_no": followup_no,
                "followup_answer": followup_answer,
            },
            thread_id=self._thread_id(session_id),
        )

    async def next_question(
        self,
        user_key: str,
        session_id: int,
    ) -> Dict[str, Any]:
        return await self._invoke(
            {
                "action": "next",
                "user_key": user_key,
                "session_id": session_id,
            },
            thread_id=self._thread_id(session_id),
        )

    async def finish(
        self,
        user_key: str,
        session_id: int,
    ) -> Dict[str, Any]:
        return await self._invoke(
            {
                "action": "finish",
                "user_key": user_key,
                "session_id": session_id,
            },
            thread_id=self._thread_id(session_id),
        )

    async def _invoke(
        self,
        state: Dict[str, Any],
        thread_id: str,
    ) -> Dict[str, Any]:
        config = {"configurable": {"thread_id": thread_id}}
        result = await self.graph.ainvoke(state, config=config)
        return _normalize(result.get("result") or {})

    async def _start(self, state: InterviewState) -> Dict[str, Any]:
        user_key = state["user_key"]
        role_code = state["role_code"]
        question_count = int(state.get("question_count") or 3)
        role_name = await asyncio.to_thread(
            self.question_service.get_role_name, role_code
        )
        history_ids = await asyncio.to_thread(
            self.interview_repository.get_user_used_question_ids,
            user_key,
            role_code,
            200,
        )
        question = await asyncio.to_thread(
            self.question_service.pick_question, role_code, history_ids
        )
        if not question:
            question = await asyncio.to_thread(
                self.question_service.pick_question, role_code, []
            )
        if not question:
            raise DomainError(
                "当前岗位暂无可用题目，请先导入题库",
                status_code=409,
                error_code="QUESTION_BANK_EMPTY",
            )

        session_id = await asyncio.to_thread(
            self.interview_repository.create_session,
            user_key,
            role_code,
            question_count,
        )
        await asyncio.to_thread(
            self.interview_repository.create_round,
            session_id,
            1,
            int(question["id"]),
            str(question["title"]),
        )
        profile = await asyncio.to_thread(self.memory_store.load_profile, user_key)
        question_view = _question_view(question)
        result = {
            "session_id": session_id,
            "role_code": role_code,
            "role_name": role_name,
            "question_no": 1,
            "question": question_view,
        }
        return {
            "session_id": session_id,
            "role_name": role_name,
            "question_no": 1,
            "question": question_view,
            "long_term_memory": profile,
            "result": result,
        }

    async def _answer(self, state: InterviewState) -> Dict[str, Any]:
        user_key = state["user_key"]
        session_id = int(state["session_id"])
        question_no = int(state["question_no"])
        answer_text = state["answer_text"].strip()
        metrics = state.get("expression_metrics") or {"input_mode": "text"}

        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)
        if session["status"] != "in_progress":
            raise DomainError("面试已经结束", status_code=409, error_code="SESSION_FINISHED")
        if int(session["current_question_no"]) != question_no:
            raise DomainError(
                "提交的题号不是当前题",
                status_code=409,
                error_code="QUESTION_OUT_OF_ORDER",
            )
        current_round = await asyncio.to_thread(
            self.interview_repository.get_round, session_id, question_no
        )
        if not current_round:
            raise DomainError(
                "当前题目不存在",
                status_code=404,
                error_code="ROUND_NOT_FOUND",
            )

        if (
            current_round.get("answer_text")
            and str(current_round["answer_text"]).strip() == answer_text
        ):
            return {
                "result": await self._existing_answer_result(
                    session, current_round
                )
            }

        question = await asyncio.to_thread(
            self.question_service.require_question,
            int(current_round["question_id"]),
        )
        role_name = await asyncio.to_thread(
            self.question_service.get_role_name, session["role_code"]
        )
        long_term_memory = await asyncio.to_thread(
            self.memory_store.load_profile, user_key
        )
        context = await asyncio.to_thread(
            self.context_service.build_reference_context,
            session["role_code"],
            question,
            answer_text,
        )
        contexts = await prepare_context(
            long_term_memory, session["role_code"], context["raw_contexts"]
        )
        analysis = await self.evaluator.evaluate_answer(
            role_name,
            question,
            answer_text,
            contexts,
            metrics,
        )
        followup_question = str(analysis.get("followup_question") or "").strip()
        need_followup = bool(analysis.get("need_followup")) and bool(followup_question)
        analysis["need_followup"] = need_followup
        analysis["followup_question"] = followup_question if need_followup else ""

        await asyncio.to_thread(
            self.interview_repository.update_round_analysis,
            session_id,
            question_no,
            answer_text,
            analysis,
        )
        if need_followup:
            await asyncio.to_thread(
                self.interview_repository.create_followup_turn,
                session_id,
                question_no,
                1,
                followup_question,
            )

        result = {
            "session_id": session_id,
            "question_no": question_no,
            "need_followup": need_followup,
            "followup_no": 1 if need_followup else 0,
            "followup_question": followup_question if need_followup else "",
            "round_analysis": analysis,
        }
        return {
            "analysis": analysis,
            "context_items": contexts,
            "retrieval_trace": context["retrieval_trace"],
            "long_term_memory": long_term_memory,
            "result": result,
        }

    async def _followup(self, state: InterviewState) -> Dict[str, Any]:
        user_key = state["user_key"]
        session_id = int(state["session_id"])
        question_no = int(state["question_no"])
        followup_no = int(state["followup_no"])
        latest_answer = state["followup_answer"].strip()

        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)
        current_round = await asyncio.to_thread(
            self.interview_repository.get_round, session_id, question_no
        )
        if not current_round:
            raise DomainError("当前题目不存在", status_code=404, error_code="ROUND_NOT_FOUND")
        turns = await asyncio.to_thread(
            self.interview_repository.list_followup_turns, session_id, question_no
        )
        current_turn = next(
            (item for item in turns if int(item["followup_no"]) == followup_no),
            None,
        )
        if not current_turn:
            raise DomainError(
                "追问序号不存在",
                status_code=409,
                error_code="FOLLOWUP_OUT_OF_ORDER",
            )

        await asyncio.to_thread(
            self.interview_repository.update_followup_answer,
            session_id,
            question_no,
            followup_no,
            latest_answer,
        )

        if followup_no >= settings.max_followup_depth:
            return {"result": self._followup_stop(session_id, question_no, followup_no, "已达到最大追问次数")}
        if any(
            phrase in latest_answer
            for phrase in ("不知道", "不会", "不清楚", "没了解", "不了解")
        ):
            return {"result": self._followup_stop(session_id, question_no, followup_no, "当前题继续追问收益较低")}

        question = await asyncio.to_thread(
            self.question_service.require_question,
            int(current_round["question_id"]),
        )
        role_name = await asyncio.to_thread(
            self.question_service.get_role_name, session["role_code"]
        )
        context = await asyncio.to_thread(
            self.context_service.build_reference_context,
            session["role_code"],
            question,
            latest_answer,
        )
        contexts = await prepare_context({}, session["role_code"], context["raw_contexts"])
        turns = await asyncio.to_thread(
            self.interview_repository.list_followup_turns, session_id, question_no
        )
        history = "\n".join(
            f"追问{item['followup_no']}：{item['question_text']}\n"
            f"回答：{item.get('answer_text') or ''}"
            for item in turns
        )
        next_question = await self.evaluator.generate_dynamic_followup(
            role_name,
            question,
            current_round.get("answer_text") or "",
            history,
            latest_answer,
            contexts,
        )
        if not next_question:
            return {"result": self._followup_stop(session_id, question_no, followup_no, "本题追问已结束")}

        next_no = followup_no + 1
        await asyncio.to_thread(
            self.interview_repository.create_followup_turn,
            session_id,
            question_no,
            next_no,
            next_question,
        )
        return {
            "context_items": context["contexts"],
            "retrieval_trace": context["retrieval_trace"],
            "result": {
                "session_id": session_id,
                "question_no": question_no,
                "need_followup": True,
                "followup_no": next_no,
                "followup_question": next_question,
                "message": "请继续回答追问",
            },
        }

    async def _next(self, state: InterviewState) -> Dict[str, Any]:
        user_key = state["user_key"]
        session_id = int(state["session_id"])
        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)
        current_no = int(session["current_question_no"])
        current_round = await asyncio.to_thread(
            self.interview_repository.get_round, session_id, current_no
        )
        if not current_round or not (current_round.get("answer_text") or "").strip():
            raise DomainError(
                "请先回答当前题目",
                status_code=409,
                error_code="QUESTION_NOT_ANSWERED",
            )
        turns = await asyncio.to_thread(
            self.interview_repository.list_followup_turns, session_id, current_no
        )
        if any(not (item.get("answer_text") or "").strip() for item in turns):
            raise DomainError(
                "请先回答当前追问",
                status_code=409,
                error_code="FOLLOWUP_NOT_ANSWERED",
            )

        total = int(session["total_questions"])
        if current_no >= total:
            return {"result": {"finished": True, "message": "题目已全部完成，请生成报告"}}

        used = await asyncio.to_thread(
            self.interview_repository.get_used_question_ids, session_id
        )
        history_used = await asyncio.to_thread(
            self.interview_repository.get_user_used_question_ids,
            user_key,
            session["role_code"],
            200,
        )
        excluded = list(dict.fromkeys(used + history_used))
        question = await asyncio.to_thread(
            self.question_service.pick_question, session["role_code"], excluded
        )
        if not question:
            question = await asyncio.to_thread(
                self.question_service.pick_question, session["role_code"], used
            )
        if not question:
            return {
                "result": {
                    "finished": True,
                    "message": "题库题目不足，请补充题库",
                }
            }

        next_no = current_no + 1
        await asyncio.to_thread(
            self.interview_repository.update_current_question, session_id, next_no
        )
        await asyncio.to_thread(
            self.interview_repository.create_round,
            session_id,
            next_no,
            int(question["id"]),
            str(question["title"]),
        )
        view = _question_view(question)
        return {
            "question_no": next_no,
            "question": view,
            "result": {
                "finished": False,
                "session_id": session_id,
                "question_no": next_no,
                "question": view,
            },
        }

    async def _finish(self, state: InterviewState) -> Dict[str, Any]:
        user_key = state["user_key"]
        session_id = int(state["session_id"])
        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)

        existing = await asyncio.to_thread(
            self.interview_repository.get_report, session_id
        )
        if existing and existing.get("report_json"):
            payload = json.loads(existing["report_json"])
            payload["report_docx_url"] = existing.get("report_docx_url", "")
            return {"result": _normalize(payload)}

        rounds = await asyncio.to_thread(
            self.interview_repository.list_rounds, session_id
        )
        for item in rounds:
            item["followup_turns"] = await asyncio.to_thread(
                self.interview_repository.list_followup_turns,
                session_id,
                int(item["question_no"]),
            )
        rounds = _normalize(rounds)
        if not any((item.get("answer_text") or "").strip() for item in rounds):
            raise DomainError(
                "至少回答一题后才能生成报告",
                status_code=409,
                error_code="NO_ANSWERS",
            )

        role_name = await asyncio.to_thread(
            self.question_service.get_role_name, session["role_code"]
        )
        recommendations = await self.recommendation_service.get_recommendations(
            session["role_code"], rounds
        )
        recommendations = _normalize(recommendations)
        payload = await self.report_service.build_payload(
            role_name, rounds, recommendations
        )
        report_url = await asyncio.to_thread(
            self.report_service.export_docx, payload
        )
        payload["report_docx_url"] = report_url
        total_score = payload["score_summary"]["total_score"]

        await asyncio.to_thread(
            self.interview_repository.finish_session, session_id, total_score
        )
        await asyncio.to_thread(
            self.interview_repository.save_report,
            session_id,
            payload["summary"],
            payload,
            report_url,
        )
        await asyncio.to_thread(
            self.resource_repository.save_recommendations,
            session_id,
            recommendations,
        )
        await asyncio.to_thread(
            self.memory_store.update_profile,
            user_key,
            session["role_code"],
            self.recommendation_service.extract_weakness_keywords(rounds),
            payload["summary"],
        )
        return {"result": payload}

    async def history(self, user_key: str) -> List[Dict[str, Any]]:
        rows = await asyncio.to_thread(
            self.interview_repository.list_history, user_key
        )
        return _normalize(rows)

    async def growth(self, user_key: str, role_code: str = "") -> Dict[str, Any]:
        rows = await asyncio.to_thread(
            self.interview_repository.get_growth,
            user_key,
            role_code or None,
        )
        rows = _normalize(rows)

        def values(key: str) -> List[float]:
            return [float(item.get(key) or 0) for item in rows]

        expressions = [
            round(
                (
                    float(item.get("speech_rate_score") or 0)
                    + float(item.get("clarity_score") or 0)
                    + float(item.get("confidence_score") or 0)
                )
                / 3,
                2,
            )
            for item in rows
        ]
        return {
            "user_key": user_key,
            "role_code": role_code,
            "labels": [str(item["start_time"])[:16] for item in rows],
            "scores": values("total_score"),
            "technical_scores": values("technical_score"),
            "depth_scores": values("depth_score"),
            "logic_scores": values("logic_score"),
            "role_match_scores": values("role_match_score"),
            "speech_rate_scores": values("speech_rate_score"),
            "clarity_scores": values("clarity_score"),
            "confidence_scores": values("confidence_score"),
            "expression_scores": expressions,
            "sessions": rows,
        }

    async def resource_advice(
        self,
        user_key: str,
        session_id: int,
        instruction: str,
    ) -> Dict[str, Any]:
        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)
        prompt = (
            f"当前用户：{user_key}\n"
            f"当前会话：{session_id}\n"
            f"岗位：{session['role_code']}\n"
            f"用户请求：{instruction}"
        )
        advice = await self.resource_agent.advise(prompt)
        return {"session_id": session_id, "advice": advice}

    async def state_snapshot(
        self,
        user_key: str,
        session_id: int,
    ) -> Dict[str, Any]:
        session = await asyncio.to_thread(
            self.interview_repository.get_session, session_id
        )
        self._validate_session(session, user_key)
        snapshot = await self.graph.aget_state(
            {"configurable": {"thread_id": self._thread_id(session_id)}}
        )
        values = getattr(snapshot, "values", {}) or {}
        safe_keys = {
            "action",
            "user_key",
            "session_id",
            "role_code",
            "role_name",
            "question_count",
            "question_no",
            "answer_text",
            "followup_no",
            "followup_answer",
            "question",
            "context_items",
            "retrieval_trace",
            "analysis",
            "long_term_memory",
            "result",
        }
        return _normalize(
            {key: value for key, value in values.items() if key in safe_keys}
        )

    async def _existing_answer_result(
        self,
        session: Dict[str, Any],
        current_round: Dict[str, Any],
    ) -> Dict[str, Any]:
        session_id = int(session["id"])
        question_no = int(current_round["question_no"])
        turns = await asyncio.to_thread(
            self.interview_repository.list_followup_turns,
            session_id,
            question_no,
        )
        pending = next(
            (item for item in turns if not (item.get("answer_text") or "").strip()),
            None,
        )
        analysis = {
            "technical_score": float(current_round.get("technical_score") or 0),
            "depth_score": float(current_round.get("depth_score") or 0),
            "logic_score": float(current_round.get("logic_score") or 0),
            "role_match_score": float(current_round.get("role_match_score") or 0),
            "speech_rate_score": float(current_round.get("speech_rate_score") or 0),
            "clarity_score": float(current_round.get("clarity_score") or 0),
            "confidence_score": float(current_round.get("confidence_score") or 0),
            "strengths": _lines(current_round.get("strengths")),
            "weaknesses": _lines(current_round.get("weaknesses")),
            "suggestions": _lines(current_round.get("suggestions")),
            "need_followup": pending is not None,
            "followup_question": pending["question_text"] if pending else "",
        }
        return {
            "session_id": session_id,
            "question_no": question_no,
            "need_followup": pending is not None,
            "followup_no": int(pending["followup_no"]) if pending else 0,
            "followup_question": pending["question_text"] if pending else "",
            "round_analysis": analysis,
        }

    @staticmethod
    def _validate_session(
        session: Dict[str, Any] | None,
        user_key: str,
    ) -> None:
        if not session or str(session["user_key"]) != str(user_key):
            raise DomainError(
                "面试会话不存在或无权访问",
                status_code=404,
                error_code="SESSION_NOT_FOUND",
            )

    @staticmethod
    def _thread_id(session_id: int) -> str:
        return f"session:{session_id}"

    @staticmethod
    def _followup_stop(
        session_id: int,
        question_no: int,
        followup_no: int,
        message: str,
    ) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "question_no": question_no,
            "need_followup": False,
            "followup_no": followup_no,
            "message": message,
        }


def _question_view(question: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": int(question["id"]),
        "title": str(question["title"]),
        "question_type": str(question.get("question_type") or ""),
        "difficulty": int(question.get("difficulty") or 1),
    }


def _lines(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [line for line in str(value or "").splitlines() if line.strip()]


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value

