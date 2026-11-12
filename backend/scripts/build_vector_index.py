from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.infrastructure.embedding import CloudEmbeddingFunction  # noqa: E402


DOCUMENTS_FILE = BACKEND_ROOT / "data" / "documents.jsonl"

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80
SEPARATORS = [
    "\n\n", "\n", "。", "！", "？", "；",
    ".", "!", "?", "，", ",", " ", "",
]


def load_documents() -> List[Document]:
    documents: List[Document] = []
    with open(DOCUMENTS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            documents.append(
                Document(
                    page_content=obj["page_content"],
                    metadata=obj.get("metadata") or {},
                )
            )
    return documents


def split_documents(
    documents: List[Document],
) -> List[Tuple[str, str, Dict[str, Any]]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
    )
    chunks: List[Tuple[str, str, Dict[str, Any]]] = []
    for doc in documents:
        source_table = str(doc.metadata.get("source_table", ""))
        source_id = str(doc.metadata.get("source_id", ""))
        doc_type = str(doc.metadata.get("type", ""))
        for index, text in enumerate(splitter.split_text(doc.page_content)):
            text = text.strip()
            if not text:
                continue
            metadata = {k: v for k, v in doc.metadata.items() if v is not None}
            metadata["chunk_index"] = index
            chunk_id = f"{source_table}:{source_id}:{doc_type}:{index}"
            chunks.append((chunk_id, text, metadata))
    return chunks


def main() -> None:
    settings.vector_db_path.mkdir(parents=True, exist_ok=True)
    embedding_fn = CloudEmbeddingFunction(
        api_key=settings.embedding_api_key,
        model=settings.embedding_model_name,
        base_url=settings.embedding_api_base,
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
    documents = load_documents()
    chunks = split_documents(documents)
    for start in range(0, len(chunks), 100):
        batch = chunks[start : start + 100]
        collection.add(
            ids=[item[0] for item in batch],
            documents=[item[1] for item in batch],
            metadatas=[item[2] for item in batch],
        )
    print(
        f"索引构建完成：文档 {len(documents)} 条，切块 {len(chunks)} 条，"
        f"目录：{settings.vector_db_path}"
    )


if __name__ == "__main__":
    main()

