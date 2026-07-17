# SRIS Release Research And Domination Playbook

## Executive Positioning

SRIS should not launch as a generic "AI interview platform." That space is already crowded by mature vendors with ATS integrations, security certifications, scheduling, and assessment libraries. SRIS has a stronger opening if it positions as:

> A structured, auditable remote interview system for small and mid-sized hiring teams that need consistent candidate evaluation, fast screening, and transparent AI-assisted scoring without enterprise implementation overhead.

The winning wedge is not emotion detection. The winning wedge is trust: structured interviews, explainable scoring, candidate-friendly workflow, compliance posture, and simple deployment.

## Current SRIS Baseline

Implemented today:

- Employer registration/login and role-protected dashboard.
- Interview creation with questions, expected answers, duration, attempts, pass score, and weights.
- Interview lifecycle: draft, active, completed.
- Single and bulk candidate invitations with unique tokens.
- Candidate interview room with webcam preview, typed answers, optional audio recording, and question progress.
- Response completion and automated scoring.
- OpenAI-based answer evaluation with keyword fallback.
- Candidate ranking, candidate reports, employer reports, and PDF export.
- Docker deployment with backend, frontend, PostgreSQL, Redis, Nginx, and migrations.

Current gaps to resolve before a serious release:

- Quality and emotion metrics are simulated in the frontend, not actually analyzed.
- Auth is not globally wired into every Axios request in the API service.
- Invitation status is created as `pending` but initial send does not update `sent_at`/`sent`.
- The frontend submits quality/emotion payloads as JSON objects, while backend endpoints currently declare scalar query parameters.
- AI scoring lacks rubric controls, audit logs, calibration data, and bias/adverse-impact reporting.
- No ATS integrations, scheduling, interview templates, team collaboration, or reviewer scorecards.
- No compliance artifacts: privacy notice, candidate consent, model card, data retention controls, audit export, adverse-impact dashboard.

## Market Reality

Competitor patterns from HireVue, Spark Hire, CodeSignal, and HackerRank:

- Mature platforms sell outcomes: faster screening, consistent evaluation, reduced recruiter workload, better candidate experience, and hiring quality.
- Buyers expect the product to fit into hiring workflows, not sit outside them. ATS integrations and reporting exports matter.
- AI is now framed as structured assistance, not magic. Strong vendors emphasize rubrics, scorecards, transcripts, integrity signals, and explainability.
- Technical hiring platforms are moving toward real-world tasks, AI fluency evaluation, and auto-filled scorecards from transcripts/code/tests.
- SMB-focused tools compete on speed, simplicity, price transparency, and replacing spreadsheets/email chaos.

Implication: SRIS should avoid claiming it replaces recruiters or objectively detects talent from facial emotion. It should claim it standardizes interviews, captures structured evidence, assists scoring, and gives humans better review material.

## Compliance And Trust Requirements

AI hiring tools create regulatory and reputational risk. SRIS should design for this from day one.

Key considerations:

- The EU AI Act treats AI systems used for recruitment, candidate evaluation, filtering, or ranking as high-risk in many cases. High-risk systems need risk management, technical documentation, record keeping, human oversight, accuracy/robustness/cybersecurity controls, and deployer instructions.
- The EU AI Act also treats emotion recognition in workplace contexts as highly sensitive, with prohibitions or heavy restrictions depending on context. Do not make emotion analysis a core scoring factor for release.
- NYC Local Law 144 requires covered automated employment decision tools to have a bias audit within one year of use, public audit summary, and required candidate/employee notices.
- EEOC-style adverse impact concerns apply whenever algorithms influence employment decisions. Employers need evidence that selection rates are monitored across protected groups where legally and appropriately collected.
- Marketing claims must be precise. Do not claim "bias-free," "detects honesty," "reads confidence," or "guarantees best candidates."

Release-safe trust stance:

- Human-in-the-loop by default.
- AI produces suggestions, scores, rationales, and evidence links; humans make decisions.
- Emotion/quality signals are optional environment diagnostics, not pass/fail scoring.
- Every score must be traceable to question, rubric, expected answer, candidate answer, model version, and evaluator prompt/version.

## Product Strategy

### Beachhead Customer

Start with small and mid-sized companies hiring for high-volume entry-level, operations, support, sales, and internship roles. These teams feel application overload but cannot afford enterprise platforms or complex implementation.

Avoid starting with regulated enterprise, government, healthcare, or high-stakes technical hiring until compliance and integrations mature.

### Differentiated Promise

SRIS should own this sentence:

> Turn messy first-round interviews into consistent, reviewable, explainable candidate evidence in minutes.

### Product Pillars

1. Structured interviews: templates, rubrics, scoring criteria, question weights, calibration.
2. Candidate experience: mobile-first, accessible, transparent, low-stress setup checks, clear privacy consent.
3. Evaluator productivity: AI summaries, per-answer evidence, reviewer notes, side-by-side comparison, ranking.
4. Trust and compliance: audit logs, adverse-impact export, human override, retention controls, model cards.
5. Workflow fit: ATS/email/calendar integrations, CSV import/export, webhooks, Slack/Teams notifications.

## Must-Build Before Public Launch

### P0: Make Existing Flows Reliable

- Fix API/client contract mismatches for quality and emotion submission.
- Add Axios auth interceptor and token refresh behavior.
- Add end-to-end smoke tests for employer create -> activate -> invite -> candidate complete -> employer report.
- Replace simulated metrics labels with "preview/demo" or remove them from release scoring.
- Ensure invitations transition to `sent` and set `sent_at` after email dispatch.
- Add robust error states and empty states across the frontend.
- Add database migrations as the only schema path; avoid relying on `create_all` in production.

### P1: Release-Grade Interview Product

- Interview templates by role: customer support, sales, junior developer, operations, data analyst, internship.
- Rubric builder with criteria per question: accuracy, completeness, communication, examples, role relevance.
- AI score explanation with evidence snippets from candidate answers.
- Reviewer scorecards and comments separate from AI scoring.
- Candidate transcript/audio playback in reports.
- CSV import for candidates and CSV export for results.
- Candidate consent screen before camera/mic and AI evaluation.

### P2: Trust Layer

- Audit log: who created interview, changed rubric, invited candidate, viewed report, changed decision.
- Model/prompt version tracking for every AI score.
- AI confidence and "needs human review" flags.
- Data retention settings per employer.
- Candidate data deletion/export workflow.
- Bias/adverse-impact reporting export for customers who collect demographic data lawfully.
- Security basics: rate limiting, password reset, email verification, stronger secret management, object storage for uploads.

### P3: Growth And Moat

- ATS integrations: Greenhouse, Lever, Ashby, Workable, BambooHR, Zoho Recruit.
- Calendar scheduling for follow-up interviews.
- Webhooks and public API.
- Organization/team management with roles: owner, recruiter, hiring manager, viewer.
- Benchmarking: compare candidates against calibrated historical rubrics, not opaque global scores.
- Interview analytics: completion rate, drop-off, average score, time-to-complete, pass rate by role/source.

## AI Feature Direction

Prioritize these AI capabilities:

- Answer evaluation against explicit rubric and expected answer.
- Interview summary for hiring managers.
- Candidate strengths/risks with evidence links.
- Suggested follow-up questions for live interviews.
- Rubric quality checker: warns when questions are vague, biased, illegal, or not role-related.
- Score calibration: compare AI score with human reviewers and surface drift.

Deprioritize or avoid for launch:

- Emotion-based candidate scoring.
- Personality inference from face/voice.
- Fully automated rejection without human review.
- Claims about deception, honesty, confidence, or cultural fit inferred from biometrics.

## Go-To-Market Plan

### Launch Offer

- Free trial for up to 3 active interviews and 25 candidate responses.
- Paid SMB plan based on active jobs/interviews and response volume.
- White-glove setup for first 10 design partners.
- Promise: launch a structured first-round interview in under 15 minutes.

### Ideal Initial Channels

- Founder-led outreach to SMB recruiters, staffing agencies, coding bootcamps, universities, and internship programs.
- LinkedIn content around structured interviewing and AI hiring compliance.
- Product Hunt/Hacker News only after the demo flow is polished and self-serve.
- Partnerships with small ATS/HR consultants who implement hiring processes for SMBs.

### Sales Demo Narrative

1. Create a role-specific interview from a template.
2. Edit rubric and expected answers.
3. Bulk invite candidates.
4. Candidate completes a clean interview flow.
5. Employer gets ranked, explainable reports with answer-level evidence.
6. Export/share results and move candidates forward.

## Metrics That Matter

Product activation:

- Time from signup to first activated interview.
- Percentage of employers who invite at least one candidate.
- Candidate completion rate.
- Time from candidate completion to reviewed decision.

Quality and trust:

- Human reviewer agreement with AI score.
- Percentage of AI scores overridden by reviewers.
- Percentage of reports marked "useful" by hiring managers.
- Candidate satisfaction after interview completion.
- Support tickets per 100 interviews.

Business:

- Active employers per week.
- Responses per employer.
- Conversion from trial to paid.
- Retention by monthly hiring cycle.
- Cost per evaluated candidate, including AI spend.

## Suggested 90-Day Roadmap

Days 1-15:

- Stabilize existing full flow and fix API mismatches.
- Remove or relabel simulated AI/quality features.
- Add auth interceptor, password reset, email verification, and basic smoke tests.

Days 16-35:

- Build rubric-based scoring and evidence-linked AI reports.
- Add candidate consent/privacy screen and retention settings.
- Add CSV import/export and role templates.

Days 36-60:

- Add reviewer scorecards, audit logs, model/prompt versioning, and report sharing.
- Run 5-10 design partner pilots.
- Measure AI/human score agreement and candidate completion friction.

Days 61-90:

- Polish onboarding and demo data.
- Add first ATS integration or Zapier/webhook bridge.
- Prepare public launch with compliance-friendly messaging, security docs, and case-study style pilot results.

## Release Messaging

Use:

- "AI-assisted structured interview evaluation."
- "Explainable scoring tied to your rubric."
- "Human-reviewed candidate evidence."
- "Built for consistent first-round screening."
- "Designed with auditability and candidate transparency."

Avoid:

- "Bias-free hiring."
- "Emotion detects candidate quality."
- "Automatically identifies the best candidate."
- "Replaces recruiters."
- "Cheat-proof."

## Research Sources Consulted

- HireVue platform positioning: https://www.hirevue.com/platform
- Spark Hire hiring platform positioning: https://www.sparkhire.com/
- CodeSignal AI-native skills validation: https://codesignal.com/
- HackerRank Interview positioning: https://www.hackerrank.com/products/interview/
- NYC Automated Employment Decision Tools guidance: https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page
- EU AI Act high-level summary: https://artificialintelligenceact.eu/high-level-summary/
