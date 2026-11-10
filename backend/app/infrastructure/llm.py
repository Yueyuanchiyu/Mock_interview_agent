from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.core.config import settings


_model: ChatOpenAI | None = None


def get_chat_model() -> ChatOpenAI:
    global _model
    if _model is None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY 未配置")

        kwargs: dict[str, Any] = {
            "model": settings.model_name,
            "api_key": settings.openai_api_key,
            "temperature": settings.llm_temperature,
            "timeout": settings.llm_timeout_seconds,
            "max_retries": 2,
            "streaming": False,
        }
        if settings.openai_api_base:
            kwargs["base_url"] = settings.openai_api_base
        _model = ChatOpenAI(**kwargs)
    return _model

