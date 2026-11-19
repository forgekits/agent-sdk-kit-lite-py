from types import SimpleNamespace

from agent_kit_lite.report import explain_failure, format_summary, summarize_result

USAGE = {
    "input_tokens": 1200,
    "output_tokens": 300,
    "cache_read_input_tokens": 800,
    "cache_creation_input_tokens": 100,
}
MODEL_USAGE = {
    "claude-opus-5-5": {
        "inputTokens": 1200,
        "outputTokens": 300,
        "cacheReadInputTokens": 800,
        "cacheCreationInputTokens": 100,
        "webSearchRequests": 0,
        "costUSD": 0.0123,
        "contextWindow": 1_000_000,
        "maxOutputTokens": 128_000,
    }
}

SUCCESS = SimpleNamespace(
    subtype="success",
    duration_ms=4200,
    duration_api_ms=3900,
    is_error=False,
    num_turns=3,
    session_id="s1",
    total_cost_usd=0.0123,
    usage=USAGE,
    result="108.1",
    model_usage=MODEL_USAGE,
    permission_denials=[],
    errors=None,
)

OVER_BUDGET = SimpleNamespace(
    subtype="error_max_budget_usd",
    duration_ms=9000,
    duration_api_ms=8500,
    is_error=True,
    num_turns=7,
    session_id="s2",
    total_cost_usd=0.51,
    usage=USAGE,
    result=None,
    model_usage=MODEL_USAGE,
    permission_denials=[],
    errors=["budget exceeded"],
)


def test_success() -> None:
    s = summarize_result(SUCCESS)
    assert s.ok is True
    assert s.text == "108.1"
    assert s.turns == 3
    assert s.cost_usd == 0.0123
    assert s.cache_read_tokens == 800
    assert s.models["claude-opus-5-5"].cost_usd == 0.0123
    assert s.errors == ()
    assert explain_failure(s) is None


def test_budget_failure() -> None:
    s = summarize_result(OVER_BUDGET)
    assert s.ok is False
    assert s.text == ""
    assert s.errors == ("budget exceeded",)
    assert "AGENT_MAX_BUDGET_USD" in (explain_failure(s) or "")


def test_failure_without_errors_uses_subtype() -> None:
    s = summarize_result(
        SimpleNamespace(**{**vars(OVER_BUDGET), "subtype": "error_max_turns", "errors": None})
    )
    assert s.errors == ("error_max_turns",)


def test_format() -> None:
    out = format_summary(summarize_result(SUCCESS))
    assert "status      ok (success)" in out
    assert "$0.0123" in out
    assert "claude-opus-5-5" in out
    assert "errors" not in out


def test_handles_missing_usage() -> None:
    s = summarize_result(
        SimpleNamespace(subtype="success", is_error=False, result="x", usage=None, total_cost_usd=None)
    )
    assert s.ok and s.input_tokens == 0 and s.cost_usd == 0.0
