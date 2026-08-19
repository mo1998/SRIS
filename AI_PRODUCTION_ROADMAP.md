# SRIS AI Production Roadmap

Planned best-practice steps for the Smart Remote Interview System (SRIS) AI stack, adapted from [h9-tec/production-ai-stack](https://github.com/h9-tec/production-ai-stack). That repo is an opinionated map of what actually runs in production — this document turns it into an ordered, verifiable plan for SRIS.

Principles borrowed from the source (and already mostly true of SRIS):

1. **The model is maybe 20% of the system.** Prompt/rubric quality, orchestration, and evals decide whether evaluation works.
2. **Every layer needs an eject path.** Open-source core + managed escape hatch. SRIS already does this for the LLM (local vLLM ↔ cloud OpenAI-compatible) and for email (Mailpit ↔ SMTP ↔ Resend).
3. **If you cannot replay it, you cannot debug it.** SRIS already persists `evaluation_runs` with provider, model, `config_hash`, per-answer evidence, and a deterministic fallback. Keep this discipline.
4. **Evals before dashboards.** SRIS has analytics dashboards; it does not yet have a golden eval set that gates prompt/provider changes.

---

## Current SRIS AI stack snapshot

| Layer | Today | Notes |
|---|---|---|
| Inference serving | vLLM (OpenAI-compatible, profile-gated, GPU) | Matches the reference default |
| LLM gateway / routing | None — direct calls to local or cloud endpoint | Provider chosen by env vars + per-organization override (feature: this doc's sibling) |
| Fallback | Deterministic rubric-aware `BaselineEvaluationProvider` | Scored with keyword coverage + length + rubric text |
| STT | faster-whisper (multilingual, int8 CPU, VAD) | Matches reference default |
| Emotion analysis | DeepFace (optional, operational metadata only) | Not evaluation evidence |
| Orchestration | RQ worker + in-process background tasks | Fire-and-forget, stateless jobs — fine for current scope |
| Observability | Prometheus + Alertmanager + Loki + Grafana + node-exporter (prod profile) | Metrics exist; no LLM tracing, no eval telemetry |
| Structured output | LLM asked for "compact JSON"; parsed with `parse_llm_json` | No constrained decoding / schema enforcement |
| Guardrails | Upload validation, anti-cheating, request limits, production config guardrails | No PII masking on LLM payloads |
| Caching / cost | None beyond vLLM prefix cache | No routing, no semantic cache |
| Evals | `test_evaluation_service.py` unit tests | No golden answer set, no regression harness |

---

## Gap analysis against production-ai-stack layers

| Reference layer | SRIS gap | Priority |
|---|---|---|
| Gateway and routing | No single URL in front of providers; org override is static, not routed | High |
| Structured output | JSON contract is prompt-enforced, not schema-enforced | Medium |
| Observability and evals | No Langfuse-style tracing; no golden set; fallback not measured | High |
| Guardrails and security | PII (candidate answers) sent to cloud provider unmasked | High |
| Caching and cost control | No routing of cheap/easy answers to small model | Medium |
| Retrieval and storage | N/A for current feature set (no RAG) — ignore pgvector until a knowledge base exists | Skip |
| Document ingestion / chunking | N/A | Skip |
| Durable execution (Temporal) | RQ is fine for current jobs; revisit if multi-step agent pipelines appear | Later |
| Arabic / multilingual | Whisper already multilingual; LLM prompt is bilingual (en/ar feedback) | Monitor, see §9 |

---

## Roadmap (ordered)

### Phase 1 — Per-organization provider selection (in progress)

Goal: employer chooses local or cloud evaluation provider from the UI; no project (`.env`/docker-compose) changes required.

- [x] `organizations` table gains `evaluation_provider`, `evaluation_model`, `evaluation_base_url`, `evaluation_api_key`.
- [x] `GET /api/users/me/organization` returns the selection; `GET /api/users/me/organization/providers` lists what the system has enabled.
- [x] `PATCH /api/users/me/organization/settings` lets owner/admin change the selection.
- [x] Evaluation service resolves provider per organization; fallback + `config_hash` + `evaluation_runs` record what was actually used.
- [x] Employer dashboard shows the selected provider; health card reflects the organization's active provider/model.

Acceptance criteria: an employer can switch an interview batch between local and cloud evaluation without touching environment files; each `evaluation_run` records the effective provider; unauthorized members cannot change settings.

### Phase 2 — Gateway layer (LiteLLM) for a single model URL

Goal: one OpenAI-compatible URL in front of local vLLM and cloud providers so fallback, routing, budgets, and spend tracking live in one place.

Steps:
1. Stand up LiteLLM as a docker service (gateway profile), pointed at the local vLLM endpoint and the configured cloud endpoint.
2. Reconfigure `LOCAL_LLM_BASE_URL` / `CLOUD_LLM_BASE_URL` to the gateway virtual model names; keep direct endpoints as the break-glass path.
3. **Pin the exact LiteLLM version** and install from a hash-verified lockfile. Do not auto-upgrade (the 2026 supply-chain incident in this exact package is the reason — see source repo §3).
4. Keep the per-organization provider selection from Phase 1; map org selection to gateway model routing.

Acceptance criteria: evaluation traffic flows through the gateway; a provider failure triggers the deterministic fallback chain exactly as today; gateway latency is added to the Prometheus dashboards.

### Phase 3 — Structured output for evaluation

Goal: replace "prompt says return JSON" with schema-enforced output so scoring never fails to parse.

Steps:
1. On the local side, enable xgrammar-guided JSON decoding in vLLM (the model config already requests JSON; constrain it server-side).
2. Define a Pydantic schema for the evaluation result (`score`, `feedback_en`, `feedback_ar`, `matched_criteria`, `missing_criteria`, `evidence`).
3. For cloud providers, use native structured outputs when available; otherwise keep the current retry/parse path but validate against the schema before accepting.
4. Keep the free-text-reasoning → constrained-final-answer pattern: do not constrain the whole generation, only the final block.

Acceptance criteria: zero evaluation runs fail because of JSON parse errors; `parse_llm_json` becomes a validation layer instead of a recovery path.

### Phase 4 — Golden eval set + CI regression gate

Goal: every prompt/provider/model change runs against a labeled golden set before merge.

Steps:
1. Curate 50–200 hand-labeled question/answer/score triples from real SRIS traffic (bilingual; Arabic answers included). Store as a versioned fixture under `backend/tests/fixtures/eval_golden.json`.
2. Write an eval harness that runs the current provider against the golden set and emits score deltas (per-provider and vs. the deterministic baseline).
3. Wire it into `scripts/release_check.sh` and the CI pipeline (`.github/workflows/ci.yml`) as a non-blocking report first, blocking once numbers stabilize.
4. Track a `provider_quality` histogram in Prometheus (score delta vs. human label) sampled from production re-evaluations.

Acceptance criteria: a prompt change cannot merge without a golden-set delta; regressions on Arabic answers are visible in CI before release.

### Phase 5 — PII and guardrails on LLM payloads

Goal: candidate data sent to any LLM (especially cloud) is minimized and auditable.

Steps:
1. Add a masking step before payload construction in `evaluation_service` / `transcription_service`: strip emails, phone-like patterns, and names from the candidate answer before it reaches the provider (keep the reference copy in the DB).
2. Log masking decisions to the audit trail per `evaluation_run`.
3. Record whether the payload left the host (cloud vs local) in the evaluation run metadata so compliance questions can be answered from data.
4. Decide and document fail-open vs fail-closed behavior for masking; test the failure path.

Acceptance criteria: candidate PII is never sent to a cloud endpoint unmasked; compliance review can list every cloud-touched evaluation.

### Phase 6 — Cost control and model routing

Goal: cheaper evaluations without quality loss, using routing instead of negotiation.

Steps:
1. At the gateway, classify evaluation requests and route the deterministic-cheap majority to a small local model; escalate only when rubric criteria demand it.
2. Add cost-per-request telemetry next to quality metrics (source repo's rule: cost and quality must share a dashboard).
3. Exploit stable prompt prefixes (the system prompt is already static) so vLLM prefix caching does the free work.
4. Shorten `max_tokens` now that output is structured; output tokens cost multiples of input.

Acceptance criteria: cost-per-evaluation is visible on a dashboard alongside pass-rate and judge agreement; no quality regression on the golden set.

### Phase 7 — Tracing (Langfuse) for replayable evaluations

Goal: replay any evaluation run — prompt version, model, retrieval context, decision — from a trace.

Steps:
1. Self-host Langfuse (Postgres + ClickHouse + Redis + S3, per reference stack) or start with the OSS core.
2. Instrument `evaluate_answer` for each provider: trace spans per answer, keyed by `evaluation_run_id`, with prompt version and config hash.
3. Wire the existing audit UI to link a trace for each `evaluation_run` row.
4. Add a PII policy for trace payloads (mask at the SDK boundary, short retention) before enabling on live traffic.

Acceptance criteria: any `evaluation_run` is replayable from its trace; traces carry no unmasked PII.

### Phase 8 — Durable execution only if agents arrive

Do **not** adopt Temporal/Restate now. SRIS jobs are stateless and short (transcription, evaluation, reminders). Revisit only if evaluation grows into multi-step agent pipelines (e.g., multi-stage review, retrieval-augmented scoring).

If it happens: move each side-effecting step into an activity with an idempotency key (a re-run must not double-queue evaluations).

---

## Language notes (Arabic)

SRIS evaluates Arabic answers and produces bilingual feedback, so the source repo's Arabic section applies:

- **Eval sets must include dialect-heavy Arabic**, not just MSA; the golden set in Phase 4 must include Gulf/Egyptian-style answers.
- **Quantization regressions hit Arabic first.** If the local model is quantized (e.g., AWQ), the golden set must gate it; an INT4 model can pass English and degrade Arabic.
- **Arabic tokenizer fertility multiplies cost** — include Arabic answers when measuring cost-per-evaluation in Phase 6.
- Whisper already handles Arabic transcription; keep it in the golden set for the transcription layer too.

## Things we deliberately skip

- Dedicated vector DB / pgvector / RAG: no document knowledge base in scope. Revisit only when interviews need retrieval-grounded scoring.
- Semantic caching: false-positive caching destroys trust in scoring; earn it with traffic data first.
- Multi-agent swarms: evaluation is a pipeline, not an open-ended agent task.
- Fine-tuning: exhaust prompting, routing, and the golden set before training a model.
- GraphRAG and embedding-serving changes: no corpus today.

## Keeping the source repo current

The reference repo is revised regularly; re-read its "Things I would skip" and gateway sections before each phase starts. Claims there are dated (last major revision July 2026); revalidate vendor claims against your own evals.