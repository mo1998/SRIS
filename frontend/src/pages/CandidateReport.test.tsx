import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CandidateReport from './CandidateReport'

const apiMock = vi.hoisted(() => ({
  reports: {
    getCandidateReport: vi.fn(),
    downloadCandidatePdf: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
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
    apiMock.reports.getCandidateReport.mockReset()
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

    renderPage()

    expect(await screen.findByText(/candidate performance report/i)).toBeInTheDocument()
    expect(screen.getByText(/local_vllm/i)).toBeInTheDocument()
    expect(screen.getByText(/qwen3-8b-awq/i)).toBeInTheDocument()
    expect(screen.getByText(/إجابة قوية/i)).toBeInTheDocument()
    expect(screen.getByText('listen')).toBeInTheDocument()
    expect(screen.getByText(/candidate described listening and following up/i)).toBeInTheDocument()
  })
})