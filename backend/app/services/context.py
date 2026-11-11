from __future__ import annotations

from typing import Any, Dict, List

from app.core.context_budget import ContextBudget
from app.infrastructure.rag import KnowledgeRetriever
from app.repositories.question import QuestionRepository
from app.services.question import QuestionService


class ContextService:
    def __init__(
        self,
        question_service: QuestionService | None = None,
        question_repository: QuestionRepository | None = None,
        retriever: KnowledgeRetriever | None = None,
        budget: ContextBudget | None = None,
    ) -> None:
        self.question_service = question_service or QuestionService()
        self.question_repository = question_repository or QuestionRepository()
        self.retriever = retriever or KnowledgeRetriever()
        self.budget = budget or ContextBudget()

    def build_reference_context(
        self,
        role_code: str,
        question: Dict[str, Any],
        answer_text: str,
    ) -> Dict[str, Any]:
        query = "\n".join(
            [
                f"题目：{question.get('title', '')}",
                f"评分要点：{question.get('scoring_points', '')}",
                f"候选人回答：{answer_text[:2000]}",
            ]
        )
        vector_hits = self.retriever.retrieve(role_code, query)
        keywords = self.question_service.extract_keywords(question, answer_text)
        chunks = self.question_repository.get_knowledge_chunks(
            role_code, keywords, limit=6
        )
        docs = self.question_repository.get_knowledge_docs(
            role_code, keywords, limit=2
        )

        candidates: List[str] = []
        traces: List[Dict[str, Any]] = []
        for hit in vector_hits:
            title = f"《{hit.title}》" if hit.title else ""
            candidates.append(
                f"向量召回{title}，相关度 {hit.score:.3f}：{hit.text}"
            )
            traces.append(
                {
                    "type": "vector",
                    "source_id": hit.source_id,
                    "source_table": hit.source_table,
                    "score": hit.score,
                }
            )
        for item in chunks:
            candidates.append(f"关键词知识片段：{item.get('chunk_text', '')}")
            traces.append({"type": "keyword_chunk", "source_id": item.get("id")})
        for item in docs:
            candidates.append(
                f"关键词文档《{item.get('title', '')}》：{item.get('content', '')}"
            )
            traces.append({"type": "keyword_doc", "source_id": item.get("id")})

        if question.get("reference_answer"):
            candidates.append(f"参考答案：{question['reference_answer']}")
        if question.get("scoring_points"):
            candidates.append(f"评分要点：{question['scoring_points']}")
        if question.get("followup_points"):
            candidates.append(f"建议追问点：{question['followup_points']}")

        deduplicated: List[str] = []
        seen = set()
        for item in candidates:
            if item not in seen:
                seen.add(item)
                deduplicated.append(item)

        return {
            "contexts": self.budget.pack(deduplicated),
            "raw_contexts": deduplicated,
            "retrieval_trace": traces,
            "keywords": keywords,
        }

