import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EmployerDashboard from './EmployerDashboard'

const apiMock = vi.hoisted(() => ({
  interviews: {
    list: vi.fn(),
  },
  users: {
    getMyOrganization: vi.fn(),
    getMyMemberships: vi.fn(),
    addMembership: vi.fn(),
  },
  reports: {
    getEvaluationHealth: vi.fn(),
    getEmailHealth: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderDashboard = () => render(
  <BrowserRouter>
    <EmployerDashboard />
  </BrowserRouter>
)

describe('EmployerDashboard', () => {
  beforeEach(() => {
    apiMock.interviews.list.mockReset()
    apiMock.users.getMyOrganization.mockReset()
    apiMock.users.getMyMemberships.mockReset()
    apiMock.users.addMembership.mockReset()
    apiMock.reports.getEvaluationHealth.mockReset()
    apiMock.reports.getEmailHealth.mockReset()
  })

  it('shows organization details and adds an existing team member', async () => {
    apiMock.interviews.list.mockResolvedValue({ data: [] })
    apiMock.users.getMyOrganization.mockResolvedValue({
      data: { id: 1, name: 'SRIS Test Co' },
    })
    apiMock.users.getMyMemberships.mockResolvedValue({
      data: [{ id: 1, user_id: 10, role: 'owner' }],
    })
    apiMock.users.addMembership.mockResolvedValue({
      data: { id: 2, user_id: 11, role: 'reviewer' },
    })
    apiMock.reports.getEvaluationHealth.mockResolvedValue({
      data: {
        provider: 'local_vllm',
        prompt_version: 'rubric-v1',
        config_hash: 'cfg123',
        model_name: 'qwen3-8b-awq',
        healthy: false,
        status: 'local_vllm_unavailable_using_fallback',
        fallback_provider: 'deterministic_baseline',
        last_error: 'connection refused',
      },
    })
    apiMock.reports.getEmailHealth.mockResolvedValue({
      data: {
        configured: false,
        status: 'configuration_incomplete',
        mail_from: 'noreply@yourdomain.com',
        mail_server: 'smtp.gmail.com',
        mail_port: 587,
        missing_settings: ['MAIL_FROM', 'MAIL_PASSWORD'],
      },
    })

    renderDashboard()

    expect(await screen.findByText('SRIS Test Co')).toBeInTheDocument()
    expect(screen.getByText(/evaluation agent health/i)).toBeInTheDocument()
    expect(screen.getByText(/local_vllm_unavailable_using_fallback/i)).toBeInTheDocument()
    expect(screen.getByText(/qwen3-8b-awq/i)).toBeInTheDocument()
    expect(screen.getByText(/deterministic_baseline/i)).toBeInTheDocument()
    expect(screen.getByText(/rubric-v1/i)).toBeInTheDocument()
    expect(screen.getByText(/cfg123/i)).toBeInTheDocument()
    expect(screen.getByText(/email delivery health/i)).toBeInTheDocument()
    expect(screen.getByText(/configuration_incomplete/i)).toBeInTheDocument()
    expect(screen.getByText(/MAIL_FROM, MAIL_PASSWORD/i)).toBeInTheDocument()
    expect(screen.getByText('Team members: 1')).toBeInTheDocument()
    expect(screen.getByText('owner')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('teammate@example.com'), 'reviewer@example.com')
    await userEvent.click(screen.getByRole('button', { name: /add/i }))

    await waitFor(() => {
      expect(apiMock.users.addMembership).toHaveBeenCalledWith({
        email: 'reviewer@example.com',
        role: 'reviewer',
      })
    })
    expect(await screen.findByText('Team member added')).toBeInTheDocument()
    expect(screen.getByText('reviewer')).toBeInTheDocument()
  })
})