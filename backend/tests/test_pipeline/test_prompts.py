"""Tests for pipeline prompts, cost estimation, and text helpers."""

from civicint.pipeline.prompts import (
    CASE_BUILDER_PROMPT,
    TRIAGE_PROMPT,
    estimate_cost,
    truncate_text,
)


class TestPrompts:
    def test_triage_prompt_is_nonempty_string(self):
        assert isinstance(TRIAGE_PROMPT, str)
        assert len(TRIAGE_PROMPT) > 100

    def test_triage_prompt_mentions_categories(self):
        for cat in ("zoning", "permits", "water", "industry"):
            assert cat in TRIAGE_PROMPT

    def test_case_builder_prompt_is_nonempty_string(self):
        assert isinstance(CASE_BUILDER_PROMPT, str)
        assert len(CASE_BUILDER_PROMPT) > 100

    def test_case_builder_prompt_mentions_required_fields(self):
        for field in ("headline", "debrief", "status", "timeline", "evidence", "confidence"):
            assert field in CASE_BUILDER_PROMPT


class TestEstimateCost:
    def test_gpt4o_mini_cost(self):
        cost = estimate_cost(1_000_000, 0, "gpt-4o-mini")
        expected = 0.15 * 0.92
        assert abs(cost - expected) < 1e-6

    def test_gpt4o_cost(self):
        cost = estimate_cost(0, 1_000_000, "gpt-4o")
        expected = 10.00 * 0.92
        assert abs(cost - expected) < 1e-6

    def test_unknown_model_falls_back_to_mini(self):
        cost_unknown = estimate_cost(1000, 500, "some-future-model")
        cost_mini = estimate_cost(1000, 500, "gpt-4o-mini")
        assert cost_unknown == cost_mini

    def test_zero_tokens(self):
        assert estimate_cost(0, 0, "gpt-4o") == 0.0

    def test_both_prompt_and_completion(self):
        cost = estimate_cost(100, 200, "gpt-4o-mini")
        assert cost > 0


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", 100) == "hello"

    def test_exact_length_unchanged(self):
        text = "a" * 50
        assert truncate_text(text, 50) == text

    def test_long_text_truncated(self):
        text = "a" * 100
        result = truncate_text(text, 50)
        assert result.startswith("a" * 50)
        assert "[... truncated ...]" in result
        assert len(result) < len(text) + 30

    def test_empty_string(self):
        assert truncate_text("", 10) == ""
