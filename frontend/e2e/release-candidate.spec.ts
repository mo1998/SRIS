import { expect, test, type Page } from '@playwright/test'

const employerUser = {
  id: 1,
  email: 'employer@example.com',
  full_name: 'Employer User',
  role: 'employer',
  company_name: 'SRIS Test Co',
}

const employeeUser = {
  id: 2,
  email: 'candidate@example.com',
  full_name: 'Candidate User',
  role: 'employee',
}

const interview = {
  id: 10,
  title: 'Support Screen',
  description: 'Structured support interview',
  status: 'active',
  duration_minutes: 30,
  max_attempts: 1,
  pass_score: 70,
  created_at: '2026-07-20T00:00:00Z',
  questions: [
    {
      id: 101,
      question_text: 'How do you handle an upset customer?',
      expected_answer: 'Listen and follow up.',
      weight: 1,
      rubric_criteria: [{ id: 1, name: 'Ownership', description: 'Takes ownership', weight: 1 }],
    },
  ],
}

const candidateReport = {
  response_id: 99,
  candidate_name: 'Candidate One',
  candidate_email: 'candidate@example.com',
  interview_title: 'Support Screen',
  total_score: 92,
  passed: true,
  voice_quality: 91,
  background_quality: 90,
  face_visibility: 88,
  lighting: 87,
  dominant_emotion: 'neutral',
  confidence_score: 84,
  evaluation_provider: 'local_vllm',
  evaluation_model: 'qwen3-8b-awq',
  evaluation_status: 'completed',
  answers: [
    {
      question: 'How do you handle an upset customer?',
      score: 92,
      feedback: 'Strong answer',
      feedback_ar: 'إجابة قوية',
      emotion: 'neutral',
      evidence: { matched_criteria: ['Ownership'], missing_criteria: [], evidence: 'Candidate took ownership.' },
    },
  ],
  feedback: 'Candidate passed.',
  generated_at: '2026-07-20T00:00:00Z',
}

const auditRuns = [
  {
    id: 2,
    response_id: 99,
    provider: 'local_vllm',
    provider_version: '1.0.0',
    model_name: 'qwen3-8b-awq',
    config_hash: 'cfg-new',
    status: 'completed',
    raw_summary: { total_score: 92, answer_count: 1 },
    error: null,
    started_at: '2026-07-20T00:02:00Z',
    completed_at: '2026-07-20T00:03:00Z',
    scores: [
      {
        id: 11,
        question_answer_id: 9,
        question_id: 101,
        question: 'How do you handle an upset customer?',
        score: 92,
        feedback_en: 'Strong answer',
        feedback_ar: 'إجابة قوية',
        evidence: { matched_criteria: ['Ownership'], missing_criteria: [] },
        created_at: '2026-07-20T00:03:00Z',
      },
    ],
  },
  {
    id: 1,
    response_id: 99,
    provider: 'local_vllm',
    provider_version: '1.0.0',
    model_name: 'qwen3-8b-awq',
    config_hash: 'cfg-old',
    status: 'completed',
    raw_summary: { total_score: 89, answer_count: 1 },
    error: null,
    started_at: '2026-07-20T00:00:00Z',
    completed_at: '2026-07-20T00:01:00Z',
    scores: [],
  },
]

async function mockApi(page: Page, user = employerUser) {
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'token')
    window.localStorage.setItem('refreshToken', 'refresh')
  })
  await page.route('**/api/auth/login', async (route) => {
    await route.fulfill({ json: { access_token: 'token', refresh_token: 'refresh' } })
  })
  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({ json: user })
  })
  await page.route('**/api/interviews/', async (route) => {
    await route.fulfill({ json: [interview] })
  })
  await page.route('**/api/users/me/organization', async (route) => {
    await route.fulfill({ json: { id: 1, name: 'SRIS Test Co' } })
  })
  await page.route('**/api/users/me/memberships', async (route) => {
    await route.fulfill({ json: [{ id: 1, role: 'owner', organization_id: 1 }] })
  })
  await page.route('**/api/reports/evaluation/health', async (route) => {
    await route.fulfill({
      json: {
        provider: 'local_vllm',
        provider_version: '1.0.0',
        prompt_version: 'rubric-v1',
        config_hash: 'cfg-new',
        model_name: 'qwen3-8b-awq',
        healthy: true,
        status: 'local_vllm_available',
        fallback_provider: 'deterministic_baseline',
        checked_at: '2026-07-20T00:00:00Z',
      },
    })
  })
  await page.route('**/api/interviews/10', async (route) => {
    await route.fulfill({ json: interview })
  })
  await page.route('**/api/responses/interview/10', async (route) => {
    await route.fulfill({
      json: [
        {
          id: 99,
          candidate_name: 'Candidate One',
          candidate_email: 'candidate@example.com',
          total_score: 92,
          passed: true,
          status: 'completed',
          confidence_score: 84,
        },
      ],
    })
  })
  await page.route('**/api/invitations/10', async (route) => {
    await route.fulfill({ json: [] })
  })
  await page.route('**/api/reports/interview/10/evaluation-analytics', async (route) => {
    await route.fulfill({
      json: {
        interview_id: 10,
        completed_responses: 1,
        total_evaluation_runs: 2,
        queued_runs: 0,
        running_runs: 0,
        completed_runs: 2,
        failed_runs: 0,
        average_latest_score: 92,
        fallback_count: 0,
        provider_counts: { local_vllm: 2 },
        generated_at: '2026-07-20T00:00:00Z',
      },
    })
  })
  await page.route('**/api/reports/candidate/99', async (route) => {
    await route.fulfill({ json: candidateReport })
  })
  await page.route('**/api/reports/candidate/99/evaluations', async (route) => {
    await route.fulfill({ json: auditRuns })
  })
  await page.route('**/api/reports/my-results', async (route) => {
    await route.fulfill({ json: [candidateReport] })
  })
}

test('release candidate employer flow shows dashboard, interview detail, and audit report', async ({ page }) => {
  await mockApi(page)

  await page.goto('/employer/dashboard')
  await expect(page.getByText('Employer Dashboard')).toBeVisible()
  await expect(page.getByText('Evaluation Agent Health')).toBeVisible()
  await expect(page.getByText('local_vllm_available')).toBeVisible()

  await page.goto('/employer/interviews/10')
  await expect(page.getByText('Support Screen')).toBeVisible()
  await expect(page.getByText('Eval Runs')).toBeVisible()
  await expect(page.getByText('Avg Latest')).toBeVisible()
  await expect(page.getByText('92.0%').first()).toBeVisible()
  await expect(page.getByRole('link', { name: /view report/i })).toHaveAttribute('href', '/employer/candidate/99')

  await page.goto('/employer/candidate/99')
  await expect(page.getByText('Candidate Performance Report')).toBeVisible()
  await expect(page.getByText('Evaluation Audit Trail')).toBeVisible()
  await expect(page.getByText('Latest')).toBeVisible()
  await expect(page.getByText('+3.0 pts')).toBeVisible()
})

test('release candidate employee flow can open detailed report without re-evaluate action', async ({ page }) => {
  await mockApi(page, employeeUser)

  await page.goto('/employee/results')
  await expect(page.getByText('My Interview Results')).toBeVisible()
  await expect(page.getByRole('link', { name: /view details/i })).toHaveAttribute('href', '/employee/candidate/99')

  await page.goto('/employee/candidate/99')
  await expect(page.getByText('Candidate Performance Report')).toBeVisible()
  await expect(page.getByText('Evaluation Audit Trail')).toBeVisible()
  await expect(page.getByRole('button', { name: /re-evaluate/i })).toHaveCount(0)
})
