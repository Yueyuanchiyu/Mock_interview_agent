from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from docx import Document

from app.core.config import settings
from app.services.evaluation import EvaluationService
from app.services.scoring import build_score_summary


class ReportService:
    def __init__(self, evaluator: EvaluationService | None = None) -> None:
        self.evaluator = evaluator or EvaluationService()

    @staticmethod
    def build_score_summary(rounds: List[Dict[str, Any]]) -> Dict[str, float]:
        return build_score_summary(rounds)

    async def build_payload(
        self,
        role_name: str,
        rounds: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        score_summary = self.build_score_summary(rounds)
        summary = await self.evaluator.generate_summary(
            role_name, rounds, recommendations
        )
        return {
            "role_name": role_name,
            "score_summary": score_summary,
            "rounds": rounds,
            "recommendations": recommendations,
            "summary": summary,
        }

    def export_docx(self, payload: Dict[str, Any]) -> str:
        document = Document()
        document.add_heading("AI 模拟面试分析报告", 0)
        document.add_paragraph(f"目标岗位：{payload.get('role_name', '')}")

        score = payload.get("score_summary", {})
        document.add_heading("一、维度评分", level=1)
        document.add_paragraph(
            f"技术正确性：{score.get('technical_score', 0)}\n"
            f"知识深度：{score.get('depth_score', 0)}\n"
            f"逻辑严谨性：{score.get('logic_score', 0)}\n"
            f"岗位匹配度：{score.get('role_match_score', 0)}\n"
            f"表达语速：{score.get('speech_rate_score', 0)}\n"
            f"表达清晰度：{score.get('clarity_score', 0)}\n"
            f"表达自信度：{score.get('confidence_score', 0)}\n"
            f"综合分：{score.get('total_score', 0)}"
        )

        document.add_heading("二、逐题分析", level=1)
        for item in payload.get("rounds", []):
            if not (item.get("answer_text") or "").strip():
                continue
            document.add_heading(f"第{item.get('question_no')}题", level=2)
            document.add_paragraph(f"题目：{item.get('question_text', '')}")
            document.add_paragraph(f"回答：{item.get('answer_text', '')}")
            for turn in item.get("followup_turns", []):
                document.add_paragraph(
                    f"追问{turn.get('followup_no')}：{turn.get('question_text', '')}"
                )
                document.add_paragraph(
                    f"追问回答{turn.get('followup_no')}：{turn.get('answer_text') or '无'}"
                )
            document.add_paragraph(f"亮点：{item.get('strengths', '')}")
            document.add_paragraph(f"不足：{item.get('weaknesses', '')}")
            document.add_paragraph(f"建议：{item.get('suggestions', '')}")

        document.add_heading("三、综合总结", level=1)
        document.add_paragraph(payload.get("summary", ""))

        document.add_heading("四、推荐学习资源", level=1)
        for resource in payload.get("recommendations", []):
            text = resource.get("title", "")
            if resource.get("content"):
                text += f"\n{resource['content']}"
            if resource.get("reason"):
                text += f"\n推荐原因：{resource['reason']}"
            if resource.get("link"):
                text += f"\n链接：{resource['link']}"
            document.add_paragraph(text)

        filename = f"{uuid.uuid4().hex}_report.docx"
        path = settings.download_dir / filename
        document.save(path)
        return f"{settings.report_base_url}/static/download/{filename}"

    @staticmethod
    def to_json(payload: Dict[str, Any]) -> str:
        return json.dumps(_normalize(payload), ensure_ascii=False)


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    return value

