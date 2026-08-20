# Smart Remote Interview System (SRIS)

> **The Enterprise-Grade, Local-First AI Remote Interviewing Platform.**  
> Conduct structured remote interviews, capture high-quality candidate responses, and leverage evidence-linked AI evaluations — with total data privacy and zero vendor lock-in.

---

## 🌟 Why SRIS?

SRIS transforms remote hiring by combining automated interview workflows with local-first AI evaluation and proctoring controls. Built for organizations that demand precision, security, and total ownership over candidate data, SRIS provides a seamless end-to-end interviewing experience.

* **🛡️ Total Data Privacy & Sovereignty**: Run fully self-hosted. Keep candidate video, audio transcripts, and evaluation data completely on your infrastructure with local LLMs (vLLM / Qwen) and local AI workers.
* **🤖 Objective, Evidence-Linked Evaluation**: AI evaluations grade candidate answers directly against your custom rubric criteria, citing exact evidence from responses. Built-in deterministic fallbacks ensure evaluation never halts.
* **🎙️ Automated Multilingual Transcription**: Speech-to-text powered by Whisper (99 languages) transcribes audio and video answers automatically upon candidate submission.
* **🎭 Deep Behavioral & Environment Insights**: Gain operational insights into candidate response quality, background noise, speech clarity, and facial emotion timeline analysis.
* **🔒 Enterprise Anti-Cheating Controls**: Protect assessment integrity with copy/paste blocking, right-click restrictions, window blur/focus tracking, and forced full-screen modes.
* **⚡ Real-Time Hiring Collaboration**: WebSockets power instant updates across your hiring team — view incoming candidate submissions, AI evaluations, and reviewer decisions as they happen.

---

## 🔥 Key Features

### 🏢 Organizations & Multi-Role Governance
* **Multi-Tenant Architecture**: Isolate interviews, responses, candidates, reports, and audit logs per organization.
* **Role-Based Access Control (RBAC)**: Fine-grained permissions across **Owner**, **Admin**, **Recruiter**, **Reviewer**, and **Candidate** roles.
* **Candidate Portal**: Self-service portal for candidates to review permitted feedback and results securely.

### 📝 Smart Interview Builder & Rubrics
* **Lifecycle Management**: Seamless workflow transitions: Draft ➔ Active ➔ Completed ➔ Cancelled.
* **Template Library**: Pre-built interview templates for rapid candidate assessment creation.
* **Weighted Evaluation Criteria**: Define weighted questions, expected answer benchmarks, and granular rubric guidelines.

### ✉️ Candidate Pipeline & Automated Reminders
* **Flexible Invites**: Send individual or bulk email invitations with tokenized access links.
* **Automated Expiry & Reminders**: Configurable background sweep handles expiration, resend cooldowns, and automated follow-up reminder emails.
* **SMTP & Preview Integration**: Email preview tools and real-time email delivery diagnostics.

### 🎯 Proctored Candidate Experience
* **Server-Authoritative Timer**: Strict server-side duration control with configurable grace periods to prevent time manipulation.
* **Multi-Format Response Capture**: Typed text, audio recordings, and video file submissions with content-signature and size validation.
* **Integrity & Proctoring Suite**: Blocks clipboard copy/paste, restricts right-clicking, tracks window focus/tab switches, and records integrity events.
* **Environment Quality Scoring**: Automated feedback on audio environment, lighting, background clarity, and candidate positioning.

### 🤖 Hybrid AI Evaluation Engine
* **Local-First & Cloud Flexibility**: Choose between fully local LLMs (vLLM/Qwen), cloud providers (OpenAI-compatible), or a hybrid blend configurable per organization.
* **Deterministic Fallback Evaluator**: Automatic rubric-aware fallback logic guarantees candidates are scored even if the LLM endpoint is unreachable.
* **Evidence-Linked Feedback**: Detailed score breakdowns, bilingual feedback, and direct candidate answer quote citations.
* **Self-Hosted Tracing**: Integrated with Langfuse for full LLM trace auditability and performance analytics.

### 📊 Reviewer Command Center & Reporting
* **Interactive Scorecards**: Team scorecards with strengths, weaknesses, overall scoring, and reviewer notes.
* **Decision Workflows**: Record pass / fail / review decisions with reviewer attribution and real-time team notification.
* **Exportable Reports**: Generate candidate PDF reports, export response analytics to CSV, and inspect evaluation audit histories.

### 🔄 Webhooks & Enterprise Operations
* **Signed Webhooks**: Export event streams (`interview.completed`, `evaluation.completed`, `decision_made`, etc.) with HMAC signatures and exponential backoff retry logic.
* **Compliance Ready**: Built-in GDPR data export/deletion requests and detailed system audit logs.
* **Observability & Health**: Native Prometheus metrics (`/metrics`) and comprehensive operational health checks.

---

## ⚡ Quick Start & Installation

SRIS is fully containerized with Docker Compose for effortless one-command deployment.

### Prerequisites
* [Docker Desktop](https://www.docker.com/) or Docker Engine (v20.10+) with Docker Compose V2.

### 1. Configure Environment
Clone the repository and copy the example environment file:
```bash
cp .env.example .env
```
*(Optional)* Edit `.env` to set your custom `SECRET_KEY`, database credentials, or email server settings.

### 2. Deploy Services
Run the automated deployment script to build containers, set up the database schema, and launch the application:

```bash
./deploy.sh
```

Alternatively, launch directly via Docker Compose:
```bash
docker compose up -d
```

### 3. Access SRIS
Once services start, access the platform via your browser:

* **Web Platform (Frontend)**: [http://localhost](http://localhost) (or configured `FRONTEND_PORT`)
* **Interactive API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Email Testing Console (Mailpit)**: [http://localhost:8025](http://localhost:8025)

---

## 🛠️ Advanced Deployment Options

### Running Background AI Workers
To run the durable background queue worker for evaluations, speech transcription, and emotion processing:

```bash
docker compose --profile worker up -d
```

### Running Local LLM (vLLM Profile)
To host a completely private, GPU-accelerated local model (Qwen 8B) for AI evaluations:

```bash
LOCAL_MODEL_PATH=./models/qwen3-8b-awq \
docker compose --profile model up -d local-model
```

### Production Deployment
For production setups with SSL termination (Let's Encrypt / Certbot), database persistence, health auto-healing, and observability:

```bash
./deploy.sh production
```

---

## 🚀 How to Use SRIS

```
 ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
 │   1. Employer   │  ───> │  2. Candidate   │  ───> │   3. AI Engine  │
 │ Build & Invite  │       │ Take Interview  │       │ Transcribe & Eval│
 └─────────────────┘       └─────────────────┘       └─────────────────┘
                                                              │
                                                              ▼
                           ┌─────────────────┐       ┌─────────────────┐
                           │   5. Export     │  <─── │   4. Reviewer   │
                           │  PDF / CSV      │       │ Score & Decide  │
                           └─────────────────┘       └─────────────────┘
```

1. **Create an Organization & Interview**: Log in as an employer, set up your organization, and build an interview template with questions and rubric criteria.
2. **Invite Candidates**: Send token-secured invitations via single or bulk email dispatch. Candidates receive direct, secure links.
3. **Candidate Response Flow**: Candidates enter the proctored interview room, record video/audio or type answers, while integrity tracking enforces assessment rules.
4. **Automated AI Processing**: Upon completion, SRIS automatically transcribes spoken responses (Whisper), calculates facial emotion timelines (DeepFace), and executes rubric evaluations (vLLM / OpenAI).
5. **Review & Decision**: Hiring teams view real-time candidate scorecards, analyze cited answer evidence, record hiring decisions (Pass/Fail/Review), and download PDF reports.

---

## ⚙️ Key Configuration Reference

| Environment Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | JWT signing key (Min 32 characters in production) | Required |
| `DEBUG` | Enable/disable debug modes and safety guardrails | `True` |
| `DATABASE_URL` | PostgreSQL connection string | Container default |
| `REDIS_URL` | Redis connection for pub/sub and background workers | Container default |
| `EVALUATION_QUEUE_BACKEND` | Evaluation job worker engine (`rq` or `in_memory`) | `rq` |
| `EMOTION_ANALYSIS_PROVIDER` | Emotion engine (`deepface`, `disabled`, or `fake`) | `deepface` |
| `TRANSCRIPTION_PROVIDER` | Speech-to-text provider (`whisper`, `disabled`, or `fake`) | `whisper` |
| `WHISPER_MODEL_SIZE` | Whisper model size (`tiny`, `base`, `small`, `medium`) | `small` |
| `INTEGRITY_BLOCK_CLIPBOARD` | Restrict copy/paste & right-click during interviews | `true` |
| `INTEGRITY_ENFORCE_FULLSCREEN`| Require fullscreen mode during candidate responses | `false` |

---

## 🏗️ System Architecture Overview

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, React Bootstrap | Modern, responsive candidate & employer web application |
| **Backend API** | FastAPI, Python 3.10+, Pydantic, SQLAlchemy | High-performance RESTful API & WebSocket backend |
| **Database** | PostgreSQL 15 | Relational data store for interviews, users, and audit logs |
| **Cache & Queue** | Redis 7 + RQ Worker | Pub/Sub messaging and async background job execution |
| **Speech-to-Text** | faster-whisper (CTranslate2) | Multilingual, fast CPU/GPU speech transcription |
| **Emotion Engine** | DeepFace / OpenCV | Privacy-safe, facial emotion timeline analysis |
| **AI Evaluator** | vLLM / OpenAI / Hybrid API | Rubric-based scoring & evidence extraction engine |
| **Reverse Proxy** | Nginx | Static asset serving, SSL termination, and request routing |

---

## 📡 Core API Summary

The backend exposes a fully documented OpenAPI specification accessible at `/docs` when running.

* **`/api/auth`**: Registration, authentication, JWT token refresh, and password recovery.
* **`/api/interviews`**: Interview CRUD, template management, and question/rubric configuration.
* **`/api/invitations`**: Individual/bulk invite dispatch, link verification, and reminder management.
* **`/api/responses`**: Proctored response submission, media uploads, integrity telemetry, and timers.
* **`/api/reports`**: Scorecard generation, AI evaluation results, candidate analytics, and PDF exports.
* **`/api/webhooks`**: Enterprise event subscription management and delivery logs.
* **`/api/ws`**: Authenticated real-time WebSocket connection for live UI updates.

---

## 📜 License & Support

SRIS is proprietary enterprise software designed for local-first deployment. For configuration support, custom integrations, or platform inquiries, refer to internal documentation or system administrators.
