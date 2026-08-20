import pytest

import httpx

from app.database import SessionLocal
from app.models import EvaluationRun, Organization
from app.services.evaluation_service import (
    CloudLLMEvaluationProvider,
    LocalVLLMEvaluationProvider,
    _build_provider,
    baseline_provider,
    enqueue_evaluation_run,
    evaluate_answer_similarity,
    get_active_llm_model,
    get_available_providers,
    get_evaluation_health,
    get_evaluation_provider,
    get_organization_provider_config,
    normalize_llm_score,
    organization_llm_configured,
    parse_llm_json,
)


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
async def test_legacy_similarity_function_uses_baseline_provider():
    score, feedback = await evaluate_answer_similarity(
        "I listen and follow up.",
        "Listen and follow up.",
    )

    assert score == 85.0
    assert "deterministic_baseline" in feedback


def test_parse_llm_json_strips_qwen_thinking_block():
    parsed = parse_llm_json(' thinkinghidden reasoning response{"score": 8, "feedback_en": "Good", "feedback_ar": "جيد"}')

    assert parsed.score == 80.0
    assert parsed.feedback_ar == "جيد"


def test_parse_llm_json_validates_against_schema():
    with pytest.raises((ValueError, TypeError)):
        parse_llm_json("not json at all")
    with pytest.raises((ValueError, TypeError)):
        parse_llm_json('{"feedback_en": "missing score"}')
    with pytest.raises((ValueError, TypeError)):
        parse_llm_json('{"score": "high", "feedback_en": "Good"}')
    with pytest.raises((ValueError, TypeError)):
        parse_llm_json('{"score": 8, "matched_criteria": "listen"}')


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

        async def post(self, url, json, headers=None):
            assert url == "http://local-vllm.test/v1/chat/completions"
            assert json["model"] == "qwen3-test"
            assert json["response_format"] == {"type": "json_object"}
            assert "Rubric criteria JSON" in json["messages"][1]["content"]
            assert "Ownership" in json["messages"][1]["content"]
            return FakeResponse()

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", FakeClient)

    provider = LocalVLLMEvaluationProvider(baseline_provider, model="qwen3-test", base_url="http://local-vllm.test/v1")
    result = await provider.evaluate_answer(
        "I listen and follow up.",
        "Listen and follow up.",
        [{"name": "Ownership", "description": "Takes ownership", "weight": 1.0}],
    )

    assert result.score == 90.0
    assert result.evidence["provider"] == "local_vllm"
    assert result.evidence["model"] == "qwen3-test"
    assert result.evidence["prompt_version"] == "rubric-v2"
    assert result.evidence["structured_output"] is True
    assert result.evidence["schema_version"] == "1"
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

        async def post(self, url, json, headers=None):
            raise RuntimeError("vllm offline")

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", FailingClient)

    provider = LocalVLLMEvaluationProvider(baseline_provider, base_url="http://local-vllm.test/v1")
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.score == 85.0
    assert result.evidence["provider"] == "deterministic_baseline"
    assert result.evidence["provider_fallback_from"] == "local_vllm"
    assert "vllm offline" in result.evidence["provider_fallback_reason"]
    assert "deterministic fallback" in result.feedback


@pytest.mark.asyncio
async def test_local_vllm_provider_falls_back_when_not_configured():
    provider = LocalVLLMEvaluationProvider(baseline_provider)
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.score == 85.0
    assert result.evidence["provider_fallback_from"] == "local_vllm"
    assert "not configured" in result.evidence["provider_fallback_reason"]


def test_organization_llm_configured_rules():
    assert organization_llm_configured({}) is False
    assert organization_llm_configured({"evaluation_provider": "local_vllm", "evaluation_base_url": "http://vllm:8100", "evaluation_model": "qwen3"}) is True
    assert organization_llm_configured({"evaluation_provider": "cloud_llm", "evaluation_base_url": "https://api.test", "evaluation_model": "gpt"}) is False
    assert organization_llm_configured({"evaluation_provider": "cloud_llm", "evaluation_base_url": "https://api.test", "evaluation_model": "gpt", "evaluation_api_key": "sk"}) is True
    assert organization_llm_configured({"evaluation_provider": "hybrid", "evaluation_base_url": "http://vllm:8100", "evaluation_model": "qwen3"}) is True


def test_enqueue_evaluation_run_uses_background_tasks_by_default():
    calls = []

    class FakeBackgroundTasks:
        def add_task(self, func, *args):
            calls.append((func, args))

    db = SessionLocal()
    try:
        run = EvaluationRun(response_id=1, provider="deterministic_baseline", status="queued")
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    backend = enqueue_evaluation_run(1, run_id, FakeBackgroundTasks())

    assert backend == "background"
    assert calls[0][1] == (1, run_id)


def test_enqueue_evaluation_run_uses_rq_when_configured(monkeypatch):
    enqueued = []

    class FakeQueue:
        def __init__(self, name, connection):
            self.name = name
            self.connection = connection

        def enqueue(self, func, *args, job_timeout):
            enqueued.append((self.name, func, args, job_timeout))

    db = SessionLocal()
    try:
        run = EvaluationRun(response_id=3, provider="deterministic_baseline", status="queued")
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    monkeypatch.setattr("app.services.evaluation_service.settings.EVALUATION_QUEUE_BACKEND", "rq")
    monkeypatch.setattr("app.services.evaluation_service.redis.from_url", lambda url: object())
    monkeypatch.setattr("app.services.evaluation_service.Queue", FakeQueue)

    backend = enqueue_evaluation_run(3, run_id, object())

    assert backend == "rq"
    assert enqueued[0][0] == "evaluation"
    assert enqueued[0][2] == (3, run_id)
    assert enqueued[0][3] == 600


def test_enqueue_evaluation_run_holds_non_queued_runs():
    db = SessionLocal()
    try:
        run = EvaluationRun(response_id=9, provider="deterministic_baseline", status="pending")
        db.add(run)
        db.commit()
        run_id = run.id
    finally:
        db.close()

    assert enqueue_evaluation_run(9, run_id, object()) == "held"


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

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", FakeClient)

    provider = CloudLLMEvaluationProvider(
        baseline_provider, model="gpt-test-mini", base_url="https://api.cloud.test/v1", api_key="sk-cloud-test"
    )
    result = await provider.evaluate_answer(
        "I structure my answer.",
        "Structure the answer.",
        [{"name": "Structure", "description": "Clear organization", "weight": 1.0}],
    )

    assert captured["url"] == "https://api.cloud.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-cloud-test"
    assert captured["json"]["model"] == "gpt-test-mini"
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert "/no_think" not in captured["json"]["messages"][0]["content"]
    assert result.score == 80.0
    assert result.evidence["provider"] == "cloud_llm"
    assert result.evidence["model"] == "gpt-test-mini"


@pytest.mark.asyncio
async def test_cloud_provider_falls_back_without_api_key():
    provider = CloudLLMEvaluationProvider(
        baseline_provider, model="gpt-test-mini", base_url="https://api.cloud.test/v1"
    )
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.evidence["provider_fallback_from"] == "cloud_llm"
    assert result.evidence["provider"] == "deterministic_baseline"
    assert "not configured" in result.evidence["provider_fallback_reason"]


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

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", FailingClient)

    provider = CloudLLMEvaluationProvider(
        baseline_provider, model="gpt-test-mini", base_url="https://api.cloud.test/v1", api_key="sk-cloud-test"
    )
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.evidence["provider_fallback_from"] == "cloud_llm"
    assert "cloud outage" in result.evidence["provider_fallback_reason"]


def test_build_provider_hybrid_chain():
    provider = _build_provider("hybrid", model="shared-model", base_url="http://vllm:8100", api_key="sk")

    assert provider.name == "local_vllm"
    assert provider.fallback_provider.name == "cloud_llm"
    assert provider.fallback_provider.fallback_provider.name == "deterministic_baseline"
    assert provider.fallback_provider.api_key == "sk"


def test_build_provider_cloud_normalizes_name():
    provider = _build_provider("cloud_llm", model="gpt", base_url="https://api.test", api_key="sk")

    assert provider.name == "cloud_llm"
    assert provider.model == "gpt"
    assert provider.api_key == "sk"


def test_build_provider_local_default():
    provider = _build_provider("local_vllm", model="qwen3", base_url="http://vllm:8100")

    assert provider.name == "local_vllm"
    assert provider.fallback_provider.name == "deterministic_baseline"


def _create_org(db, provider, model=None, base_url=None, api_key=None) -> int:
    org = Organization(name="Provider Test Org")
    db.add(org)
    db.flush()
    org.evaluation_provider = provider
    org.evaluation_model = model
    org.evaluation_base_url = base_url
    org.evaluation_api_key = api_key
    db.commit()
    return org.id


def test_org_override_selects_cloud_provider():
    db = SessionLocal()
    try:
        org_id = _create_org(
            db, "cloud_llm",
            model="org-cloud-model", base_url="https://org.example.com/v1", api_key="sk-org",
        )
        provider = get_evaluation_provider(db, org_id)
        assert provider.name == "cloud_llm"
        assert provider.model == "org-cloud-model"
        assert provider.base_url == "https://org.example.com/v1"
        assert provider.api_key == "sk-org"
        assert get_active_llm_model(db, org_id) == "org-cloud-model"
        assert get_organization_provider_config(db, org_id)["evaluation_provider"] == "cloud_llm"
    finally:
        db.close()


def test_org_override_selects_local_provider():
    db = SessionLocal()
    try:
        org_id = _create_org(db, "local_vllm", model="org-local-model", base_url="http://vllm:8100")
        provider = get_evaluation_provider(db, org_id)
        assert provider.name == "local_vllm"
        assert provider.model == "org-local-model"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_org_cloud_unconfigured_falls_back_at_evaluate_time():
    db = SessionLocal()
    try:
        org_id = _create_org(db, "cloud_llm")
        provider = get_evaluation_provider(db, org_id)
        assert provider.name == "cloud_llm"
        result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")
        assert result.evidence["provider_fallback_from"] == "cloud_llm"
        assert result.evidence["provider"] == "deterministic_baseline"
    finally:
        db.close()


def test_custom_cloud_endpoint_used_from_org_settings():
    db = SessionLocal()
    try:
        org_id = _create_org(
            db, "cloud_llm",
            model="gemini-test", base_url="https://generativelanguage.googleapis.com", api_key="sk-custom",
        )
        provider = get_evaluation_provider(db, org_id)
        assert provider.name == "cloud_llm"
        assert provider.model == "gemini-test"
        assert provider.base_url == "https://generativelanguage.googleapis.com"
        assert provider.api_key == "sk-custom"
    finally:
        db.close()


def test_available_providers_all_selectable_no_deterministic_option():
    providers = {p["value"]: p["available"] for p in get_available_providers()}
    assert providers == {"local_vllm": True, "cloud_llm": True, "hybrid": True}


def test_no_org_override_uses_baseline_provider():
    db = SessionLocal()
    try:
        org_id = _create_org(db, None)
        provider = get_evaluation_provider(db, org_id)
        assert provider.name == "deterministic_baseline"
        assert get_organization_provider_config(db, org_id) == {}
    finally:
        db.close()


@pytest.mark.asyncio
async def test_evaluation_health_not_configured_without_org_provider():
    health = await get_evaluation_health()

    assert health["provider"] == "deterministic_baseline"
    assert health["configured"] is False
    assert health["healthy"] is False
    assert health["status"] == "not_configured"
    assert health["config_hash"] is None


@pytest.mark.asyncio
async def test_evaluation_health_reflects_org_provider(monkeypatch):
    class HealthyClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            return type("Resp", (), {"raise_for_status": lambda self: None, "status_code": 200})()

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", HealthyClient)

    db = SessionLocal()
    try:
        org_id = _create_org(db, "cloud_llm", model="org-cloud-model", base_url="https://org.example.com/v1", api_key="sk-org")
        health = await get_evaluation_health(db=db, organization_id=org_id)
        assert health["provider"] == "cloud_llm"
        assert health["model_name"] == "org-cloud-model"
        assert health["organization_provider"] == "cloud_llm"
        assert health["configured"] is True
        assert health["healthy"] is True
        assert health["status"] == "available"
        assert health["config_hash"]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_evaluation_health_reports_llm_unavailable(monkeypatch):
    class FailingClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url, headers=None):
            raise RuntimeError("offline")

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", FailingClient)

    db = SessionLocal()
    try:
        org_id = _create_org(db, "local_vllm", model="qwen3", base_url="http://local-vllm.test/v1")
        health = await get_evaluation_health(db=db, organization_id=org_id)
        assert health["provider"] == "local_vllm"
        assert health["configured"] is True
        assert health["healthy"] is False
        assert health["status"] == "llm_unavailable_using_fallback"
        assert health["fallback_provider"] == "deterministic_baseline"
        assert "offline" in health["last_error"]
    finally:
        db.close()


class FakeLLMResponse:
    def __init__(self, content):
        self._content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.mark.asyncio
async def test_local_provider_repairs_invalid_json_once(monkeypatch):
    calls = []

    class RepairClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers=None):
            calls.append(json)
            if len(calls) == 1:
                return FakeLLMResponse('{"score": 9, "feedback_en": "broken json"')
            return FakeLLMResponse(
                '{"score": 9, "feedback_en": "Fixed", "feedback_ar": "جيد", '
                '"matched_criteria": ["listen"], "missing_criteria": [], "evidence": "ok"}'
            )

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", RepairClient)

    provider = LocalVLLMEvaluationProvider(baseline_provider, model="qwen3-test", base_url="http://local-vllm.test/v1")
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert len(calls) == 2
    assert "Return ONLY a single compact JSON object" in calls[1]["messages"][-1]["content"]
    assert calls[1]["response_format"] == {"type": "json_object"}
    assert result.score == 90.0
    assert result.evidence["provider"] == "local_vllm"


@pytest.mark.asyncio
async def test_cloud_provider_degrades_when_response_format_rejected(monkeypatch):
    calls = []

    class DegradeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers=None):
            calls.append(json)
            if len(calls) == 1:
                response = httpx.Response(
                    400,
                    json={"error": "unsupported parameter: response_format"},
                    request=httpx.Request("POST", url),
                )
                response.raise_for_status()
            return FakeLLMResponse(
                '{"score": 7, "feedback_en": "ok", "feedback_ar": "حسن", '
                '"matched_criteria": ["x"], "missing_criteria": [], "evidence": "e"}'
            )

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", DegradeClient)

    provider = CloudLLMEvaluationProvider(
        baseline_provider, model="gpt-test-mini", base_url="https://api.cloud.test/v1", api_key="sk-cloud-test"
    )
    result = await provider.evaluate_answer("I structure my answer.", "Structure the answer.")

    assert len(calls) == 2
    assert "response_format" not in calls[1]
    assert result.score == 70.0
    assert result.evidence["structured_output"] is False
    assert result.evidence["provider"] == "cloud_llm"


@pytest.mark.asyncio
async def test_local_provider_skips_response_format_when_disabled(monkeypatch):
    captured = {}

    class PlainClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers=None):
            captured["json"] = json
            return FakeLLMResponse(
                '{"score": 8, "feedback_en": "ok", "feedback_ar": "جيد", '
                '"matched_criteria": [], "missing_criteria": [], "evidence": "e"}'
            )

    monkeypatch.setattr("app.services.evaluation_service.settings.EVALUATION_STRUCTURED_OUTPUT_ENABLED", False)
    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", PlainClient)

    provider = LocalVLLMEvaluationProvider(baseline_provider, model="qwen3-test", base_url="http://local-vllm.test/v1")
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert "response_format" not in captured["json"]
    assert result.score == 80.0
    assert result.evidence["structured_output"] is False


@pytest.mark.asyncio
async def test_repair_retry_exhausted_falls_back(monkeypatch):
    class AlwaysBrokenClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json, headers=None):
            return FakeLLMResponse("garbage no braces")

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", AlwaysBrokenClient)

    provider = LocalVLLMEvaluationProvider(baseline_provider, model="qwen3-test", base_url="http://local-vllm.test/v1")
    result = await provider.evaluate_answer("I listen and follow up.", "Listen and follow up.")

    assert result.evidence["provider"] == "deterministic_baseline"
    assert result.evidence["provider_fallback_from"] == "local_vllm"
    assert "did not contain a JSON object" in result.evidence["provider_fallback_reason"]