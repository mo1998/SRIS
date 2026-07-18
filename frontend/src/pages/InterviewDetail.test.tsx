import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InterviewDetail from './InterviewDetail'

const apiMock = vi.hoisted(() => ({
  interviews: {
    get: vi.fn(),
    update: vi.fn(),
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
    apiMock.interviews.update.mockReset()
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

  it('updates draft interview details', async () => {
    apiMock.interviews.update.mockResolvedValue({
      data: {
        id: 1,
        title: 'Updated Support Screen',
        description: 'Updated description',
        status: 'draft',
        duration_minutes: 45,
        max_attempts: 2,
        pass_score: 75,
        created_at: '2026-07-18T00:00:00Z',
        questions: [],
      },
    })

    renderPage()

    expect(await screen.findByText('Support Screen')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: /edit/i })[0])

    const titleInput = screen.getByLabelText(/title/i)
    await userEvent.clear(titleInput)
    await userEvent.type(titleInput, 'Updated Support Screen')
    await userEvent.clear(screen.getByLabelText(/duration/i))
    await userEvent.type(screen.getByLabelText(/duration/i), '45')
    await userEvent.clear(screen.getByLabelText(/max attempts/i))
    await userEvent.type(screen.getByLabelText(/max attempts/i), '2')
    await userEvent.clear(screen.getByLabelText(/pass score/i))
    await userEvent.type(screen.getByLabelText(/pass score/i), '75')
    await userEvent.click(screen.getByRole('button', { name: /save details/i }))

    await waitFor(() => {
      expect(apiMock.interviews.update).toHaveBeenCalledWith(1, expect.objectContaining({
        title: 'Updated Support Screen',
        duration_minutes: 45,
        max_attempts: 2,
        pass_score: 75,
      }))
    })
    expect(await screen.findByText('Updated Support Screen')).toBeInTheDocument()
  })

  it('updates draft interview questions and rubric criteria', async () => {
    apiMock.interviews.update.mockResolvedValue({
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
            id: 11,
            question_text: 'Updated customer question?',
            expected_answer: 'Updated expected answer.',
            weight: 2,
            rubric_criteria: [
              {
                id: 101,
                name: 'Empathy',
                description: 'Shows customer empathy.',
                weight: 1.5,
              },
            ],
          },
        ],
      },
    })

    renderPage()

    expect(await screen.findByText('Support Screen')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: /edit/i })[1])

    const questionInput = screen.getByLabelText(/question text/i)
    await userEvent.clear(questionInput)
    await userEvent.type(questionInput, 'Updated customer question?')
    await userEvent.clear(screen.getByLabelText(/expected answer/i))
    await userEvent.type(screen.getByLabelText(/expected answer/i), 'Updated expected answer.')
    await userEvent.clear(screen.getAllByLabelText(/^weight$/i)[0])
    await userEvent.type(screen.getAllByLabelText(/^weight$/i)[0], '2')
    await userEvent.click(screen.getByRole('button', { name: /add criterion/i }))
    await userEvent.type(screen.getAllByLabelText(/^name$/i)[1], 'Empathy')
    await userEvent.type(screen.getAllByLabelText(/^description$/i)[1], 'Shows customer empathy.')
    await userEvent.click(screen.getByRole('button', { name: /save questions/i }))

    await waitFor(() => {
      expect(apiMock.interviews.update).toHaveBeenCalledWith(1, expect.objectContaining({
        questions: [expect.objectContaining({
          question_text: 'Updated customer question?',
          expected_answer: 'Updated expected answer.',
          weight: 2,
          order_index: 0,
          rubric_criteria: [expect.objectContaining({
            name: 'Clarity',
            order_index: 0,
          }), expect.objectContaining({
            name: 'Empathy',
            description: 'Shows customer empathy.',
            order_index: 1,
          })],
        })],
      }))
    })
    expect(await screen.findByText(/updated customer question/i)).toBeInTheDocument()
  })
})