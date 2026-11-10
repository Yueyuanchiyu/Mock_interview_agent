from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.infrastructure.db import get_conn  # noqa: E402


def load_knowledge_rows() -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
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
                documents.append(
                    {
                        "id": f"doc_{row['id']}",
                        "document": f"知识文档《{title}》：{content}",
                        "metadata": {
                            "source_table": "knowledge_doc",
                            "source_id": row["id"],
                            "role_code": row["role_code"],
                            "title": title,
                        },
                    }
                )

            cursor.execute(
                """
                SELECT id, doc_id, role_code, chunk_text, keywords
                FROM knowledge_chunk
                """
            )
            for row in cursor.fetchall():
                text = (row.get("chunk_text") or "").strip()
                if not text:
                    continue
                documents.append(
                    {
                        "id": f"chunk_{row['id']}",
                        "document": text,
                        "metadata": {
                            "source_table": "knowledge_chunk",
                            "source_id": row["id"],
                            "doc_id": row.get("doc_id"),
                            "role_code": row["role_code"],
                            "title": row.get("keywords") or "",
                        },
                    }
                )
    return documents


def main() -> None:
    settings.vector_db_path.mkdir(parents=True, exist_ok=True)
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model_name
    )
    client = chromadb.PersistentClient(path=str(settings.vector_db_path))
    try:
        client.delete_collection(settings.vector_collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=settings.vector_collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    rows = load_knowledge_rows()
    for index in range(0, len(rows), 100):
        batch = rows[index : index + 100]
        collection.add(
            ids=[item["id"] for item in batch],
            documents=[item["document"] for item in batch],
            metadatas=[item["metadata"] for item in batch],
        )
    print(f"索引构建完成：{len(rows)} 条，目录：{settings.vector_db_path}")


if __name__ == "__main__":
    main()

