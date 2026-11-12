from __future__ import annotations

from typing import List

import dashscope
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class CloudEmbeddingFunction(EmbeddingFunction):
    """阿里云百炼（DashScope）云端 Embedding，替代本地 BGE 模型。"""

    _BATCH_SIZE = 10

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        if base_url:
            dashscope.base_http_api_url = base_url

    def __call__(self, input: Documents) -> Embeddings:
        texts = [
            item if isinstance(item, str) else self._extract_text(item)
            for item in input
        ]
        embeddings: Embeddings = []
        for start in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[start : start + self._BATCH_SIZE]
            response = dashscope.TextEmbedding.call(
                model=self.model,
                input=batch,
                api_key=self.api_key,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"云端 Embedding 失败: code={response.code} message={response.message}"
                )
            items = sorted(
                response.output["embeddings"],
                key=lambda item: item["index"],
            )
            embeddings.extend([item["embedding"] for item in items])
        return embeddings

    @staticmethod
    def _extract_text(document) -> str:
        content = getattr(document, "get_content", None)
        if callable(content):
            return str(content())
        return str(document)
