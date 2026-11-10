from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings
from app.core.logging import Logger


logger = Logger.get_logger(__name__)


@dataclass(slots=True)
class RetrievalHit:
    text: str
    score: float
    source_id: str
    title: str
    source_table: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeRetriever:
    def __init__(self) -> None:
        self._collection = None

    def _get_collection(self):
        if not settings.enable_vector_rag:
            return None
        if self._collection is not None:
            return self._collection
        if not settings.vector_db_path.exists():
            logger.warning("向量库目录不存在，RAG 将降级为关键词召回")
            return None

        try:
            embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name=settings.embedding_model_name
            )
            client = chromadb.PersistentClient(path=str(settings.vector_db_path))
            self._collection = client.get_collection(
                name=settings.vector_collection_name,
                embedding_function=embedding_fn,
            )
            return self._collection
        except Exception as exc:
            logger.warning("向量库不可用，RAG 将降级为关键词召回: %s", exc)
            return None

    def retrieve(
        self,
        role_code: str,
        query: str,
        limit: int | None = None,
    ) -> List[RetrievalHit]:
        collection = self._get_collection()
        if collection is None or not query.strip():
            return []

        try:
            result = collection.query(
                query_texts=[query],
                n_results=limit or settings.rag_top_k,
                where={"role_code": role_code},
            )
        except Exception as exc:
            logger.warning("向量检索失败，继续使用关键词召回: %s", exc)
            return []

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        hits: List[RetrievalHit] = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            text = (document or "").strip()
            if not text:
                continue
            meta = metadata or {}
            try:
                score = 1.0 / (1.0 + float(distance))
            except Exception:
                score = 0.0
            hits.append(
                RetrievalHit(
                    text=text,
                    score=round(score, 4),
                    source_id=str(meta.get("source_id", "")),
                    title=str(meta.get("title", "")),
                    source_table=str(meta.get("source_table", "")),
                )
            )
        return hits

