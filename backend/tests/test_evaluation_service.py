import pytest

from app.services import evaluation_service
from app.config import settings
from app.services.evaluation_service import baseline_provider, evaluate_answer_similarity, get_active_llm_model, get_evaluation_health, get_evaluation_provider, local_vllm_provider, normalize_llm_score, parse_llm_json


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
    assert result.evidence["prompt_version"] == settings.EVALUATION_PROMPT_VERSION
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
    assert health["prompt_version"] == settings.EVALUATION_PROMPT_VERSION
    assert health["config_hash"]
    assert health["healthy"] is False
    assert health["fallback_provider"] == "deterministic_baseline"
    assert "offline" in health["last_error"]


def test_enqueue_evaluation_run_uses_background_tasks_by_default(monkeypatch):
    calls = []

    class FakeBackgroundTasks:
        def add_task(self, func, *args):
            calls.append((func, args))

    monkeypatch.setattr(settings, "EVALUATION_QUEUE_BACKEND", "background")

    backend = evaluation_service.enqueue_evaluation_run(1, 2, FakeBackgroundTasks())

    assert backend == "background"
    assert calls[0][1] == (1, 2)


def test_enqueue_evaluation_run_uses_rq_when_configured(monkeypatch):
    enqueued = []

    class FakeQueue:
        def __init__(self, name, connection):
            self.name = name
            self.connection = connection

        def enqueue(self, func, *args, job_timeout):
            enqueued.append((self.name, func, args, job_timeout))

    monkeypatch.setattr(settings, "EVALUATION_QUEUE_BACKEND", "rq")
    monkeypatch.setattr(evaluation_service.redis, "from_url", lambda url: object())
    monkeypatch.setattr(evaluation_service, "Queue", FakeQueue)

    backend = evaluation_service.enqueue_evaluation_run(3, 4, object())

    assert backend == "rq"
    assert enqueued[0][0] == settings.EVALUATION_QUEUE_NAME
    assert enqueued[0][2] == (3, 4)
    assert enqueued[0][3] == 600

@pytest.mark.asyncio
async def test_cloud_provider_sends_openai_compatible_payload(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": '{"score": 8, "feedback_en": "Clear structure", "feedback_ar": "هيكل واضح", "matched_criteria": ["structure"], "missing_criteria": [], "evidence": "Well organized"}'
                    }
                }]
            }

    captured = {}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "cloud")
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_API_KEY", "sk-cloud-test")
    monkeypatch.setattr(settings, "CLOUD_LLM_MODEL", "gpt-test-mini")
    monkeypatch.setattr(settings, "CLOUD_LLM_BASE_URL", "https://api.cloud.test/v1")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", FakeClient)

    provider = get_evaluation_provider()
    result = await provider.evaluate_answer(
        "I structure my answer.",
        "Structure the answer.",
        [{"name": "Structure", "description": "Clear organization", "weight": 1.0}],
    )

    assert captured["url"] == "https://api.cloud.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-cloud-test"
    assert captured["json"]["model"] == "gpt-test-mini"
    assert "/no_think" not in captured["json"]["messages"][0]["content"]
    assert result.score == 80.0
    assert result.evidence["provider"] == "cloud_llm"
    assert result.evidence["model"] == "gpt-test-mini"


@pytest.mark.asyncio
async def test_cloud_provider_falls_back_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "cloud")
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_API_KEY", "")

    provider = get_evaluation_provider()
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.evidence["provider_fallback_from"] == "cloud_llm"
    assert result.evidence["provider"] == "deterministic_baseline"
    assert "CLOUD_LLM_API_KEY" in result.evidence["provider_fallback_reason"]


@pytest.mark.asyncio
async def test_cloud_provider_falls_back_on_endpoint_error(monkeypatch):
    class FailingClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers):
            raise RuntimeError("cloud outage")

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "cloud")
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_API_KEY", "sk-cloud-test")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", FailingClient)

    provider = get_evaluation_provider()
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.evidence["provider_fallback_from"] == "cloud_llm"
    assert "cloud outage" in result.evidence["provider_fallback_reason"]


def test_get_evaluation_provider_hybrid_chain(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "hybrid")
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)

    provider = get_evaluation_provider()
    assert provider.name == "local_vllm"
    assert provider.fallback_provider.name == "cloud_llm"
    assert provider.fallback_provider.fallback_provider.name == "deterministic_baseline"
    assert get_active_llm_model() == settings.LOCAL_LLM_MODEL


def test_get_evaluation_provider_hybrid_cloud_only(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "hybrid")
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", False)
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)

    provider = get_evaluation_provider()
    assert provider.name == "cloud_llm"
    assert provider.fallback_provider.name == "deterministic_baseline"
    assert get_active_llm_model() == settings.CLOUD_LLM_MODEL


def test_get_evaluation_provider_hybrid_both_disabled_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "hybrid")
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", False)
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", False)

    provider = get_evaluation_provider()
    assert provider.name == "deterministic_baseline"
    assert get_active_llm_model() is None


def test_get_evaluation_provider_cloud_mode_respects_toggle(monkeypatch):
    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "cloud")
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", False)

    provider = get_evaluation_provider()
    assert provider.name == "deterministic_baseline"


@pytest.mark.asyncio
async def test_evaluation_health_reports_cloud_reachable(monkeypatch):
    class HealthyClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            return type("Resp", (), {"raise_for_status": lambda self: None, "status_code": 200})()

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "hybrid")
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_API_KEY", "sk-cloud-test")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", HealthyClient)

    health = await get_evaluation_health()

    assert health["provider"] == "local_vllm"
    assert health["local_healthy"] is True
    assert health["cloud_healthy"] is True
    assert health["healthy"] is True
    assert health["status"] == "available"


@pytest.mark.asyncio
async def test_evaluation_health_hybrid_uses_cloud_when_local_down(monkeypatch):
    class CloudOnlyClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            if url.startswith("http://local"):
                raise RuntimeError("vllm offline")
            return type("Resp", (), {"raise_for_status": lambda self: None, "status_code": 200})()

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "hybrid")
    monkeypatch.setattr(settings, "LOCAL_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_ENABLED", True)
    monkeypatch.setattr(settings, "CLOUD_LLM_API_KEY", "sk-cloud-test")
    monkeypatch.setattr(evaluation_service.httpx, "AsyncClient", CloudOnlyClient)

    health = await get_evaluation_health()

    assert health["local_healthy"] is False
    assert health["cloud_healthy"] is True
    assert health["healthy"] is True
    assert health["status"] == "available"
