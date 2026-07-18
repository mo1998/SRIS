import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InterviewDetail from './InterviewDetail'

const apiMock = vi.hoisted(() => ({
  interviews: {
    get: vi.fn(),
  },
  responses: {
    list: vi.fn(),
  },
  invitations: {
    list: vi.fn(),
  },
  reports: {
    downloadInterviewPdf: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: '1' }),
  }
})

const renderPage = () => render(
  <BrowserRouter>
    <InterviewDetail />
  </BrowserRouter>
)

describe('InterviewDetail', () => {
  beforeEach(() => {
    apiMock.interviews.get.mockReset()
    apiMock.responses.list.mockReset()
    apiMock.invitations.list.mockReset()
    apiMock.interviews.get.mockResolvedValue({
      data: {
        id: 1,
        title: 'Support Screen',
        description: 'Structured support interview',
        status: 'draft',
        duration_minutes: 30,
        max_attempts: 1,
        pass_score: 70,
        created_at: '2026-07-18T00:00:00Z',
        questions: [
          {
            id: 10,
            question_text: 'How do you handle an upset customer?',
            weight: 1.5,
            rubric_criteria: [
              {
                id: 100,
                name: 'Clarity',
                description: 'Answer is clear and direct.',
                weight: 1,
              },
            ],
          },
        ],
      },
    })
    apiMock.responses.list.mockResolvedValue({ data: [] })
    apiMock.invitations.list.mockResolvedValue({ data: [] })
  })

  it('shows rubric criteria for interview questions', async () => {
    renderPage()

    expect(await screen.findByText('Support Screen')).toBeInTheDocument()
    expect(screen.getByText(/how do you handle an upset customer/i)).toBeInTheDocument()
    expect(screen.getByText(/rubric criteria/i)).toBeInTheDocument()
    expect(screen.getByText(/clarity/i)).toBeInTheDocument()
    expect(screen.getByText(/answer is clear and direct/i)).toBeInTheDocument()
  })
})