import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CandidateReport from './CandidateReport'

const apiMock = vi.hoisted(() => ({
  reports: {
    getCandidateReport: vi.fn(),
    getCandidateEvaluations: vi.fn(),
    reevaluateCandidate: vi.fn(),
    downloadCandidatePdf: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const authMock = vi.hoisted(() => ({
  user: { role: 'employer' },
}))

vi.mock('../store/authStore', () => ({
  useAuth: () => authMock,
}))

const renderPage = () => render(
  <MemoryRouter initialEntries={["/employer/candidate/99"]}>
    <Routes>
      <Route path="/employer/candidate/:responseId" element={<CandidateReport />} />
    </Routes>
  </MemoryRouter>
)

describe('CandidateReport', () => {
  beforeEach(() => {
    authMock.user = { role: 'employer' }
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    apiMock.reports.getCandidateReport.mockReset()
    apiMock.reports.getCandidateEvaluations.mockReset()
    apiMock.reports.reevaluateCandidate.mockReset()
    apiMock.reports.downloadCandidatePdf.mockReset()
  })

  it('shows evaluation agent metadata and answer evidence', async () => {
    apiMock.reports.getCandidateReport.mockResolvedValue({
      data: {
        candidate_name: 'Candidate One',
        candidate_email: 'candidate@example.com',
        interview_title: 'Support Screen',
        total_score: 90,
        passed: true,
        voice_quality: 0,
        background_quality: 0,
        face_visibility: 0,
        lighting: 0,
        dominant_emotion: 'neutral',
        confidence_score: 50,
        evaluation_provider: 'local_vllm',
        evaluation_model: 'qwen3-8b-awq',
        evaluation_status: 'completed',
        answers: [
          {
            question: 'How do you handle an upset customer?',
            score: 90,
            feedback: 'Strong answer',
            feedback_ar: 'إجابة قوية',
            emotion: null,
            evidence: {
              matched_criteria: ['listen', 'follow up'],
              missing_criteria: ['none'],
              evidence: 'Candidate described listening and following up.',
            },
          },
        ],
        feedback: 'Overall feedback',
        generated_at: '2026-07-20T00:00:00Z',
      },
    })
    apiMock.reports.getCandidateEvaluations.mockResolvedValue({
      data: [
        {
          id: 8,
          response_id: 99,
          provider: 'local_vllm',
          provider_version: '1.0.0',
          model_name: 'qwen3-8b-awq',
          config_hash: 'def456',
          status: 'completed',
          raw_summary: { total_score: 93, answer_count: 1 },
          error: null,
          started_at: '2026-07-20T00:02:00Z',
          completed_at: '2026-07-20T00:03:00Z',
          scores: [
            {
              id: 80,
              question_answer_id: 10,
              question_id: 5,
              question: 'How do you handle an upset customer?',
              score: 93,
              feedback_en: 'Stronger answer',
              feedback_ar: 'إجابة أقوى',
              evidence: {
                matched_criteria: ['listen'],
                missing_criteria: [],
                provider_fallback_from: null,
              },
              created_at: '2026-07-20T00:03:00Z',
            },
          ],
        },
        {
          id: 7,
          response_id: 99,
          provider: 'local_vllm',
          provider_version: '1.0.0',
          model_name: 'qwen3-8b-awq',
          config_hash: 'abc123',
          status: 'completed',
          raw_summary: { total_score: 90, answer_count: 1 },
          error: null,
          started_at: '2026-07-20T00:00:00Z',
          completed_at: '2026-07-20T00:01:00Z',
          scores: [
            {
              id: 70,
              question_answer_id: 10,
              question_id: 5,
              question: 'How do you handle an upset customer?',
              score: 90,
              feedback_en: 'Strong answer',
              feedback_ar: 'إجابة قوية',
              evidence: {
                matched_criteria: ['listen'],
                missing_criteria: [],
                provider_fallback_from: null,
              },
              created_at: '2026-07-20T00:01:00Z',
            },
          ],
        },
      ],
    })
    apiMock.reports.reevaluateCandidate.mockResolvedValue({
      data: {
        id: 8,
        response_id: 99,
        provider: 'local_vllm',
        model_name: 'qwen3-8b-awq',
        status: 'completed',
        scores: [],
      },
    })

    renderPage()

    expect(await screen.findByText(/candidate performance report/i)).toBeInTheDocument()
    expect(screen.getAllByText(/local_vllm/i)).toHaveLength(3)
    expect(screen.getAllByText(/qwen3-8b-awq/i)).toHaveLength(3)
    expect(screen.getAllByText(/إجابة قوية/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('listen')).toHaveLength(3)
    expect(screen.getByText(/candidate described listening and following up/i)).toBeInTheDocument()
    expect(screen.getByText(/evaluation audit trail/i)).toBeInTheDocument()
    expect(screen.getByText(/run #8/i)).toBeInTheDocument()
    expect(screen.getByText(/latest/i)).toBeInTheDocument()
    expect(screen.getByText(/\+3\.0 pts/i)).toBeInTheDocument()
    expect(screen.getByText(/run #7/i)).toBeInTheDocument()
    expect(screen.getByText(/abc123/i)).toBeInTheDocument()

    vi.mocked(window.confirm).mockReturnValueOnce(false)
    await userEvent.click(screen.getByRole('button', { name: /re-evaluate/i }))

    expect(apiMock.reports.reevaluateCandidate).not.toHaveBeenCalled()

    vi.mocked(window.confirm).mockReturnValueOnce(true)
    await userEvent.click(screen.getByRole('button', { name: /re-evaluate/i }))

    await waitFor(() => {
      expect(apiMock.reports.reevaluateCandidate).toHaveBeenCalledWith(99)
      expect(apiMock.reports.getCandidateReport).toHaveBeenCalledTimes(2)
      expect(apiMock.reports.getCandidateEvaluations).toHaveBeenCalledTimes(2)
    })
  })

  it('hides re-evaluation action from employee candidates', async () => {
    authMock.user = { role: 'employee' }
    apiMock.reports.getCandidateReport.mockResolvedValue({
      data: {
        response_id: 99,
        candidate_name: 'Candidate One',
        candidate_email: 'candidate@example.com',
        interview_title: 'Support Screen',
        total_score: 90,
        passed: true,
        voice_quality: 0,
        background_quality: 0,
        face_visibility: 0,
        lighting: 0,
        dominant_emotion: 'neutral',
        confidence_score: 50,
        evaluation_provider: 'local_vllm',
        evaluation_model: 'qwen3-8b-awq',
        evaluation_status: 'completed',
        answers: [],
        feedback: 'Overall feedback',
        generated_at: '2026-07-20T00:00:00Z',
      },
    })
    apiMock.reports.getCandidateEvaluations.mockResolvedValue({ data: [] })

    renderPage()

    expect(await screen.findByText(/candidate performance report/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /re-evaluate/i })).not.toBeInTheDocument()
  })
})