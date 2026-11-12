from __future__ import annotations

from typing import List

import dashscope
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings


class CloudEmbeddingFunction(EmbeddingFunction):
    """阿里云百炼（DashScope）云端 Embedding，替代本地 BGE 模型。"""

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
        response = dashscope.TextEmbedding.call(
            model=self.model,
            input=texts,
            api_key=self.api_key,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"云端 Embedding 失败: code={response.code} message={response.message}"
            )
        items = sorted(
            response.output["embeddings"],
            key=lambda item: item["text_index"],
        )
        return [item["embedding"] for item in items]

    @staticmethod
    def _extract_text(document) -> str:
        content = getattr(document, "get_content", None)
        if callable(content):
            return str(content())
        return str(document)
