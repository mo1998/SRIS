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
    getOrganizationMembers: vi.fn(),
    addMembership: vi.fn(),
    getOrganizationProviders: vi.fn(),
    updateOrganizationSettings: vi.fn(),
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
    apiMock.users.getOrganizationMembers.mockReset()
    apiMock.users.addMembership.mockReset()
    apiMock.users.getOrganizationProviders.mockReset()
    apiMock.users.updateOrganizationSettings.mockReset()
    apiMock.reports.getEvaluationHealth.mockReset()
    apiMock.reports.getEmailHealth.mockReset()
  })

  it('shows organization details and adds an existing team member', async () => {
    apiMock.interviews.list.mockResolvedValue({ data: [] })
    apiMock.users.getMyOrganization.mockResolvedValue({
      data: { id: 1, name: 'SRIS Test Co' },
    })
    apiMock.users.getOrganizationProviders.mockResolvedValue({
      data: {
        organization_id: 1,
        selected: null,
        configured: false,
        role: 'owner',
        providers: [
          { value: 'local_vllm', available: true },
          { value: 'cloud_llm', available: true },
          { value: 'hybrid', available: true },
        ],
      },
    })
    apiMock.users.addMembership.mockResolvedValue({
      data: { user_id: 12, email: 'newmember@example.com', role: 'reviewer' },
    })
    apiMock.users.getOrganizationMembers
      .mockResolvedValueOnce({
        data: [
          { user_id: 10, email: 'owner@example.com', full_name: 'Omar Owner', role: 'owner' },
          { user_id: 11, email: 'reviewer@example.com', full_name: 'Rita Reviewer', role: 'reviewer' },
        ],
      })
      .mockResolvedValueOnce({
        data: [
          { user_id: 10, email: 'owner@example.com', full_name: 'Omar Owner', role: 'owner' },
          { user_id: 11, email: 'reviewer@example.com', full_name: 'Rita Reviewer', role: 'reviewer' },
          { user_id: 12, email: 'newmember@example.com', full_name: 'Nina New', role: 'reviewer' },
        ],
      })
    apiMock.reports.getEvaluationHealth.mockResolvedValue({
      data: {
        provider: 'local_vllm',
        prompt_version: 'rubric-v1',
        config_hash: 'cfg123',
        model_name: 'qwen3-8b-awq',
        configured: true,
        healthy: false,
        status: 'llm_unavailable_using_fallback',
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
    expect(screen.getByText(/evaluation agent/i)).toBeInTheDocument()
    expect(screen.getByText(/ai provider/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
    expect(screen.getByText(/not configured/i)).toBeInTheDocument()
    expect(screen.getByText(/cloud llm/i)).toBeInTheDocument()
    expect(apiMock.reports.getEvaluationHealth).toHaveBeenCalledWith(1)
    expect(screen.getByText(/llm_unavailable_using_fallback/i)).toBeInTheDocument()
    expect(screen.getByText(/qwen3-8b-awq/i)).toBeInTheDocument()
    expect(screen.getByText(/deterministic_baseline/i)).toBeInTheDocument()
    expect(screen.getByText(/rubric-v1/i)).toBeInTheDocument()
    expect(screen.getByText(/cfg123/i)).toBeInTheDocument()
    expect(screen.getByText(/email delivery/i)).toBeInTheDocument()
    expect(screen.getByText(/configuration_incomplete/i)).toBeInTheDocument()
    expect(screen.getByText(/MAIL_FROM, MAIL_PASSWORD/i)).toBeInTheDocument()
    expect(screen.getByText('Team members: 2')).toBeInTheDocument()
    expect(screen.getByText('Omar Owner')).toBeInTheDocument()
    expect(screen.getByText('Rita Reviewer')).toBeInTheDocument()
    expect(screen.getByText('owner')).toBeInTheDocument()
    expect(screen.getByText('reviewer@example.com')).toBeInTheDocument()

    await userEvent.type(screen.getByPlaceholderText('teammate@example.com'), 'newmember@example.com')
    await userEvent.click(screen.getByRole('button', { name: /add/i }))

    await waitFor(() => {
      expect(apiMock.users.addMembership).toHaveBeenCalledWith({
        email: 'newmember@example.com',
        role: 'reviewer',
      })
    })
    expect(await screen.findByText('newmember@example.com')).toBeInTheDocument()
    expect(screen.getByText('Nina New')).toBeInTheDocument()
    expect(screen.getByText('Team members: 3')).toBeInTheDocument()
  })
})