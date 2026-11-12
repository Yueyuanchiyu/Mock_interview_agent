from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.infrastructure.db import get_conn  # noqa: E402


OUTPUT = BACKEND_ROOT / "data" / "documents.jsonl"


def _doc(content: str, metadata: dict) -> dict:
    return {"page_content": content, "metadata": metadata}


def export() -> list[dict]:
    documents: list[dict] = []
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, role_code, title, content, tags FROM knowledge_doc"
            )
            for row in cursor.fetchall():
                content = (row.get("content") or "").strip()
                if not content:
                    continue
                title = (row.get("title") or "").strip()
                page = f"《{title}》\n{content}" if title else content
                documents.append(
                    _doc(
                        page,
                        {
                            "role_code": row["role_code"],
                            "source_table": "knowledge_doc",
                            "source_id": row["id"],
                            "title": title,
                            "type": "knowledge",
                        },
                    )
                )

            cursor.execute(
                """
                SELECT id, doc_id, role_code, chunk_index, chunk_text, keywords
                FROM knowledge_chunk
                """
            )
            for row in cursor.fetchall():
                text = (row.get("chunk_text") or "").strip()
                if not text:
                    continue
                documents.append(
                    _doc(
                        text,
                        {
                            "role_code": row["role_code"],
                            "source_table": "knowledge_chunk",
                            "source_id": row["id"],
                            "doc_id": row.get("doc_id"),
                            "chunk_index": row.get("chunk_index"),
                            "keywords": row.get("keywords") or "",
                            "type": "knowledge",
                        },
                    )
                )

            cursor.execute(
                """
                SELECT id, role_code, question_type, difficulty, title,
                       reference_answer, scoring_points, followup_points, tags
                FROM question_bank
                """
            )
            for row in cursor.fetchall():
                base = {
                    "role_code": row["role_code"],
                    "source_table": "question_bank",
                    "source_id": row["id"],
                    "difficulty": row.get("difficulty"),
                    "question_type": row.get("question_type") or "",
                    "tags": row.get("tags") or "",
                }
                for field, typ in (
                    ("title", "question"),
                    ("scoring_points", "scoring"),
                    ("reference_answer", "reference"),
                    ("followup_points", "followup"),
                ):
                    content = (row.get(field) or "").strip()
                    if not content:
                        continue
                    metadata = {**base, "type": typ}
                    if typ == "question":
                        metadata["title"] = content
                    documents.append(_doc(content, metadata))
    return documents


def main() -> None:
    documents = export()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for doc in documents:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"导出完成：{len(documents)} 条 -> {OUTPUT}")


if __name__ == "__main__":
    main()
