from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, Callable, Dict, List, Sequence

from langchain_core.messages import BaseMessage

from app.core.config import settings
from app.core.context_budget import ContextBudget
from app.core.logging import Logger
from app.infrastructure.llm import get_chat_model


logger = Logger.get_logger(__name__)

_metrics: Dict[str, int] = {
    "calls": 0,
    "fallbacks": 0,
    "total_latency_ms": 0,
}


def get_metrics() -> Dict[str, int]:
    return dict(_metrics)


def _memory_context(profile: Dict[str, Any], role_code: str) -> str:
    role_memory = (profile.get("roles") or {}).get(role_code) or {}
    weaknesses = role_memory.get("recurring_weaknesses") or []
    if not weaknesses:
        return ""
    return "长期记忆中的重复薄弱点：" + "、".join(str(item) for item in weaknesses[-6:])


async def prepare_context(
    memory_profile: Dict[str, Any],
    role_code: str,
    context_items: List[str],
) -> List[str]:
    """before_model：注入长期记忆，超预算时先摘要再裁剪。"""
    items = list(context_items or [])
    mem = _memory_context(memory_profile, role_code)
    if mem:
        items = [mem, *items]

    budget = ContextBudget(settings.context_max_tokens)
    if not settings.enable_context_compression:
        return budget.pack(items)

    total = sum(budget.estimate_tokens(item) for item in items)
    if total <= settings.context_compression_trigger_tokens:
        return budget.pack(items)

    reserved = settings.context_compression_trigger_tokens
    kept: List[str] = []
    overflow: List[str] = []
    acc = 0
    for item in items:
        est = budget.estimate_tokens(item)
        if acc + est <= reserved:
            kept.append(item)
            acc += est
        else:
            overflow.append(item)

    summary = await _summarize(overflow)
    if summary:
        kept = [f"历史上下文摘要：{summary}", *kept]
    return budget.pack(kept)


async def _summarize(overflow: List[str]) -> str:
    if not overflow:
        return ""
    text = ContextBudget(settings.context_compression_trigger_tokens).trim(
        "\n\n".join(overflow)
    )
    try:
        model = get_chat_model(thinking=False)
        response = await model.ainvoke(
            "请把下面这些面试上下文压缩成一段不超过 300 字的中文摘要，"
            "保留与评分、追问、改进建议相关的关键信息：\n\n" + text
        )
        return str(response.content).strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("上下文摘要失败，回退为截断: %s", exc)
        return ""


async def invoke_structured(
    schema: type,
    messages: Sequence[BaseMessage],
    *,
    thinking: bool = True,
    fallback: Callable[[], Any | Awaitable[Any]],
) -> Any:
    """after_model：统一结构化调用、失败降级与观测。"""
    start = time.perf_counter()
    _metrics["calls"] += 1
    try:
        model = get_chat_model(thinking=thinking).with_structured_output(schema)
        result = await model.ainvoke(list(messages))
        _metrics["total_latency_ms"] += int((time.perf_counter() - start) * 1000)
        return result
    except Exception as exc:  # noqa: BLE001
        _metrics["fallbacks"] += 1
        _metrics["total_latency_ms"] += int((time.perf_counter() - start) * 1000)
        logger.warning("LLM 结构化调用失败，使用规则降级: %s", exc)
        value = fallback()
        if inspect.isawaitable(value):
            value = await value
        return value
