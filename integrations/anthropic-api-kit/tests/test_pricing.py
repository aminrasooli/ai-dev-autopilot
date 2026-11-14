from anthropic_api_kit.pricing import estimate_cost_usd
import pytest


def test_known_model_cost():
    est = estimate_cost_usd("claude-haiku-4-5", input_tokens=1_000_000, output_tokens=1_000_000)
    assert est.input_cost_usd == pytest.approx(1.00)
    assert est.output_cost_usd == pytest.approx(5.00)
    assert est.total_usd == pytest.approx(6.00)


def test_small_call_cost():
    est = estimate_cost_usd("claude-sonnet-5", input_tokens=500, output_tokens=200)
    assert est.total_usd > 0
    assert est.total_usd < 0.01


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        estimate_cost_usd("not-a-real-model", input_tokens=10, output_tokens=10)
