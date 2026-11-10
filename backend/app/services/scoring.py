from __future__ import annotations

from typing import Any, Dict, List


def build_score_summary(rounds: List[Dict[str, Any]]) -> Dict[str, float]:
    answered = [item for item in rounds if (item.get("answer_text") or "").strip()]
    if not answered:
        return {
            "technical_score": 0,
            "depth_score": 0,
            "logic_score": 0,
            "role_match_score": 0,
            "speech_rate_score": 0,
            "clarity_score": 0,
            "confidence_score": 0,
            "total_score": 0,
        }

    keys = [
        "technical_score",
        "depth_score",
        "logic_score",
        "role_match_score",
        "speech_rate_score",
        "clarity_score",
        "confidence_score",
    ]
    result = {
        key: round(
            sum(float(item.get(key) or 0) for item in answered) / len(answered),
            2,
        )
        for key in keys
    }
    result["total_score"] = round(
        (
            result["technical_score"]
            + result["depth_score"]
            + result["logic_score"]
            + result["role_match_score"]
        )
        / 4,
        2,
    )
    return result

