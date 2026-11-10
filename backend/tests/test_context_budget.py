from app.core.context_budget import ContextBudget


def test_estimator_counts_chinese_conservatively():
    assert ContextBudget.estimate_tokens("abcdefgh") == 2
    assert ContextBudget.estimate_tokens("你好世界") >= 4


def test_trim_respects_budget():
    budget = ContextBudget(max_tokens=50)
    text = "Spring Boot 自动配置通过条件装配注册 Bean。" * 20
    trimmed = budget.trim(text, 20)
    assert ContextBudget.estimate_tokens(trimmed) <= 21
    assert trimmed.endswith("…")


def test_pack_stops_before_budget_is_exceeded():
    budget = ContextBudget(max_tokens=30)
    packed = budget.pack(["a" * 80, "b" * 80], reserved_tokens=5)
    assert len(packed) == 1
    assert ContextBudget.estimate_tokens(packed[0]) <= 25

