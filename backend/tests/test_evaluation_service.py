import pytest

from app.services.evaluation_service import baseline_provider, evaluate_answer_similarity


@pytest.mark.asyncio
async def test_baseline_scores_complete_keyword_coverage_high():
    result = await baseline_provider.evaluate_answer(
        "I listen, empathize, clarify the issue, resolve it, and follow up with the customer.",
        "Listen, empathize, clarify, resolve, and follow up.",
    )

    assert result.score == 97.5
    assert result.evidence["provider"] == "deterministic_baseline"
    assert result.evidence["keyword_coverage"] == 100.0
    assert set(result.evidence["matched_keywords"]) == {"listen", "empathize", "clarify", "resolve", "follow"}


@pytest.mark.asyncio
async def test_baseline_penalizes_missing_keywords_and_short_answers():
    result = await baseline_provider.evaluate_answer(
        "I listen.",
        "Listen, empathize, clarify, resolve, and follow up.",
    )

    assert 0 < result.score < 50
    assert "Missing concepts" in result.feedback
    assert "empathize" in result.evidence["missing_keywords"]


@pytest.mark.asyncio
async def test_baseline_scores_empty_answer_zero_with_evidence():
    result = await baseline_provider.evaluate_answer("", "Listen and follow up.")

    assert result.score == 0.0
    assert result.evidence["keyword_coverage"] == 0.0
    assert "empty candidate response" in result.feedback


@pytest.mark.asyncio
async def test_legacy_similarity_function_uses_baseline_provider():
    score, feedback = await evaluate_answer_similarity(
        "I listen and follow up.",
        "Listen and follow up.",
    )

    assert score == 85.0
    assert "deterministic_baseline" in feedback