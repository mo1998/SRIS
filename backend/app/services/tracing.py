"""Langfuse tracing for replayable evaluation runs.

Best-effort observability: tracing failures never break evaluation. PII policy
mirrors Phase 5 — payloads are masked at the SDK boundary with the same
`mask_pii` used for LLM payloads; if masking fails the span is skipped rather
than risk sending unmasked PII to the trace store.

Disabled by default; enable via `LANGFUSE_ENABLED=true` plus credentials for a
self-hosted Langfuse (OSS) or Langfuse Cloud. Spans are keyed by the trace id,
which is the `evaluation_run` id (`run-<evaluation_run_id>`).
"""

import logging
import threading
from typing import Optional

from app.config import settings
from app.services.pii_masking import mask_pii

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def get_langfuse():
    """Lazy singleton client (sync SDK; network I/O happens in a background thread).

    Returns None when disabled or init failed.
    """
    global _client
    if not settings.LANGFUSE_ENABLED:
        return None
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            try:
                from langfuse import Langfuse

                _client = Langfuse(
                    public_key=settings.LANGFUSE_PUBLIC_KEY,
                    secret_key=settings.LANGFUSE_SECRET_KEY,
                    host=settings.LANGFUSE_HOST,
                )
            except Exception as exc:  # pragma: no cover - init failure path
                logger.warning("Langfuse init failed: %s", exc)
                _client = False
    return _client or None


def _trace_metadata(*, evaluation_run_id, provider, model, prompt_version, config_hash, organization_id) -> dict:
    return {
        "evaluation_run_id": evaluation_run_id,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "config_hash": config_hash,
        "organization_id": organization_id,
    }


async def create_run_trace(
    *,
    evaluation_run_id: int,
    provider: str,
    model: Optional[str],
    prompt_version: str,
    config_hash: Optional[str],
    organization_id: Optional[int],
) -> Optional[object]:
    client = get_langfuse()
    if client is None:
        return None
    try:
        return client.trace(
            id=f"run-{evaluation_run_id}",
            name="evaluation_run",
            metadata=_trace_metadata(
                evaluation_run_id=evaluation_run_id,
                provider=provider,
                model=model,
                prompt_version=prompt_version,
                config_hash=config_hash,
                organization_id=organization_id,
            ),
        )
    except Exception as exc:  # pragma: no cover - tracing is best-effort
        logger.warning("Langfuse trace create failed: %s", exc)
        return None


async def add_answer_span(
    trace,
    *,
    question_answer_id: int,
    question_text: str,
    expected_answer: str,
    answer_text: str,
    candidate_name: Optional[str],
    rubric_criteria: list,
    result,
) -> None:
    if trace is None:
        return
    try:
        # Mask at the SDK boundary; never send unmasked PII to the trace store.
        masked_answer, summary = mask_pii(answer_text, candidate_name)
        span = trace.span(
            name="answer_evaluation",
            input={
                "question_answer_id": question_answer_id,
                "question": question_text,
                "expected_answer": expected_answer,
                "candidate_answer": masked_answer,
                "rubric_criteria": rubric_criteria,
            },
            output={
                "score": result.score,
                "feedback": result.feedback,
                "evidence": result.evidence,
            },
            metadata={
                "pii_masking": {**summary.to_dict(), "enabled": bool(settings.EVALUATION_PII_MASKING_ENABLED)},
            },
        )
        span.end()
    except Exception as exc:  # pragma: no cover - tracing is best-effort
        logger.warning("Langfuse answer span failed: %s", exc)


async def finalize_run_trace(trace, *, score: float, passed: bool, error: Optional[str] = None) -> None:
    if trace is None:
        return
    try:
        trace.update(output={"score": score, "passed": passed, "error": error})
    except Exception as exc:  # pragma: no cover - tracing is best-effort
        logger.warning("Langfuse trace finalize failed: %s", exc)


async def flush_traces() -> None:
    client = get_langfuse()
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:  # pragma: no cover - tracing is best-effort
        logger.warning("Langfuse flush failed: %s", exc)