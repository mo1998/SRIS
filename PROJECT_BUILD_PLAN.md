# SRIS Full Project Build Plan

## Operating Rules

- Implement in small, verifiable slices.
- Every functionality must have a matching verification step before moving on.
- Do not download, install, or run model weights without explicit user approval.
- Local AI must be optional, configurable, and isolated behind service interfaces.
- AI decisions must be explainable, auditable, and human-reviewable.
- Release claims must match implemented behavior.
- CI must run the same checks developers run locally.

## Target Product

SRIS will become a modern, production-ready smart interview platform for structured remote interviews. Employers can create role-based interviews, invite candidates, collect written/audio/video-backed responses, evaluate answers with local AI-assisted scoring, review evidence-linked reports, and make human-reviewed hiring decisions. Candidates get a clear, accessible, privacy-aware interview experience.

## Architecture

### Backend

- FastAPI application with modular routers and services.
- PostgreSQL as source of truth.
- Redis for caching, async job state, rate limits, and queues where needed.
- SQLAlchemy models with Alembic migrations only; no production `create_all`.
- Background worker for evaluation, email, transcription, and report generation.
- Object/file storage abstraction for uploaded audio/video/report files.
- Structured logging, request IDs, health checks, and metrics endpoints.

### Frontend

- React + TypeScript + Vite.
- Modern responsive UI with a focused SaaS/productivity feel.
- Role-aware navigation and protected routes.
- Typed API client with auth interceptor and refresh handling.
- Accessible forms, clear loading/error states, optimistic feedback where safe.
- Candidate interview room optimized for desktop and mobile.

### AI Services

- `EvaluationProvider` interface for answer scoring.
- `EmbeddingProvider` interface for semantic similarity.
- `TranscriptionProvider` interface for local speech-to-text.
- `AudioQualityProvider` interface for voice activity/noise checks.
- `VisionQualityProvider` interface for non-biometric camera quality checks.
- No emotion/personality scoring in release-critical decisions.

## Local AI Research Recommendation

No model should be downloaded or run until approved. Recommended approach:

1. Start with deterministic rubric scoring and lexical similarity as a zero-model baseline.
2. Add optional local embeddings for semantic similarity after approval.
   - Candidate: `sentence-transformers/all-MiniLM-L6-v2`.
   - Reason: small, Apache-2.0, sentence similarity fit, CPU-friendly compared with LLMs.
   - Caveat: downloads Hugging Face model weights and truncates longer text unless chunked.
3. Add optional local STT after approval.
   - Candidate: Whisper `base.en` or `small.en` for English-first release.
   - Reason: MIT license, known speech transcription baseline.
   - Caveat: needs ffmpeg and model weights; CPU may be slow on longer interviews.
4. Add optional local VAD/noise quality after approval.
   - Candidate: Silero VAD.
   - Reason: lightweight, fast CPU inference, MIT license, useful for speech presence and silence ratio.
5. Avoid emotion recognition as a scoring feature.
   - EU/workplace regulation risk is high.
   - Use camera checks only for operational quality: face visible, lighting sufficient, no video unavailable.
6. For local LLM serving, defer until core scoring is stable.
   - CPU/simple deployment: `llama.cpp` behind an OpenAI-compatible local endpoint.
   - GPU/high-throughput deployment: vLLM.
   - Both require selecting and approving specific model weights separately.

## Domain Model Roadmap

Add or refine entities:

- Organization
- TeamMembership
- InterviewTemplate
- Rubric
- RubricCriterion
- Invitation
- CandidateResponse
- QuestionAnswer
- EvaluationRun
- EvaluationScore
- ReviewerScorecard
- AuditLog
- FileAsset
- DataRetentionPolicy
- IntegrationConnection

## Implementation Phases

### Phase 0: Project Hygiene And Baseline Verification

Goals:

- Make the current branch buildable and testable.
- Establish local commands and CI foundations.
- Fix obvious API contract mismatches that block the main flow.

Implementation:

- Add backend test stack: pytest, pytest-asyncio, httpx test client, factory helpers.
- Add frontend test stack: Vitest, React Testing Library, jsdom.
- Add formatting/linting: Ruff for backend, ESLint/Prettier for frontend.
- Add typed environment validation.
- Add GitHub Actions CI for backend, frontend, Docker build, and migration check.
- Add `.env.example` coverage for all required settings.

Verification:

- `pytest` passes for initial smoke tests.
- `npm run build` passes.
- `npm run test` passes.
- `docker compose config` passes.
- CI workflow validates syntax and runs on pull request.

### Phase 1: Authentication, Accounts, And Organizations

Goals:

- Production-grade authentication and role boundaries.
- Employer organizations and team members.

Implementation:

- Add access/refresh token lifecycle with secure refresh endpoint.
- Add frontend Axios auth interceptor.
- Add password reset and email verification flow.
- Add organization creation for employers.
- Add team roles: owner, admin, recruiter, reviewer.
- Add account settings page.

Verification:

- Backend auth tests: register, login, refresh, reject invalid token, role enforcement.
- Frontend tests: protected route redirects, auth persistence, logout.
- E2E smoke: employer signup -> dashboard.

### Phase 2: Interview Builder And Templates

Goals:

- Make interview creation professional, reusable, and rubric-driven.

Implementation:

- Redesign interview builder UI.
- Add role templates for support, sales, operations, internship, junior developer, analyst.
- Add rubric criteria per question.
- Add question ordering, weights, required/optional flags, answer guidance.
- Add preview mode.
- Add draft autosave.

Verification:

- Backend tests for interview/template/rubric CRUD and authorization.
- Frontend component tests for builder validation and dynamic question editing.
- E2E: create interview from template -> edit rubric -> activate.

### Phase 3: Invitations And Candidate Pipeline

Goals:

- Reliable candidate invitation workflow and tracking.

Implementation:

- Fix invitation status transitions: pending -> sent -> accepted -> completed/expired.
- Add CSV import and validation for candidates.
- Add resend and revoke invitation controls.
- Add invitation preview and email template settings.
- Add public candidate token verification screen.

Verification:

- Backend tests for single/bulk invite, duplicates, expiry, resend, revoke.
- Email service tests using mock transport.
- Frontend tests for invite modal and CSV validation.
- E2E: employer bulk invites -> candidate opens valid token.

### Phase 4: Candidate Interview Experience

Goals:

- Modern, accessible, low-friction interview room.

Implementation:

- Add candidate consent and privacy notice before interview starts.
- Add device setup checks for camera and microphone.
- Add clear progress, timer, answer autosave, and reconnect recovery.
- Add text answers and optional audio upload.
- Add upload progress and retry behavior.
- Add mobile-responsive layout.
- Replace simulated quality labels with actual status or remove claims until implemented.

Verification:

- Backend tests for starting response, max attempts, answer submit, completion.
- Frontend tests for setup/interview/complete states.
- E2E: candidate completes interview with typed answers.
- Manual browser check for desktop/mobile layout before release.

### Phase 5: Evaluation Engine

Goals:

- Build an auditable local-first scoring system.

Implementation:

- Add evaluation provider interfaces.
- Implement deterministic baseline:
  - rubric completeness checks
  - keyword/phrase coverage
  - answer length and empty-answer handling
  - weighted score aggregation
- Add `EvaluationRun` records with provider, version, prompt/config hash, timestamps, and raw evidence.
- Add evidence-linked score explanations.
- Add human reviewer override and comments.
- Add optional local embedding provider only after user approves model download.
- Add optional local LLM provider only after user approves model download and serving choice.

Verification:

- Unit tests for scoring edge cases.
- Golden test fixtures for expected scoring behavior.
- Integration test: complete response -> evaluation run -> report.
- Regression test proving scoring is deterministic for baseline provider.

### Phase 6: Audio And Transcription

Goals:

- Support audio-backed answers without relying on cloud AI.

Implementation:

- Add audio asset validation, size/type checks, storage abstraction.
- Add optional transcription provider.
- Add transcript review/edit in employer report.
- Add VAD-based speech presence/silence ratio only after user approves model download.
- Do not use voice traits for candidate scoring.

Verification:

- Backend tests for upload validation and file persistence.
- Provider contract tests with fake transcription provider.
- Optional model tests only after approval and explicit model setup.

### Phase 7: Reports, Ranking, And Reviewer Workflow

Goals:

- Make reports evidence-rich and useful for human hiring decisions.

Implementation:

- Candidate report: question-by-question scores, rubric criteria, evidence snippets, transcript/audio links.
- Interview report: ranking, pass rate, score distribution, reviewer status.
- Reviewer scorecards and comments.
- Human decision states: shortlisted, rejected, needs review, hired.
- PDF and CSV exports.

Verification:

- Backend report tests for authorization, ranking, aggregation, export.
- Frontend tests for report rendering and filters.
- Snapshot or PDF smoke test ensuring export file is generated.

### Phase 8: Trust, Compliance, And Security

Goals:

- Make SRIS acceptable to real hiring teams.

Implementation:

- Candidate consent capture.
- Data retention policies.
- Audit logs for sensitive actions.
- Model card page for enabled AI providers.
- Human-in-the-loop disclosure.
- Candidate data export/delete request workflow.
- Rate limiting and security headers.
- Access logs and report view tracking.
- Remove or clearly isolate emotion recognition from hiring scoring.

Verification:

- Tests for audit log creation.
- Tests for retention policy behavior.
- Security checks in CI.
- Manual compliance checklist review before release.

### Phase 9: Modern UI Rebuild

Goals:

- Replace Bootstrap-default feel with a polished, fast, domain-specific SaaS interface.

Implementation:

- Define design tokens: color, spacing, type scale, shadows, borders.
- Build app shell: sidebar/topbar, responsive nav, role-aware actions.
- Build dashboard with dense operational metrics.
- Build consistent forms, tables, empty states, modals, toasts, and status badges.
- Optimize loading, route splitting, and bundle size.
- Maintain accessibility: focus states, labels, contrast, keyboard flows.

Verification:

- Frontend build and tests.
- Lighthouse/accessibility checks where available.
- Manual responsive QA for employer dashboard, builder, interview room, reports.

### Phase 10: Integrations And Automation

Goals:

- Make SRIS fit real hiring workflows.

Implementation:

- Webhooks for interview completed, candidate scored, invitation completed.
- CSV export/import.
- Slack/Teams notification bridge.
- First ATS integration via webhook/Zapier-compatible API.
- Calendar scheduling for follow-up interviews.

Verification:

- Contract tests for webhook payloads.
- Retry/idempotency tests.
- Integration mock tests.

### Phase 11: CI/CD And Deployment

Goals:

- Reliable automated validation and deployment.

Implementation:

- GitHub Actions workflows:
  - backend lint/test
  - frontend lint/test/build
  - Docker image build
  - Alembic migration check
  - dependency/security scan
  - deploy workflow with environment approvals
- Add staging and production deployment docs.
- Add versioned Docker images.
- Add rollback procedure.
- Add health checks and smoke test after deploy.

Verification:

- CI passes on pull request.
- Docker images build.
- Staging deploy runs migrations and health checks.
- Rollback command documented and tested on staging.

## Testing Strategy

Backend:

- Unit tests for services and scoring.
- API integration tests with transactional test database.
- Permission tests for every protected route.
- Migration tests.
- File upload/report generation tests.

Frontend:

- Component tests for forms and critical states.
- API mocking for page flows.
- Build/typecheck on every CI run.
- E2E smoke tests for employer and candidate happy paths.

AI:

- Provider contract tests using fake providers.
- Golden scoring fixtures for deterministic baseline.
- Optional local model tests only after approved model setup.
- Drift/calibration tests when real pilot data exists.

Deployment:

- Docker Compose config validation.
- Container health checks.
- Post-deploy smoke tests.

## Immediate Next Implementation Slice

Start with Phase 0 because everything else depends on reliable verification.

First slice:

1. Add backend pytest infrastructure.
2. Add tests for health, auth register/login, and current interview creation contract.
3. Fix any failing schema/model issues exposed by those tests.
4. Add frontend Vitest infrastructure.
5. Add a smoke test for route rendering.
6. Add GitHub Actions CI running backend tests and frontend build/test.

Required verification before moving to Phase 1:

- Backend tests pass locally.
- Frontend tests/build pass locally.
- CI workflow file validates structurally.
- `git diff --check` passes.

## Model Approval Gates

Before any model is downloaded or run, ask for explicit approval with:

- Model name and source.
- License.
- Approximate download size.
- Expected CPU/GPU/RAM requirements.
- Purpose in SRIS.
- Whether it sends telemetry or needs account tokens.
- How to disable/remove it.
