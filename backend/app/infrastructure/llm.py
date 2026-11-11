from __future__ import annotations

from typing import Any

from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


_model_cache: dict[bool, ChatDeepSeek] = {}


def get_chat_model(thinking: bool | None = None) -> ChatDeepSeek:
    """获取 DeepSeek 聊天模型。

    thinking=None 时使用全局配置 DEEPSEEK_THINKING；
    True 开启思考模式（评分/总结等重质量场景，DeepSeek 默认即开启），
    False 关闭思考模式（追问/工具调用等低延迟场景）。
    """
    key = settings.deepseek_thinking if thinking is None else thinking
    if key not in _model_cache:
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置")

        kwargs: dict[str, Any] = {
            "model": settings.deepseek_model,
            "api_key": settings.deepseek_api_key,
            "temperature": settings.llm_temperature,
            "timeout": settings.llm_timeout_seconds,
            "max_retries": 2,
            "streaming": False,
        }
        if settings.deepseek_api_base:
            kwargs["base_url"] = settings.deepseek_api_base
        if not key:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        _model_cache[key] = ChatDeepSeek(**kwargs)
    return _model_cache[key]

