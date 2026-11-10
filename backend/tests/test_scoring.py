from decimal import Decimal

from app.services.scoring import build_score_summary


def test_unanswered_round_is_excluded_from_score():
    rounds = [
        {
            "answer_text": "有效回答",
            "technical_score": Decimal("8"),
            "depth_score": Decimal("6"),
            "logic_score": Decimal("7"),
            "role_match_score": Decimal("8"),
            "speech_rate_score": Decimal("5"),
            "clarity_score": Decimal("5"),
            "confidence_score": Decimal("5"),
        },
        {
            "answer_text": None,
            "technical_score": Decimal("0"),
            "depth_score": Decimal("0"),
            "logic_score": Decimal("0"),
            "role_match_score": Decimal("0"),
            "speech_rate_score": Decimal("0"),
            "clarity_score": Decimal("0"),
            "confidence_score": Decimal("0"),
        },
    ]
    summary = build_score_summary(rounds)
    assert summary["technical_score"] == 8
    assert summary["total_score"] == 7.25

