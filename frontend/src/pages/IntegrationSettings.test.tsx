import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import IntegrationSettings from './IntegrationSettings'

const apiMock = vi.hoisted(() => ({
  users: {
    getMyOrganization: vi.fn(),
    getOrganizationProviders: vi.fn(),
    updateOrganizationSettings: vi.fn(),
    listProviderPresets: vi.fn(),
    createProviderPreset: vi.fn(),
    applyProviderPreset: vi.fn(),
    deleteProviderPreset: vi.fn(),
  },
  reports: {
    getEvaluationHealth: vi.fn(),
    getEmailHealth: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({
  api: apiMock,
}))

const renderPage = () => render(<IntegrationSettings />)

describe('IntegrationSettings', () => {
  beforeEach(() => {
    apiMock.users.getMyOrganization.mockReset()
    apiMock.users.getOrganizationProviders.mockReset()
    apiMock.users.updateOrganizationSettings.mockReset()
    apiMock.users.listProviderPresets.mockReset()
    apiMock.users.createProviderPreset.mockReset()
    apiMock.users.applyProviderPreset.mockReset()
    apiMock.users.deleteProviderPreset.mockReset()
    apiMock.reports.getEvaluationHealth.mockReset()
    apiMock.reports.getEmailHealth.mockReset()
  })

  const mockLoad = () => {
    apiMock.users.getMyOrganization.mockResolvedValue({ data: { id: 1, name: 'SRIS Test Co' } })
    apiMock.users.getOrganizationProviders.mockResolvedValue({
      data: {
        organization_id: 1,
        selected: null,
        configured: false,
        role: 'owner',
        providers: [
          { value: 'local_vllm', available: true },
          { value: 'cloud_llm', available: true },
        ],
      },
    })
    apiMock.users.listProviderPresets.mockResolvedValue({ data: [] })
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
  }

  it('renders the AI Provider form by default and saves provider settings', async () => {
    mockLoad()
    apiMock.users.updateOrganizationSettings.mockResolvedValue({
      data: { id: 1, name: 'SRIS Test Co', evaluation_provider: 'cloud_llm', evaluation_model: 'gemini-2.5-flash', evaluation_base_url: 'https://api.test', evaluation_api_key: null },
    })

    renderPage()

    await screen.findByRole('button', { name: /^save$/i })
    expect(screen.getByLabelText('Provider')).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Provider'), 'cloud_llm')
    await userEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      expect(apiMock.users.updateOrganizationSettings).toHaveBeenCalledWith({
        evaluation_provider: 'cloud_llm',
        evaluation_model: '',
        evaluation_base_url: '',
        evaluation_api_key: '',
      })
    })
  })

  it('shows evaluation agent health on its tab', async () => {
    mockLoad()

    renderPage()

    await userEvent.click(await screen.findByRole('tab', { name: /evaluation agent/i }))

    expect(screen.getByText(/llm_unavailable_using_fallback/i)).toBeInTheDocument()
    expect(screen.getByText(/qwen3-8b-awq/i)).toBeInTheDocument()
    expect(screen.getByText(/deterministic_baseline/i)).toBeInTheDocument()
    expect(screen.getByText(/rubric-v1/i)).toBeInTheDocument()
    expect(screen.getByText(/cfg123/i)).toBeInTheDocument()
    expect(screen.getByText(/connection refused/i)).toBeInTheDocument()
  })

  it('shows email delivery health on its tab', async () => {
    mockLoad()

    renderPage()

    await userEvent.click(await screen.findByRole('tab', { name: /email delivery/i }))

    expect(screen.getByText(/configuration_incomplete/i)).toBeInTheDocument()
    expect(screen.getByText(/noreply@yourdomain.com/i)).toBeInTheDocument()
    expect(screen.getByText(/smtp.gmail.com:587/i)).toBeInTheDocument()
    expect(screen.getByText(/MAIL_FROM, MAIL_PASSWORD/i)).toBeInTheDocument()
  })
})
