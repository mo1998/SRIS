import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CreateInterview from './CreateInterview'

const navigateMock = vi.hoisted(() => vi.fn())
const apiMock = vi.hoisted(() => ({
  interviews: {
    listTemplates: vi.fn(),
    getTemplate: vi.fn(),
    createFromTemplate: vi.fn(),
    create: vi.fn(),
  },
}))

vi.mock('react-router-dom', () => ({
  useNavigate: () => navigateMock,
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const supportTemplate = {
  id: 1,
  name: 'Customer Support Screen',
  description: 'First-round support screen',
  role_category: 'customer_support',
  duration_minutes: 25,
  pass_score: 70,
  questions: [
    {
      id: 1,
      question_text: 'How do you handle an upset customer?',
      expected_answer: 'Listen and resolve.',
      weight: 1.5,
      order_index: 0,
      rubric_criteria: [
        {
          id: 1,
          name: 'Clarity',
          description: 'Answer is clear and direct.',
          weight: 1,
          order_index: 0,
        },
      ],
    },
  ],
}

describe('CreateInterview', () => {
  beforeEach(() => {
    navigateMock.mockReset()
    apiMock.interviews.listTemplates.mockReset()
    apiMock.interviews.getTemplate.mockReset()
    apiMock.interviews.createFromTemplate.mockReset()
    apiMock.interviews.create.mockReset()
    apiMock.interviews.listTemplates.mockResolvedValue({ data: [supportTemplate] })
  })

  it('loads templates and creates an interview from a selected template', async () => {
    apiMock.interviews.getTemplate.mockResolvedValue({ data: supportTemplate })
    apiMock.interviews.createFromTemplate.mockResolvedValue({ data: { id: 42 } })

    render(<CreateInterview />)

    await userEvent.selectOptions(await screen.findByLabelText(/template/i), '1')
    expect(await screen.findByText('How do you handle an upset customer?')).toBeInTheDocument()
    expect(screen.getByText(/clarity/i)).toBeInTheDocument()
    expect(screen.getByText(/answer is clear and direct/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /create from template/i }))

    await waitFor(() => {
      expect(apiMock.interviews.createFromTemplate).toHaveBeenCalledWith(1, {
        title: 'Customer Support Screen',
        description: 'First-round support screen',
        duration_minutes: 25,
        max_attempts: 1,
        pass_score: 70,
      })
    })
    expect(navigateMock).toHaveBeenCalledWith('/employer/interviews/42')
  })

  it('keeps the manual create flow working', async () => {
    apiMock.interviews.create.mockResolvedValue({ data: { id: 43 } })

    render(<CreateInterview />)

    await userEvent.type(screen.getByLabelText(/interview title/i), 'Manual Screen')
    await userEvent.type(screen.getByLabelText(/question text/i), 'Why are you interested?')
    await userEvent.click(screen.getByRole('button', { name: /add criterion/i }))
    await userEvent.type(screen.getByLabelText(/^name$/i), 'Clarity')
    await userEvent.type(screen.getByLabelText(/^description$/i), 'Explains the motivation clearly')
    await userEvent.click(screen.getByRole('button', { name: /^create interview$/i }))

    await waitFor(() => {
      expect(apiMock.interviews.create).toHaveBeenCalledWith(expect.objectContaining({
        title: 'Manual Screen',
        questions: [expect.objectContaining({
          question_text: 'Why are you interested?',
          order_index: 0,
          rubric_criteria: [expect.objectContaining({
            name: 'Clarity',
            description: 'Explains the motivation clearly',
            order_index: 0,
          })],
        })],
      }))
    })
    expect(navigateMock).toHaveBeenCalledWith('/employer/interviews/43')
  })
})