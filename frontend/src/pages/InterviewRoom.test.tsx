import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InterviewRoom from './InterviewRoom'

const apiMock = vi.hoisted(() => ({
  invitations: {
    verify: vi.fn(),
  },
  interviews: {
    get: vi.fn(),
    getQuestions: vi.fn(),
  },
  responses: {
    start: vi.fn(),
    submitAnswer: vi.fn(),
    submitQuality: vi.fn(),
    submitEmotion: vi.fn(),
    complete: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

vi.mock('react-webcam', () => ({
  default: () => <div data-testid="webcam" />,
}))

const renderPage = (token = 'valid-token') => render(
  <MemoryRouter initialEntries={[`/interview/${token}`]}>
    <Routes>
      <Route path="/interview/:token" element={<InterviewRoom />} />
      <Route path="/login" element={<div>Login page</div>} />
    </Routes>
  </MemoryRouter>
)

describe('InterviewRoom token verification', () => {
  const getUserMediaMock = vi.fn()

  beforeEach(() => {
    apiMock.invitations.verify.mockReset()
    apiMock.interviews.get.mockReset()
    apiMock.interviews.getQuestions.mockReset()
    apiMock.responses.start.mockReset()
    apiMock.responses.submitAnswer.mockReset()
    apiMock.responses.submitQuality.mockReset()
    apiMock.responses.submitEmotion.mockReset()
    apiMock.responses.complete.mockReset()
    getUserMediaMock.mockReset()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: getUserMediaMock },
    })
  })

  it('shows a public verified invitation screen from the token response', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    expect(screen.getByText('Support Screen')).toBeInTheDocument()
    expect(screen.getByText(/candidate one/i)).toBeInTheDocument()
    expect(screen.getByText(/candidate@example.com/i)).toBeInTheDocument()
    expect(screen.getByText(/questions:/i).closest('p')).toHaveTextContent('Questions: 1')
    expect(apiMock.invitations.verify).toHaveBeenCalledWith('valid-token')
    expect(apiMock.interviews.get).not.toHaveBeenCalled()
    expect(apiMock.interviews.getQuestions).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    expect(screen.getByText(/interview instructions/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start interview/i })).toBeDisabled()
    expect(apiMock.responses.start).not.toHaveBeenCalled()

    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    expect(screen.getByRole('button', { name: /start interview/i })).toBeDisabled()

    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    expect(screen.getByRole('button', { name: /start interview/i })).toBeDisabled()

    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))
    expect(await screen.findByText(/camera and microphone are available/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start interview/i })).toBeEnabled()
  })

  it('starts the interview only after consent and device checks pass', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })
    apiMock.responses.start.mockResolvedValue({ data: { id: 99 } })

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))
    expect(await screen.findByText(/camera and microphone are available/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /start interview/i }))

    await waitFor(() => {
      expect(apiMock.responses.start).toHaveBeenCalledWith({
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        invitation_token: 'valid-token',
      })
    })
    expect(await screen.findByText(/question 1 of 1/i)).toBeInTheDocument()
    expect(screen.getByText(/time remaining: 30:00/i)).toBeInTheDocument()
  })

  it('restores and autosaves typed answer drafts', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })
    apiMock.responses.start.mockResolvedValue({ data: { id: 99 } })
    localStorage.setItem('sris-answer-draft:valid-token:20', 'Previously saved answer')

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))
    await userEvent.click(await screen.findByRole('button', { name: /start interview/i }))

    expect(await screen.findByDisplayValue('Previously saved answer')).toBeInTheDocument()
    expect(screen.getByText(/your saved draft was restored/i)).toBeInTheDocument()

    const answerInput = screen.getByLabelText(/your answer/i)
    await userEvent.clear(answerInput)
    await userEvent.type(answerInput, 'Updated local draft')

    await waitFor(() => {
      expect(localStorage.getItem('sris-answer-draft:valid-token:20')).toBe('Updated local draft')
    })
    expect(screen.getByText(/draft saved locally/i)).toBeInTheDocument()
  })

  it('completes the interview with a typed answer', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })
    apiMock.responses.start.mockResolvedValue({ data: { id: 99 } })
    apiMock.responses.submitAnswer.mockResolvedValue({ data: { question_id: 20 } })
    apiMock.responses.complete.mockResolvedValue({ data: { id: 99, status: 'completed' } })

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))
    await userEvent.click(await screen.findByRole('button', { name: /start interview/i }))
    await userEvent.type(await screen.findByLabelText(/your answer/i), 'I would listen and follow up.')
    await userEvent.click(screen.getByRole('button', { name: /submit & complete/i }))

    await waitFor(() => {
      expect(apiMock.responses.submitAnswer).toHaveBeenCalledWith(99, 20, 'I would listen and follow up.', undefined, undefined, expect.any(Function))
    })
    expect(apiMock.responses.submitQuality).not.toHaveBeenCalled()
    expect(apiMock.responses.submitEmotion).not.toHaveBeenCalled()
    expect(apiMock.responses.complete).toHaveBeenCalledWith(99)
    expect(await screen.findByText(/interview completed/i)).toBeInTheDocument()
  })

  it('keeps typed answers available for retry after submit failure', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })
    apiMock.responses.start.mockResolvedValue({ data: { id: 99 } })
    apiMock.responses.submitAnswer.mockRejectedValueOnce({ response: { data: { detail: 'Network retry needed' } } })
    apiMock.responses.submitAnswer.mockResolvedValueOnce({ data: { question_id: 20 } })
    apiMock.responses.complete.mockResolvedValue({ data: { id: 99, status: 'completed' } })

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    getUserMediaMock.mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))
    await userEvent.click(await screen.findByRole('button', { name: /start interview/i }))
    await userEvent.type(await screen.findByLabelText(/your answer/i), 'Retryable answer')
    await userEvent.click(screen.getByRole('button', { name: /submit & complete/i }))

    expect(await screen.findByText(/network retry needed/i)).toBeInTheDocument()
    expect(screen.getByDisplayValue('Retryable answer')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /retry submission/i }))

    await waitFor(() => {
      expect(apiMock.responses.submitAnswer).toHaveBeenCalledTimes(2)
    })
    expect(await screen.findByText(/interview completed/i)).toBeInTheDocument()
  })

  it('keeps start disabled when device checks fail', async () => {
    apiMock.invitations.verify.mockResolvedValue({
      data: {
        id: 12,
        interview_id: 4,
        candidate_email: 'candidate@example.com',
        candidate_name: 'Candidate One',
        status: 'sent',
        expires_at: '2026-07-25T00:00:00Z',
        interview: {
          id: 4,
          title: 'Support Screen',
          description: 'Structured support interview',
          duration_minutes: 30,
          max_attempts: 1,
          questions: [
            { id: 20, question_text: 'How do you handle an upset customer?', question_type: 'text', weight: 1, order_index: 0 },
          ],
        },
      },
    })
    getUserMediaMock.mockRejectedValue(new Error('Permission denied'))

    renderPage()

    expect(await screen.findByText(/invitation verified/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /continue to setup/i }))
    await userEvent.click(screen.getByLabelText(/i understand how my interview data will be used/i))
    await userEvent.click(screen.getByLabelText(/i consent to participate/i))
    await userEvent.click(screen.getByRole('button', { name: /check camera and microphone/i }))

    expect(await screen.findByText(/device check failed/i)).toBeInTheDocument()
    expect(screen.getByText(/permission denied/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start interview/i })).toBeDisabled()
    expect(apiMock.responses.start).not.toHaveBeenCalled()
  })

  it('shows token verification errors without loading the interview room', async () => {
    apiMock.invitations.verify.mockRejectedValue({ response: { data: { detail: 'Invitation has expired' } } })

    renderPage('expired-token')

    expect(await screen.findByText(/invitation has expired/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /go to login/i })).toBeInTheDocument()
    expect(apiMock.interviews.get).not.toHaveBeenCalled()
    expect(apiMock.interviews.getQuestions).not.toHaveBeenCalled()
  })
})