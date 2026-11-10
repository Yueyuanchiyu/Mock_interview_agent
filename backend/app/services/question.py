from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.core.exceptions import DomainError
from app.repositories.question import QuestionRepository
from app.repositories.resource import ResourceRepository


class QuestionService:
    def __init__(
        self,
        repository: QuestionRepository | None = None,
        resource_repository: ResourceRepository | None = None,
    ) -> None:
        self.repository = repository or QuestionRepository()
        self.resource_repository = resource_repository or ResourceRepository()

    def get_role_name(self, role_code: str) -> str:
        role_name = self.repository.get_role_name(role_code)
        if not role_name:
            raise DomainError(
                f"岗位 {role_code} 不存在",
                status_code=404,
                error_code="ROLE_NOT_FOUND",
            )
        return role_name

    def pick_question(
        self,
        role_code: str,
        exclude_ids: Optional[List[int]] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.repository.get_random_question(role_code, exclude_ids or [])

    def require_question(self, question_id: int) -> Dict[str, Any]:
        question = self.repository.get_question_by_id(question_id)
        if not question:
            raise DomainError(
                "题库数据不存在",
                status_code=404,
                error_code="QUESTION_NOT_FOUND",
            )
        return question

    def search_learning_resources(
        self,
        role_code: str,
        keywords: List[str],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        return self.resource_repository.search(role_code, keywords, limit)

    @staticmethod
    def extract_keywords(question: Dict[str, Any], answer_text: str) -> List[str]:
        text = " ".join(
            str(question.get(key, "") or "")
            for key in ("tags", "question_type", "title", "scoring_points", "followup_points")
        )
        text += " " + answer_text[:2000]
        parts = re.split(r"[，,。；;：:\n\t、()（）/\\\-| ]+", text)
        stop_words = {
            "请", "一下", "以及", "如何", "什么", "这个", "一个", "进行",
            "说明", "项目", "问题", "场景", "能力", "模块",
        }
        result: List[str] = []
        seen = set()
        for part in parts:
            word = part.strip()
            key = word.lower()
            if len(word) < 2 or word in stop_words or key in seen:
                continue
            seen.add(key)
            result.append(word)
        return result[:12]

