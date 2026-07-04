from agent_finops.pricing import estimate_cost_usd


def test_known_model_uses_real_rate():
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost == 0.15


def test_completion_tokens_priced_separately():
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=0, completion_tokens=1_000_000)
    assert cost == 0.60


def test_local_model_is_genuinely_free():
    cost = estimate_cost_usd("llama3.2:3b", prompt_tokens=500_000, completion_tokens=500_000)
    assert cost == 0.0


def test_unknown_model_gets_nonzero_fallback_not_silent_zero():
    cost = estimate_cost_usd("some-brand-new-model", prompt_tokens=1_000_000, completion_tokens=0)
    assert cost > 0


def test_negative_tokens_rejected():
    try:
        estimate_cost_usd("gpt-4o-mini", prompt_tokens=-1, completion_tokens=0)
        assert False, "expected ValueError"
    except ValueError:
        pass
