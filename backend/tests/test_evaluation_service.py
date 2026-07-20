import pytest

from app.services import evaluation_service
from app.config import settings
from app.services.evaluation_service import baseline_provider, evaluate_answer_similarity, get_evaluation_health, local_vllm_provider, normalize_llm_score, parse_llm_json


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
async def test_baseline_includes_rubric_criteria_in_evidence_and_scoring():
    result = await baseline_provider.evaluate_answer(
        "I listen first and use a clear escalation plan.",
        "Listen and follow up.",
        [{"name": "Escalation", "description": "Has a clear escalation plan", "weight": 1.5}],
    )

    assert "escalation" in result.evidence["matched_keywords"]
    assert result.evidence["rubric_criteria"][0]["name"] == "Escalation"


@pytest.mark.asyncio
async def test_baseline_scores_empty_answer_zero_with_evidence():
    result = await baseline_provider.evaluate_answer("", "Listen and follow up.")

    assert result.score == 0.0
    assert result.evidence["keyword_coverage"] == 0.0
    assert "empty candidate response" in result.feedback


@pytest.mark.asyncio
async def test_legacy_similarity_function_uses_baseline_provider(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "deterministic_baseline")

    score, feedback = await evaluate_answer_similarity(
        "I listen and follow up.",
        "Listen and follow up.",
    )

    assert score == 85.0
    assert "deterministic_baseline" in feedback


def test_parse_llm_json_strips_qwen_thinking_block():
    parsed = parse_llm_json('<think>hidden reasoning</think>{"score": 8, "feedback_en": "Good", "feedback_ar": "جيد"}')

    assert parsed["score"] == 8
    assert parsed["feedback_ar"] == "جيد"


def test_normalize_llm_score_accepts_ten_or_hundred_point_scales():
    assert normalize_llm_score(8) == 80.0
    assert normalize_llm_score(87.5) == 87.5
    assert normalize_llm_score(120) == 100.0


@pytest.mark.asyncio
async def test_local_vllm_provider_uses_openai_compatible_json(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": '{"score": 9, "feedback_en": "Strong answer", "feedback_ar": "إجابة قوية", "matched_criteria": ["listen"], "missing_criteria": [], "evidence": "Covers key actions"}'
                    }
                }]
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            assert url == "http://local-vllm.test/v1/chat/completions"
            assert json["model"] == "qwen3-test"
            assert "Rubric criteria JSON" in json["messages"][1]["content"]
            assert "Ownership" in json["messages"][1]["content"]
            return FakeResponse()

    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://local-vllm.test/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "qwen3-test")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", FakeClient)

    result = await local_vllm_provider.evaluate_answer(
        "I listen and follow up.",
        "Listen and follow up.",
        [{"name": "Ownership", "description": "Takes ownership", "weight": 1.0}],
    )

    assert result.score == 90.0
    assert result.evidence["provider"] == "local_vllm"
    assert result.evidence["model"] == "qwen3-test"
    assert result.evidence["rubric_criteria"][0]["name"] == "Ownership"
    assert "Strong answer" in result.feedback
    assert "إجابة قوية" in result.feedback


@pytest.mark.asyncio
async def test_local_vllm_provider_falls_back_when_endpoint_fails(monkeypatch):
    class FailingClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            raise RuntimeError("vllm offline")

    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", FailingClient)

    result = await local_vllm_provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.score == 85.0
    assert result.evidence["provider_fallback_from"] == "local_vllm"
    assert "vllm offline" in result.evidence["provider_fallback_reason"]
    assert "deterministic fallback" in result.feedback


@pytest.mark.asyncio
async def test_evaluation_health_reports_local_vllm_unavailable(monkeypatch):
    class FailingClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            raise RuntimeError("offline")

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "local_vllm")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", FailingClient)

    health = await get_evaluation_health()

    assert health["provider"] == "local_vllm"
    assert health["healthy"] is False
    assert health["fallback_provider"] == "deterministic_baseline"
    assert "offline" in health["last_error"]