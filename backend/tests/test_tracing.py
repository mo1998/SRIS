import pytest

from app.services import tracing
from app.services.tracing import add_answer_span, create_run_trace, finalize_run_trace, flush_traces, get_langfuse


class FakeSpan:
    def __init__(self):
        self.ended = False

    def end(self):
        self.ended = True


class FakeTrace:
    def __init__(self):
        self.spans = []
        self.output = None

    def span(self, **kwargs):
        self.spans.append(kwargs)
        return FakeSpan()

    def update(self, **kwargs):
        self.output = kwargs.get("output")


class FakeClient:
    def __init__(self):
        self.traces = []
        self.flushed = False

    def trace(self, **kwargs):
        self.traces.append(kwargs)
        return FakeTrace()

    def flush(self):
        self.flushed = True


class FakeResult:
    def __init__(self):
        self.score = 90.0
        self.feedback = "local qwen3-test: Strong Arabic feedback: جيد"
        self.evidence = {"provider": "local_vllm"}


def test_get_langfuse_disabled_returns_none(monkeypatch):
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", False)
    assert get_langfuse() is None


def test_get_langfuse_init_failure_returns_none(monkeypatch):
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", True)

    def broken_init(**kwargs):
        raise RuntimeError("no network")

    monkeypatch.setattr("langfuse.Langfuse", broken_init)
    assert get_langfuse() is None


@pytest.mark.asyncio
async def test_create_run_trace_metadata(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", True)

    def fake_get_langfuse():
        return fake

    monkeypatch.setattr(tracing, "get_langfuse", fake_get_langfuse)

    trace = await create_run_trace(
        evaluation_run_id=123,
        provider="local_vllm",
        model="qwen3-test",
        prompt_version="rubric-v2",
        config_hash="abc123",
        organization_id=7,
    )

    assert trace is not None
    assert len(fake.traces) == 1
    assert fake.traces[0]["id"] == "run-123"
    assert fake.traces[0]["name"] == "evaluation_run"
    meta = fake.traces[0]["metadata"]
    assert meta["evaluation_run_id"] == 123
    assert meta["provider"] == "local_vllm"
    assert meta["prompt_version"] == "rubric-v2"
    assert meta["config_hash"] == "abc123"
    assert meta["organization_id"] == 7


@pytest.mark.asyncio
async def test_disabled_trace_helpers_are_noops(monkeypatch):
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", False)

    trace = await create_run_trace(
        evaluation_run_id=1, provider="local_vllm", model="m", prompt_version="v1", config_hash="c", organization_id=1
    )
    assert trace is None
    await add_answer_span(None, question_answer_id=1, question_text="q", expected_answer="e", answer_text="a", candidate_name="n", rubric_criteria=[], result=FakeResult())
    await finalize_run_trace(None, score=1.0, passed=True)
    await flush_traces()


@pytest.mark.asyncio
async def test_answer_span_masks_at_sdk_boundary(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", True)
    monkeypatch.setattr("app.services.tracing.settings.EVALUATION_PII_MASKING_ENABLED", True)

    def fake_get_langfuse():
        return fake

    monkeypatch.setattr(tracing, "get_langfuse", fake_get_langfuse)

    trace = await create_run_trace(
        evaluation_run_id=10, provider="cloud_llm", model="gpt-test", prompt_version="rubric-v2", config_hash="h", organization_id=2
    )
    await add_answer_span(
        trace,
        question_answer_id=55,
        question_text="Introduce yourself",
        expected_answer="A short intro",
        answer_text="Hi, my name is Jane Doe, email jane.doe@corp.com, phone 555-123-4567",
        candidate_name="Jane Doe",
        rubric_criteria=[],
        result=FakeResult(),
    )

    assert len(trace.spans) == 1
    span_input = trace.spans[0]["input"]
    assert "jane.doe@corp.com" not in span_input["candidate_answer"]
    assert "[EMAIL]" in span_input["candidate_answer"]
    assert "555-123-4567" not in span_input["candidate_answer"]
    assert "[PHONE]" in span_input["candidate_answer"]
    assert "Jane Doe" not in span_input["candidate_answer"]
    assert "[NAME]" in span_input["candidate_answer"]
    assert trace.spans[0]["output"]["score"] == 90.0
    assert trace.spans[0]["metadata"]["pii_masking"]["masked"] is True


@pytest.mark.asyncio
async def test_masking_failure_at_sdk_boundary_skips_span(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", True)
    monkeypatch.setattr("app.services.tracing.settings.EVALUATION_PII_MASKING_ENABLED", True)

    def fake_get_langfuse():
        return fake

    def broken_mask_pii(text, candidate_name=None):
        raise RuntimeError("masking down")

    monkeypatch.setattr(tracing, "get_langfuse", fake_get_langfuse)
    monkeypatch.setattr(tracing, "mask_pii", broken_mask_pii)

    trace = await create_run_trace(
        evaluation_run_id=11, provider="local_vllm", model="m", prompt_version="v2", config_hash="h", organization_id=1
    )
    await add_answer_span(
        trace, question_answer_id=1, question_text="q", expected_answer="e", answer_text="raw pii", candidate_name="Jane", rubric_criteria=[], result=FakeResult()
    )

    assert len(trace.spans) == 0  # span skipped, nothing leaked to the trace store


@pytest.mark.asyncio
async def test_finalize_updates_trace_output(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr("app.services.tracing.settings.LANGFUSE_ENABLED", True)

    def fake_get_langfuse():
        return fake

    monkeypatch.setattr(tracing, "get_langfuse", fake_get_langfuse)

    trace = await create_run_trace(
        evaluation_run_id=12, provider="local_vllm", model="m", prompt_version="v2", config_hash="h", organization_id=1
    )
    await finalize_run_trace(trace, score=85.0, passed=True)
    await flush_traces()

    assert trace.output == {"score": 85.0, "passed": True, "error": None}
    assert fake.flushed is True