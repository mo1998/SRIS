"""
Prometheus metrics for SRIS observability.

Exposes an internal `/metrics` endpoint scraped by the Prometheus compose
service, plus the RQ / LLM / email custom metrics the alert rules depend on.
"""

import logging

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings

logger = logging.getLogger("sris.metrics")

EMAIL_SENT_TOTAL = Counter(
    "sris_email_sent_total",
    "Emails successfully handed to the email provider.",
    ["provider"],
)
EMAIL_FAILURES_TOTAL = Counter(
    "sris_email_failures_total",
    "Emails that failed to send after retries.",
    ["provider"],
)
LLM_FALLBACKS_TOTAL = Counter(
    "sris_llm_fallbacks_total",
    "LLM evaluations that fell back to a lower-priority provider.",
    ["from_provider", "to_provider"],
)
RQ_QUEUE_DEPTH = Gauge(
    "sris_rq_queue_depth",
    "Number of pending jobs in an RQ queue.",
    ["queue"],
)
RQ_FAILED_JOBS = Gauge(
    "sris_rq_failed_jobs",
    "Number of failed jobs registered for an RQ queue.",
    ["queue"],
)
RQ_WORKERS = Gauge(
    "sris_rq_workers",
    "Number of RQ workers registered with Redis.",
)


def record_email_result(provider: str, ok: bool) -> None:
    if ok:
        EMAIL_SENT_TOTAL.labels(provider=provider).inc()
    else:
        EMAIL_FAILURES_TOTAL.labels(provider=provider).inc()


def record_llm_fallback(from_provider: str, to_provider: str) -> None:
    LLM_FALLBACKS_TOTAL.labels(from_provider=from_provider, to_provider=to_provider).inc()


def _queue_names() -> list:
    return sorted({settings.EVALUATION_QUEUE_NAME, settings.TRANSCRIPTION_QUEUE_NAME})


def _update_rq_metrics() -> None:
    """Refresh RQ queue/worker gauges. Never raises: monitoring must not take
    the API down when Redis is unreachable."""
    try:
        import redis
        from rq import Queue, Worker

        connection = redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
        )
        connection.ping()

        for queue_name in _queue_names():
            queue = Queue(queue_name, connection=connection)
            RQ_QUEUE_DEPTH.labels(queue=queue_name).set(queue.count)
            RQ_FAILED_JOBS.labels(queue=queue_name).set(queue.failed_job_registry.count)

        RQ_WORKERS.set(len(Worker.all(connection=connection)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to refresh RQ metrics: %s", exc)


def metrics_endpoint() -> Response:
    """Render the Prometheus exposition of all registered metrics."""
    _update_rq_metrics()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app: FastAPI) -> None:
    """Attach HTTP instrumentation and the `/metrics` endpoint (if enabled)."""
    if not settings.METRICS_ENABLED:
        logger.info("Metrics disabled (METRICS_ENABLED=false)")
        return

    Instrumentator().instrument(app)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
    logger.info("Metrics endpoint registered at /metrics")
