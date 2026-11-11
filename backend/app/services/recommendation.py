from __future__ import annotations

import re
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm_guard import invoke_structured
from app.agent.prompts import RESOURCE_SYSTEM_PROMPT, resource_prompt
from app.core.logging import Logger
from app.repositories.resource import ResourceRepository
from app.schemas.llm import ResourceSelection
from app.services.question import QuestionService


logger = Logger.get_logger(__name__)


class RecommendationService:
    def __init__(
        self,
        question_service: QuestionService | None = None,
        resource_repository: ResourceRepository | None = None,
    ) -> None:
        self.question_service = question_service or QuestionService()
        self.resource_repository = resource_repository or ResourceRepository()

    async def get_recommendations(
        self,
        role_code: str,
        rounds: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        keywords = self.extract_weakness_keywords(rounds)
        candidates = self.question_service.search_learning_resources(
            role_code, keywords, limit=10
        )
        if not candidates:
            return []
        role_name = self.question_service.get_role_name(role_code)
        prompt = resource_prompt(role_name, keywords, candidates)
        selection = await invoke_structured(
            ResourceSelection,
            [
                SystemMessage(content=RESOURCE_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ],
            thinking=True,
            fallback=lambda: ResourceSelection(resources=[]),
        )
        choices = [item.model_dump() for item in selection.resources]
        if not choices:
            return self._fallback(candidates, keywords)
        return self._merge(candidates, choices)

    @staticmethod
    def extract_weakness_keywords(rounds: List[Dict[str, Any]]) -> List[str]:
        tokens: List[str] = []
        stop_words = {
            "回答", "说明", "问题", "能力", "项目", "场景", "模块", "这个",
            "一个", "不足", "需要", "继续", "加强", "分析", "当前", "主要",
        }
        for item in rounds:
            low_score = any(
                float(item.get(field) or 0) < 7
                for field in (
                    "technical_score",
                    "depth_score",
                    "logic_score",
                    "role_match_score",
                )
            )
            if not low_score:
                continue
            text = f"{item.get('weaknesses') or ''} {item.get('question_text') or ''}"
            tokens.extend(
                part.strip()
                for part in re.split(r"[，,。；;：:\n\t、()（）/\\\-| ]+", text)
                if part.strip()
            )

        result: List[str] = []
        seen = set()
        for token in tokens:
            key = token.lower()
            if len(token) < 2 or token in stop_words or key in seen:
                continue
            seen.add(key)
            result.append(token)
        return result[:10] or ["基础", "原理", "项目表达"]

    @staticmethod
    def _merge(
        candidates: List[Dict[str, Any]],
        choices: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        resource_map = {int(item["id"]): item for item in candidates}
        merged: List[Dict[str, Any]] = []
        used = set()
        for choice in choices:
            resource_id = int(choice.get("id", 0))
            if resource_id not in resource_map or resource_id in used:
                continue
            used.add(resource_id)
            item = dict(resource_map[resource_id])
            item["reason"] = str(choice.get("reason", "")).strip()
            item["priority"] = int(choice.get("priority", 99))
            merged.append(item)
        merged.sort(key=lambda item: item["priority"])
        return merged[:5]

    @staticmethod
    def _fallback(
        candidates: List[Dict[str, Any]],
        keywords: List[str],
    ) -> List[Dict[str, Any]]:
        result = []
        for index, item in enumerate(candidates[:5], start=1):
            enriched = dict(item)
            enriched["reason"] = (
                f"该资源与当前薄弱点（{'、'.join(keywords[:3])}）相关。"
            )
            enriched["priority"] = index
            result.append(enriched)
        return result

